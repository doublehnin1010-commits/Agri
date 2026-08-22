from datetime import datetime, timezone
from io import BytesIO

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.core.deps import get_current_user_id
from app.db.mongodb import get_db, get_gridfs_bucket
from app.models.chat import ChatRequest, ChatResponse
from app.services.rag import arag_answer, arag_image_answer
from app.core.config import settings

router = APIRouter()


def _message(
    role: str,
    content: str,
    created_at: datetime,
    answer: dict | None = None,
    image_id: ObjectId | None = None,
    image_content_type: str | None = None,
) -> dict:
    item = {"role": role, "content": content, "created_at": created_at}
    if answer is not None:
        item["answer"] = answer
    if image_id is not None:
        item["image_id"] = image_id
        item["image_content_type"] = image_content_type
    return item


def _answer_to_text(answer: dict | None) -> str:
    if not isinstance(answer, dict):
        return ""
    return _clean_text(answer.get("answer")) or _clean_text(answer.get("meaning_simple_mm")) or ""


def _clean_text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _title_from_message(message: str, limit: int = 40) -> str:
    title = " ".join(message.split())
    if len(title) > limit:
        return f"{title[: limit - 1]}..."
    return title or "Untitled conversation"


def _object_id_or_none(value: str | None) -> ObjectId | None:
    if not value or value == "draft":
        return None
    try:
        return ObjectId(value)
    except Exception:
        return None


_IMAGE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


async def _read_validated_image(image: UploadFile) -> tuple[bytes, str]:
    filename = (image.filename or "").lower()
    extension = next((suffix for suffix in _IMAGE_TYPES if filename.endswith(suffix)), None)
    if extension is None or image.content_type != _IMAGE_TYPES[extension]:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only JPG, JPEG, PNG, and WEBP images are supported.")

    max_bytes = settings.max_image_upload_mb * 1024 * 1024
    image_bytes = await image.read(max_bytes + 1)
    if not image_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded image is empty.")
    if len(image_bytes) > max_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"Image must be {settings.max_image_upload_mb} MB or smaller.")

    try:
        with Image.open(BytesIO(image_bytes)) as decoded:
            decoded.verify()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded image is corrupted or unreadable.")
    return image_bytes, _IMAGE_TYPES[extension]


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, user_id: str = Depends(get_current_user_id)):
    db = get_db()
    history = db["chat_history"]
    now = datetime.now(timezone.utc)
    conversation = None
    object_id = _object_id_or_none(payload.conversation_id)
    if object_id is not None:
        conversation = await history.find_one({"_id": object_id, "user_id": user_id})

    answer = await arag_answer(payload.message)
    user_message = _message("user", payload.message, now)
    assistant_message = _message("assistant", _answer_to_text(answer), now, answer)

    if conversation:
        existing_messages = conversation.get("messages")
        if not existing_messages:
            existing_messages = [
                _message("user", conversation.get("user_message", ""), conversation.get("created_at", now)),
                _message("assistant", _answer_to_text(conversation.get("assistant_message")), conversation.get("created_at", now), conversation.get("assistant_message")),
            ]

        await history.update_one(
            {"_id": conversation["_id"], "user_id": user_id},
            {"$set": {"messages": [*existing_messages, user_message, assistant_message], "updated_at": now}},
        )
        conversation_id = str(conversation["_id"])
        created_at = conversation.get("created_at", now)
        title = conversation.get("title") or _title_from_message(conversation.get("user_message", payload.message))
    else:
        title = _title_from_message(payload.message)
        result = await history.insert_one(
            {
                "user_id": user_id,
                "title": title,
                "messages": [user_message, assistant_message],
                "created_at": now,
                "updated_at": now,
            }
        )
        conversation_id = str(result.inserted_id)
        created_at = now

    return {"answer": answer, "conversation_id": conversation_id, "title": title, "created_at": created_at}


@router.post("/chat/image", response_model=ChatResponse)
async def image_chat(
    image: UploadFile = File(...),
    question: str = Form(""),
    conversation_id: str | None = Form(None),
    user_id: str = Depends(get_current_user_id),
):
    if len(question.strip()) > 2000:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Question must be 2000 characters or fewer.")
    image_bytes, mime_type = await _read_validated_image(image)
    answer = await arag_image_answer(question.strip(), image_bytes, mime_type)
    image_id = await get_gridfs_bucket().upload_from_stream(
        image.filename or "uploaded-image",
        BytesIO(image_bytes),
        metadata={"user_id": user_id, "content_type": mime_type},
    )

    db = get_db()
    history = db["chat_history"]
    now = datetime.now(timezone.utc)
    conversation = None
    object_id = _object_id_or_none(conversation_id)
    if object_id is not None:
        conversation = await history.find_one({"_id": object_id, "user_id": user_id})

    display_question = question.strip() or "Please analyze this agriculture image."
    user_message = _message("user", f"[Image attached]\n{display_question}", now, image_id=image_id, image_content_type=mime_type)
    assistant_message = _message("assistant", _answer_to_text(answer), now, answer)
    if conversation:
        existing_messages = conversation.get("messages") or []
        await history.update_one(
            {"_id": conversation["_id"], "user_id": user_id},
            {"$set": {"messages": [*existing_messages, user_message, assistant_message], "updated_at": now}},
        )
        response_id = str(conversation["_id"])
        created_at = conversation.get("created_at", now)
        title = conversation.get("title") or _title_from_message(display_question)
    else:
        title = _title_from_message(display_question)
        result = await history.insert_one(
            {"user_id": user_id, "title": title, "messages": [user_message, assistant_message], "created_at": now, "updated_at": now}
        )
        response_id = str(result.inserted_id)
        created_at = now

    return {"answer": answer, "conversation_id": response_id, "title": title, "created_at": created_at}

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends

from app.db.mongodb import get_db
from app.models.chat import ChatRequest, ChatResponse
from app.core.deps import get_current_user_id
from app.services.rag import rag_answer


router = APIRouter()


def _message(role: str, content: str, created_at: datetime, answer: dict | None = None) -> dict:
    item = {
        "role": role,
        "content": content,
        "created_at": created_at,
    }
    if answer is not None:
        item["answer"] = answer
    return item


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


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, user_id: str = Depends(get_current_user_id)):
    db = get_db()
    history = db["chat_history"]
    now = datetime.now(timezone.utc)
    conversation = None
    object_id = _object_id_or_none(payload.conversation_id)
    if object_id is not None:
        conversation = await history.find_one({"_id": object_id, "user_id": user_id})

    previous_answer = None
    if conversation:
        messages = conversation.get("messages") or []
        for item in reversed(messages):
            if item.get("role") == "assistant":
                previous_answer = item.get("answer")
                break
        if previous_answer is None:
            previous_answer = conversation.get("assistant_message")

    answer = rag_answer(payload.message, previous_answer=previous_answer)

    user_message = _message("user", payload.message, now)
    assistant_message = _message("assistant", "", now, answer)
    assistant_message["content"] = (
        answer.get("meaning_simple_mm")
        or answer.get("meaning")
        or answer.get("proverb")
        or ""
    )

    if conversation:
        existing_messages = conversation.get("messages")
        if not existing_messages:
            existing_messages = [
                _message("user", conversation.get("user_message", ""), conversation.get("created_at", now)),
                _message(
                    "assistant",
                    "",
                    conversation.get("created_at", now),
                    conversation.get("assistant_message"),
                ),
            ]
            existing_messages[-1]["content"] = (
                (conversation.get("assistant_message") or {}).get("meaning_simple_mm")
                or (conversation.get("assistant_message") or {}).get("meaning")
                or (conversation.get("assistant_message") or {}).get("proverb")
                or ""
            )

        await history.update_one(
            {"_id": conversation["_id"], "user_id": user_id},
            {
                "$set": {
                    "messages": [*existing_messages, user_message, assistant_message],
                    "updated_at": now,
                }
            },
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

    return {
        "answer": answer,
        "conversation_id": conversation_id,
        "title": title,
        "created_at": created_at,
    }


from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.deps import get_current_user_id
from app.db.mongodb import get_db, get_gridfs_bucket


def _serialize_message(message: dict) -> dict:
    serialized = dict(message)
    if serialized.get("image_id") is not None:
        image_id = str(serialized["image_id"])
        serialized["image_id"] = image_id
        serialized["image_url"] = f"/api/v1/history/images/{image_id}"
    return serialized


router = APIRouter()


class HistoryTitleUpdate(BaseModel):
    title: str


def _parse_object_id(object_id: str) -> ObjectId:
    try:
        return ObjectId(object_id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid conversation id") from exc


@router.get("/history")
async def history(limit: int = 30, user_id: str = Depends(get_current_user_id)):
    db = get_db()
    cur = (
        db["chat_history"]
        .find(
            {"user_id": user_id},
            {"user_message": 1, "assistant_message": 1, "created_at": 1, "title": 1, "messages": 1},
        )
        .sort("created_at", -1)
        .limit(max(1, min(limit, 200)))
    )
    items = await cur.to_list(length=max(1, min(limit, 200)))
    normalized_items = []
    for item in reversed(items):
        base = {
            "id": str(item["_id"]),
            "title": item.get("title", ""),
            "created_at": item["created_at"],
        }
        if item.get("messages"):
            normalized_items.append({**base, "messages": [_serialize_message(message) for message in item["messages"]]})
        else:
            normalized_items.append(
                {
                    **base,
                    "user_message": item["user_message"],
                    "assistant_message": item["assistant_message"],
                }
            )

    return {
        "items": normalized_items
    }


@router.get("/history/images/{image_id}")
async def history_image(image_id: str, user_id: str = Depends(get_current_user_id)):
    try:
        object_id = ObjectId(image_id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image id") from exc

    message = await get_db()["chat_history"].find_one(
        {"user_id": user_id, "messages.image_id": object_id},
        {"_id": 1},
    )
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    try:
        stream = await get_gridfs_bucket().open_download_stream(object_id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found") from exc

    content_type = (stream.metadata or {}).get("content_type", "application/octet-stream")
    return StreamingResponse(stream, media_type=content_type)


@router.patch("/history/{conversation_id}")
async def rename_history(
    conversation_id: str,
    payload: HistoryTitleUpdate,
    user_id: str = Depends(get_current_user_id),
):
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Title must not be empty")

    db = get_db()
    object_id = _parse_object_id(conversation_id)
    result = await db["chat_history"].update_one(
        {"_id": object_id, "user_id": user_id},
        {"$set": {"title": title}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    return {"id": conversation_id, "title": title}


@router.delete("/history/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_history(conversation_id: str, user_id: str = Depends(get_current_user_id)):
    db = get_db()
    object_id = _parse_object_id(conversation_id)
    result = await db["chat_history"].delete_one({"_id": object_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

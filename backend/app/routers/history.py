from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from app.core.deps import get_current_user_id
from app.db.mongodb import get_db


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
            normalized_items.append({**base, "messages": item["messages"]})
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

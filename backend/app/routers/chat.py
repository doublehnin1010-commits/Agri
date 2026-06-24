from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.db.mongodb import get_db
from app.models.chat import ChatRequest, ChatResponse
from app.core.deps import get_current_user_id
from app.services.rag import rag_answer


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, user_id: str = Depends(get_current_user_id)):
    db = get_db()
    history = db["chat_history"]
    previous = await history.find(
        {"user_id": user_id},
        {"_id": 0, "assistant_message": 1},
    ).sort("created_at", -1).limit(1).to_list(length=1)
    previous_answer = previous[0]["assistant_message"] if previous else None

    answer = rag_answer(payload.message, previous_answer=previous_answer)

    await history.insert_one(
        {
            "user_id": user_id,
            "user_message": payload.message,
            "assistant_message": answer,
            "created_at": datetime.now(timezone.utc),
        }
    )

    return {"answer": answer}


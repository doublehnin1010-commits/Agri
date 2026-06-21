from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.db.mongodb import get_db
from app.models.chat import ChatRequest, ChatResponse
from app.core.deps import get_current_user_id
from app.services.rag import rag_answer


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, user_id: str = Depends(get_current_user_id)):
    answer = rag_answer(payload.message)

    db = get_db()
    history = db["chat_history"]
    await history.insert_one(
        {
            "user_id": user_id,
            "user_message": payload.message,
            "assistant_message": answer,
            "created_at": datetime.now(timezone.utc),
        }
    )

    return {"answer": answer}


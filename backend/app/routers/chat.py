from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends

from app.db.mongodb import get_db
from app.models.chat import ChatRequest, ChatResponse
from app.core.deps import get_current_user_id
from app.services.conversation_memory import ConversationMemoryService
from app.services.rag import arag_answer, classify_user_intent


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


def _answer_to_text(answer: dict | None) -> str:
    if not isinstance(answer, dict):
        return ""
    proverb = _clean_text(answer.get("proverb"))
    meaning = _clean_text(answer.get("meaning_simple_mm")) or _clean_text(answer.get("meaning"))
    example = _clean_text(answer.get("example_mm")) or _clean_text(answer.get("example"))
    if answer.get("intent") == "proverb_list":
        return "\n\n".join(part for part in (meaning, example) if part)
    if not proverb:
        return "\n\n".join(part for part in (meaning, example) if part)

    parts = [f"စကားပုံ:\n{proverb}", meaning]
    if example and (not meaning or "ဥပမာ:" not in meaning):
        parts.append(f"ဥပမာ:\n{example}")
    return "\n\n".join(part for part in parts if part)


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


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, user_id: str = Depends(get_current_user_id)):
    db = get_db()
    history = db["chat_history"]
    now = datetime.now(timezone.utc)
    conversation = None
    object_id = _object_id_or_none(payload.conversation_id)
    if object_id is not None:
        conversation = await history.find_one({"_id": object_id, "user_id": user_id})

    memory = ConversationMemoryService.load(conversation)
    previous_answer = ConversationMemoryService.previous_answer(memory)
    intent_data = await classify_user_intent(payload.message)
    answer = await arag_answer(
        payload.message,
        previous_answer=previous_answer,
        memory=memory,
    )
    updated_memory = ConversationMemoryService.update(
        memory,
        str(intent_data["intent"]),
        answer,
        topic=intent_data.get("topic"),
        user_message=payload.message,
    )

    user_message = _message("user", payload.message, now)
    assistant_message = _message("assistant", _answer_to_text(answer), now, answer)

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
            existing_messages[-1]["content"] = _answer_to_text(conversation.get("assistant_message"))

        await history.update_one(
            {"_id": conversation["_id"], "user_id": user_id},
            {
                "$set": {
                    "messages": [*existing_messages, user_message, assistant_message],
                    "memory": updated_memory,
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
                "memory": updated_memory,
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


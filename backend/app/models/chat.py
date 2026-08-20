from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None


class SourceItem(BaseModel):
    document_id: str | None = None
    filename: str | None = None
    file_type: str | None = None
    chunk_id: int | str | None = None
    page_number: int | None = None
    source: str | None = None
    preview: str | None = None
    score: float | None = None
    similarity: float | None = None


class ChatAnswer(BaseModel):
    answer: str | None = None
    language: str | None = None
    sources: list[SourceItem] = []


class ChatResponse(BaseModel):
    answer: dict[str, Any]
    conversation_id: str
    title: str
    created_at: datetime


class HistoryItem(BaseModel):
    user_message: str
    assistant_message: dict
    created_at: datetime

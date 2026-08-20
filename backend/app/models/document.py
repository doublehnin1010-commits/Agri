from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


DocumentStatus = Literal["pending", "processing", "completed", "failed"]


class AgricultureDocument(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    status: DocumentStatus
    uploaded_at: datetime
    processed_at: datetime | None = None
    chunk_count: int = 0
    error: str | None = None


class DocumentUploadResponse(BaseModel):
    document_id: str
    status: DocumentStatus
    message: str


class DocumentListResponse(BaseModel):
    documents: list[AgricultureDocument] = Field(default_factory=list)

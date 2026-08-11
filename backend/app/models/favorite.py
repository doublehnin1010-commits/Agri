from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class FavoriteStatusResponse(BaseModel):
    message: str | None = None
    favorite: bool


class FavoriteProverbResponse(BaseModel):
    id: str
    proverb: str
    meaning: str | None = None
    english_meaning: str | None = None
    category: str | None = None
    keyword: str | None = None
    example: str | None = None
    created_at: datetime

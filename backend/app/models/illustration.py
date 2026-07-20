from typing import Literal

from pydantic import BaseModel, Field


ImageStyle = Literal[
    "realistic",
    "anime",
    "watercolor",
    "oil_painting",
    "cartoon",
    "traditional_myanmar",
    "vector",
    "sketch",
]


class IllustrationRequest(BaseModel):
    proverb: str = Field(min_length=1, max_length=1000)
    meaning: str = Field(min_length=1, max_length=4000)
    english_meaning: str | None = Field(default=None, max_length=4000)
    style: ImageStyle = "realistic"


class IllustrationResponse(BaseModel):
    success: bool = True
    style: ImageStyle
    proverb: str
    meaning: str
    prompt: str
    image_url: str
    mime_type: str = "image/png"

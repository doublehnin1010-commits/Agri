from pydantic import BaseModel, Field


class ProverbCreate(BaseModel):
    keyword: str = Field(default="", max_length=200)
    proverb: str = Field(min_length=1, max_length=2000)
    meaning: str = Field(default="", max_length=4000)
    english_meaning: str = Field(default="", max_length=4000)
    example: str = Field(default="", max_length=4000)


class ProverbUpdate(BaseModel):
    keyword: str | None = Field(default=None, max_length=200)
    proverb: str | None = Field(default=None, min_length=1, max_length=2000)
    meaning: str | None = Field(default=None, max_length=4000)
    english_meaning: str | None = Field(default=None, max_length=4000)
    example: str | None = Field(default=None, max_length=4000)


class ProverbResponse(BaseModel):
    id: str
    keyword: str | None = None
    proverb: str
    meaning: str | None = None
    english_meaning: str | None = None
    example: str | None = None

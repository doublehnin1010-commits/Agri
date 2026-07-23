from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.proverb import ProverbResponse


QuizDifficulty = Literal["easy", "medium", "hard"]
QuizQuestionType = Literal[
    "multiple_choice",
    "meaning_identification",
    "situation_matching",
    "fill_in_the_blank",
]


class QuizStartRequest(BaseModel):
    category: str | None = Field(default=None, max_length=120)
    difficulty: QuizDifficulty | None = "easy"
    question_count: int = Field(default=5, ge=1, le=20)

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class QuizQuestionResponse(BaseModel):
    id: int
    type: QuizQuestionType
    proverb: str
    question: str
    options: list[str] = Field(min_length=4, max_length=4)


class QuizStartResponse(BaseModel):
    quiz_id: str
    questions: list[QuizQuestionResponse]


class QuizAnswer(BaseModel):
    question_id: int = Field(ge=1)
    selected: int = Field(ge=0, le=3)


class QuizSubmitRequest(BaseModel):
    quiz_id: str = Field(min_length=1, max_length=120)
    answers: list[QuizAnswer] = Field(min_length=1)


class QuizQuestionResult(BaseModel):
    question_id: int
    correct: bool
    correct_answer: int
    explanation: str
    selected: int | None = None


class QuizSubmitResponse(BaseModel):
    score: int
    total: int
    percentage: int
    results: list[QuizQuestionResult]
    recommended_proverbs: list[ProverbResponse]

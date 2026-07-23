from __future__ import annotations

import logging
import random
import uuid
from dataclasses import dataclass
from typing import Any

from app.models.quiz import QuizQuestionResponse, QuizQuestionType, QuizStartRequest, QuizStartResponse, QuizSubmitRequest, QuizSubmitResponse, QuizQuestionResult
from app.services.retriever_service import get_metadata_cache


logger = logging.getLogger(__name__)

QUESTION_TYPES: list[QuizQuestionType] = [
    "multiple_choice",
    "meaning_identification",
    "situation_matching",
    "fill_in_the_blank",
]

@dataclass
class StoredQuestion:
    id: int
    type: QuizQuestionType
    proverb: str
    meaning: str
    english_meaning: str
    example: str
    question: str
    options: list[str]
    correct_answer: int


@dataclass
class QuizSession:
    quiz_id: str
    user_id: str
    questions: list[StoredQuestion]


_sessions: dict[str, QuizSession] = {}


async def start_quiz(payload: QuizStartRequest, user_id: str) -> QuizStartResponse:
    rows = _dataset_rows(payload.category)
    if len(rows) < 4:
        raise ValueError("Not enough proverb data is available for this quiz.")

    selected_rows = random.sample(rows, k=min(payload.question_count, len(rows)))
    questions: list[StoredQuestion] = []
    for index, row in enumerate(selected_rows, start=1):
        question_type = QUESTION_TYPES[(index - 1) % len(QUESTION_TYPES)]
        candidates = _distractor_rows(row, rows, count=8)
        generated = _fallback_generated(row, candidates, question_type)
        questions.append(_stored_question(index, row, generated, question_type, candidates))

    quiz_id = uuid.uuid4().hex
    _sessions[quiz_id] = QuizSession(quiz_id=quiz_id, user_id=user_id, questions=questions)
    logger.info("Started quiz %s for user %s with %s questions.", quiz_id, user_id, len(questions))
    return QuizStartResponse(
        quiz_id=quiz_id,
        questions=[
            QuizQuestionResponse(
                id=question.id,
                type=question.type,
                proverb=question.proverb,
                question=question.question,
                options=question.options,
            )
            for question in questions
        ],
    )


async def submit_quiz(payload: QuizSubmitRequest, user_id: str) -> QuizSubmitResponse:
    session = _sessions.get(payload.quiz_id)
    if session is None or session.user_id != user_id:
        raise KeyError("Quiz session not found.")

    answers = {answer.question_id: answer.selected for answer in payload.answers}
    results: list[QuizQuestionResult] = []
    incorrect_questions: list[StoredQuestion] = []
    score = 0

    for question in session.questions:
        selected = answers.get(question.id)
        correct = selected == question.correct_answer
        if correct:
            score += 1
        else:
            incorrect_questions.append(question)
        results.append(
            QuizQuestionResult(
                question_id=question.id,
                correct=correct,
                correct_answer=question.correct_answer,
                selected=selected,
                explanation=_explanation(question),
            )
        )

    total = len(session.questions)
    percentage = round((score / total) * 100) if total else 0
    return QuizSubmitResponse(
        score=score,
        total=total,
        percentage=percentage,
        results=results,
        recommended_proverbs=[],
    )


def _dataset_rows(category: str | None) -> list[dict[str, Any]]:
    rows = [
        _normalize_row(row)
        for row in get_metadata_cache()
        if row and row.get("proverb") and (row.get("meaning") or row.get("english_meaning"))
    ]
    if category:
        normalized = category.casefold()
        rows = [row for row in rows if str(row.get("category") or "").casefold() == normalized]
    random.shuffle(rows)
    return rows


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "keyword": str(row.get("keyword") or ""),
        "category": str(row.get("category") or ""),
        "proverb": str(row.get("proverb") or ""),
        "meaning": str(row.get("meaning") or ""),
        "english_meaning": str(row.get("english_meaning") or ""),
        "example": str(row.get("example") or ""),
    }


def _distractor_rows(correct: dict[str, Any], rows: list[dict[str, Any]], *, count: int) -> list[dict[str, Any]]:
    category = correct.get("category")
    pool = [row for row in rows if row["proverb"] != correct["proverb"] and row.get("category") == category]
    if len(pool) < count:
        pool.extend(row for row in rows if row["proverb"] != correct["proverb"] and row not in pool)
    return random.sample(pool, k=min(count, len(pool)))


def _stored_question(
    index: int,
    row: dict[str, Any],
    generated: dict[str, Any],
    question_type: QuizQuestionType,
    candidates: list[dict[str, Any]],
) -> StoredQuestion:
    correct = _option_text(generated.get("correct_option")) or _meaning(row)
    distractors = [_option_text(item) for item in generated.get("distractors", [])]
    distractors.extend(_meaning(item) for item in candidates)
    options = _unique_options([correct, *distractors])[:4]
    if len(options) < 4:
        raise ValueError("Not enough unique answer options are available.")
    random.shuffle(options)
    return StoredQuestion(
        id=index,
        type=question_type,
        proverb=row["proverb"],
        meaning=row["meaning"],
        english_meaning=row["english_meaning"],
        example=row["example"],
        question=str(generated.get("question") or _default_question(question_type)).strip(),
        options=options,
        correct_answer=options.index(correct),
    )


def _fallback_generated(row: dict[str, Any], candidates: list[dict[str, Any]], question_type: QuizQuestionType) -> dict[str, Any]:
    return {
        "question": _default_question(question_type),
        "correct_option": _meaning(row),
        "distractors": [_meaning(item) for item in candidates[:3]],
    }


def _default_question(question_type: QuizQuestionType) -> str:
    if question_type == "situation_matching":
        return "Which situation best matches this proverb?"
    if question_type == "fill_in_the_blank":
        return "Choose the meaning that completes the idea of this proverb."
    if question_type == "meaning_identification":
        return "Identify the meaning of this proverb."
    return "What is the correct meaning?"


def _meaning(row: dict[str, Any]) -> str:
    return str(row.get("meaning") or row.get("english_meaning") or "").strip()


def _option_text(value: Any) -> str:
    return str(value or "").strip()


def _unique_options(options: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for option in options:
        normalized = " ".join(option.split())
        if not normalized or normalized.casefold() in seen:
            continue
        seen.add(normalized.casefold())
        unique.append(normalized)
    return unique


def _explanation(question: StoredQuestion) -> str:
    meaning = question.meaning or question.english_meaning
    return meaning

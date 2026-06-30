from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from app.services.gemini import generate_gemini_text


logger = logging.getLogger(__name__)

ALLOWED_CATEGORIES = {
    "Social",
    "Education",
    "Family",
    "Friendship",
    "Success",
    "Failure",
    "Leadership",
    "Honesty",
    "Wisdom",
    "Patience",
    "Money",
    "Time",
    "Work",
    "Kindness",
    "Responsibility",
    "Morality",
    "General",
}
MAX_GEMINI_RETRIES = 3
DEFAULT_MAX_CONCURRENT_GEMINI = 5


@dataclass(frozen=True)
class GeneratedMetadata:
    """Gemini-generated metadata for one proverb."""

    category: str
    keywords: list[str]
    failed: bool = False


def _build_metadata_prompt(proverb: str, meaning: str, english_meaning: str) -> str:
    return f"""
You are an expert in Myanmar Proverbs and Myanmar linguistics.

Given

- proverb
- Myanmar meaning
- English meaning

Generate

- one category
- 5 to 10 semantic keywords

Allowed Categories

Social
Education
Family
Friendship
Success
Failure
Leadership
Honesty
Wisdom
Patience
Money
Time
Work
Kindness
Responsibility
Morality
General

Return ONLY valid JSON.

Example

{{
    "category":"Social",
    "keywords":[
        "ချီးမွမ်း",
        "ကဲ့ရဲ့",
        "ဝေဖန်",
        "အပြစ်တင်",
        "ဂုဏ်သတင်း",
        "လူမှုဆက်ဆံရေး"
    ]
}}

Proverb:
{proverb}

Myanmar meaning:
{meaning}

English meaning:
{english_meaning}
""".strip()


def _parse_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from Gemini text, tolerating fenced responses."""

    cleaned = re.sub(r"```(?:json)?|```", "", text.strip(), flags=re.IGNORECASE)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Gemini response did not contain a JSON object.")

    parsed = json.loads(cleaned[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Gemini response JSON was not an object.")
    return parsed


def _normalize_metadata(payload: dict[str, Any], row_number: int) -> GeneratedMetadata:
    category = str(payload.get("category") or "General").strip()
    if category not in ALLOWED_CATEGORIES:
        logger.warning("Row %s returned unsupported category %r.", row_number, category)
        category = "General"

    raw_keywords = payload.get("keywords")
    if isinstance(raw_keywords, list):
        keywords = [str(keyword).strip() for keyword in raw_keywords if str(keyword).strip()]
    elif isinstance(raw_keywords, str):
        keywords = [keyword.strip() for keyword in raw_keywords.split(",") if keyword.strip()]
    else:
        keywords = []

    if len(keywords) < 5 or len(keywords) > 10:
        logger.warning("Row %s returned %s keywords; expected 5-10.", row_number, len(keywords))

    return GeneratedMetadata(category=category, keywords=keywords[:10])


def _fallback_metadata() -> GeneratedMetadata:
    return GeneratedMetadata(category="General", keywords=[], failed=True)


async def generate_metadata_for_pair(
    proverb: str,
    meaning: str,
    english_meaning: str,
    row_number: int,
    *,
    semaphore: asyncio.Semaphore,
) -> GeneratedMetadata:
    prompt = _build_metadata_prompt(proverb, meaning, english_meaning)
    last_error: Exception | None = None

    async with semaphore:
        for attempt in range(1, MAX_GEMINI_RETRIES + 1):
            try:
                raw_text = await asyncio.to_thread(generate_gemini_text, prompt)
                payload = _parse_json_object(raw_text)
                return _normalize_metadata(payload, row_number)
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                logger.exception(
                    "Metadata JSON parsing error for row %s on attempt %s/%s.",
                    row_number,
                    attempt,
                    MAX_GEMINI_RETRIES,
                )
            except Exception as exc:
                last_error = exc
                logger.exception(
                    "Gemini metadata error for row %s on attempt %s/%s.",
                    row_number,
                    attempt,
                    MAX_GEMINI_RETRIES,
                )

            if attempt < MAX_GEMINI_RETRIES:
                await asyncio.sleep(2**attempt)

    logger.error("Metadata generation failed for row %s: %s", row_number, last_error)
    return _fallback_metadata()


async def generate_metadata_for_dataset(
    rows: list[tuple[str, str, str]],
    *,
    max_concurrent: int = DEFAULT_MAX_CONCURRENT_GEMINI,
) -> list[GeneratedMetadata]:
    """Generate metadata for all merged proverb rows with bounded Gemini concurrency."""

    if not rows:
        return []

    semaphore = asyncio.Semaphore(max_concurrent)
    tasks = [
        generate_metadata_for_pair(
            proverb,
            meaning,
            english_meaning,
            row_number,
            semaphore=semaphore,
        )
        for row_number, (proverb, meaning, english_meaning) in enumerate(rows, start=1)
    ]

    return await asyncio.gather(*tasks)

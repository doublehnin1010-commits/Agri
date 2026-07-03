from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from app.core.config import settings
from app.services.llm_service import agenerate_utility_response


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

_THINK_OPEN = "<" + "think" + ">"
_THINK_CLOSE = "<" + "/" + "think" + ">"
_THINKING_BLOCK_RES = (
    re.compile(
        re.escape(_THINK_OPEN) + r".*?" + re.escape(_THINK_CLOSE),
        re.DOTALL | re.IGNORECASE,
    ),
    re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE),
)
_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*|```", re.IGNORECASE)
_RAW_RESPONSE_LOG_LIMIT = 4000
ProgressCallback = Callable[[int, int], None]


@dataclass(frozen=True)
class GeneratedMetadata:
    """LLM-generated metadata for one proverb."""

    category: str
    keywords: list[str]
    failed: bool = False


def metadata_batch_size() -> int:
    return settings.metadata_batch_size


def metadata_max_concurrent() -> int:
    return settings.metadata_max_concurrent


def metadata_max_retries() -> int:
    return settings.metadata_max_retries


def _build_batch_metadata_prompt(rows: Sequence[tuple[int, str, str, str]]) -> str:
    records = [
        {
            "index": row_number,
            "proverb": proverb,
            "meaning": meaning,
            "english_meaning": english_meaning,
        }
        for row_number, proverb, meaning, english_meaning in rows
    ]
    records_json = json.dumps(records, ensure_ascii=False, indent=2)
    allowed = ", ".join(sorted(ALLOWED_CATEGORIES))

    return f"""You are an expert in Myanmar Proverbs and Myanmar linguistics.

Task: For EVERY record below, output one category and 5-10 semantic keywords in Myanmar.
Do NOT generate or rewrite English meanings.

STRICT OUTPUT RULES — violating any rule is a failure:
- Return ONLY JSON. Nothing else.
- Never explain your reasoning.
- Never use markdown.
- Never use code fences (no ```).
- Never use {_THINK_OPEN} or <think> tags.
- Never write any text before the JSON.
- Never write any text after the JSON.
- The response MUST start with the character {{
- The response MUST end with the character }}
- If uncertain, still return valid JSON using category "General" and your best keywords.

Allowed categories: {allowed}

Required JSON shape (return one object per input record, same index values):
{{
  "items": [
    {{
      "index": 1,
      "category": "Social",
      "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
    }}
  ]
}}

Records:
{records_json}"""


def _strip_thinking_blocks(text: str) -> str:
    cleaned = text
    for pattern in _THINKING_BLOCK_RES:
        cleaned = pattern.sub("", cleaned)
    return cleaned


def _strip_code_fences(text: str) -> str:
    return _CODE_FENCE_RE.sub("", text)


def _extract_json_object(text: str) -> str:
    """Return the outermost JSON object substring from noisy LLM text."""

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM response did not contain a JSON object.")

    return text[start : end + 1]


def _parse_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from LLM text after removing common noise."""

    cleaned = _strip_thinking_blocks(text.strip())
    cleaned = _strip_code_fences(cleaned).strip()

    if not cleaned:
        raise ValueError("LLM response was empty after cleaning.")

    candidates: list[str] = []
    if cleaned.startswith("{"):
        candidates.append(cleaned)
    try:
        candidates.append(_extract_json_object(cleaned))
    except ValueError:
        if not candidates:
            raise

    seen: set[str] = set()
    last_error: json.JSONDecodeError | ValueError | None = None

    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)

        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue

        if not isinstance(parsed, dict):
            raise ValueError("LLM response JSON was not an object.")
        return parsed

    if last_error is not None:
        raise ValueError(f"LLM response JSON was invalid: {last_error}") from last_error
    raise ValueError("LLM response did not contain a JSON object.")


def _log_raw_response(batch_index: int, raw_text: str, *, attempt: int, reason: str) -> None:
    preview = raw_text.strip()
    if len(preview) > _RAW_RESPONSE_LOG_LIMIT:
        preview = f"{preview[:_RAW_RESPONSE_LOG_LIMIT]}... [truncated]"

    logger.error(
        "Metadata batch %s attempt %s/%s %s. Raw Ollama response:\n%s",
        batch_index,
        attempt,
        metadata_max_retries(),
        reason,
        preview or "<empty>",
    )


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


def _normalize_batch_response(
    payload: dict[str, Any],
    rows: Sequence[tuple[int, str, str, str]],
) -> dict[int, GeneratedMetadata]:
    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        raise ValueError("LLM batch response must contain an items list.")

    expected_indexes = {row_number for row_number, *_ in rows}
    metadata_by_index: dict[int, GeneratedMetadata] = {}
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        try:
            row_number = int(item.get("index"))
        except (TypeError, ValueError):
            continue
        if row_number not in expected_indexes:
            continue
        metadata_by_index[row_number] = _normalize_metadata(item, row_number)

    missing = expected_indexes - set(metadata_by_index)
    if missing:
        raise ValueError(f"LLM batch response missed indexes: {sorted(missing)}")

    return metadata_by_index


async def generate_metadata_for_batch(
    rows: Sequence[tuple[int, str, str, str]],
    *,
    semaphore: asyncio.Semaphore,
    batch_index: int = 0,
) -> list[tuple[int, GeneratedMetadata]]:
    prompt = _build_batch_metadata_prompt(rows)
    row_range = f"{rows[0][0]}-{rows[-1][0]}"
    last_error: Exception | None = None
    max_retries = metadata_max_retries()

    logger.info(
        "Metadata batch %s started (rows %s, size=%s).",
        batch_index,
        row_range,
        len(rows),
    )

    async with semaphore:
        for attempt in range(1, max_retries + 1):
            started_at = time.perf_counter()
            raw_text = ""

            try:
                raw_text = await agenerate_utility_response(prompt)
                if not raw_text.strip():
                    raise ValueError("Ollama returned an empty response.")

                payload = _parse_json_object(raw_text)
                normalized = _normalize_batch_response(payload, rows)
                elapsed = round(time.perf_counter() - started_at, 2)

                logger.info(
                    "Metadata batch %s succeeded on attempt %s/%s in %ss (rows %s).",
                    batch_index,
                    attempt,
                    max_retries,
                    elapsed,
                    row_range,
                )
                return [(row_number, normalized[row_number]) for row_number, *_ in rows]
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                elapsed = round(time.perf_counter() - started_at, 2)
                _log_raw_response(
                    batch_index,
                    raw_text,
                    attempt=attempt,
                    reason=f"JSON parse failed after {elapsed}s ({exc})",
                )
            except Exception as exc:
                last_error = exc
                elapsed = round(time.perf_counter() - started_at, 2)
                logger.exception(
                    "Metadata batch %s Ollama error on attempt %s/%s after %ss (rows %s).",
                    batch_index,
                    attempt,
                    max_retries,
                    elapsed,
                    row_range,
                )
                if raw_text.strip():
                    _log_raw_response(
                        batch_index,
                        raw_text,
                        attempt=attempt,
                        reason=f"Ollama call failed after {elapsed}s ({exc})",
                    )

            if attempt < max_retries:
                backoff = 2**attempt
                logger.warning(
                    "Metadata batch %s retrying in %ss (attempt %s/%s failed).",
                    batch_index,
                    backoff,
                    attempt,
                    max_retries,
                )
                await asyncio.sleep(backoff)

    logger.error(
        "Metadata batch %s exhausted retries for rows %s; using fallback metadata. Last error: %s",
        batch_index,
        row_range,
        last_error,
    )
    return [(row_number, _fallback_metadata()) for row_number, *_ in rows]


async def generate_metadata_for_dataset(
    rows: Sequence[tuple[str, str, str]],
    *,
    batch_size: int | None = None,
    max_concurrent: int | None = None,
    progress_callback: ProgressCallback | None = None,
) -> list[GeneratedMetadata]:
    """Generate metadata in configurable batches with bounded Ollama concurrency."""

    resolved_batch_size = batch_size if batch_size is not None else metadata_batch_size()
    resolved_max_concurrent = max_concurrent if max_concurrent is not None else metadata_max_concurrent()

    if resolved_batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")
    if resolved_max_concurrent <= 0:
        raise ValueError("max_concurrent must be greater than zero")
    if not rows:
        return []

    indexed_rows = [
        (row_number, proverb, meaning, english_meaning)
        for row_number, (proverb, meaning, english_meaning) in enumerate(rows, start=1)
    ]
    batches = [
        indexed_rows[index : index + resolved_batch_size]
        for index in range(0, len(indexed_rows), resolved_batch_size)
    ]

    semaphore = asyncio.Semaphore(resolved_max_concurrent)
    metadata_rows: list[GeneratedMetadata | None] = [None] * len(indexed_rows)
    processed = 0

    tasks = [
        asyncio.create_task(
            generate_metadata_for_batch(batch, semaphore=semaphore, batch_index=batch_index)
        )
        for batch_index, batch in enumerate(batches, start=1)
    ]

    for task in asyncio.as_completed(tasks):
        batch_result = await task
        for row_number, metadata in batch_result:
            metadata_rows[row_number - 1] = metadata
        processed += len(batch_result)
        if progress_callback is not None:
            progress_callback(processed, len(indexed_rows))

    return [metadata or _fallback_metadata() for metadata in metadata_rows]

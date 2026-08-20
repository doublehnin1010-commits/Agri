from __future__ import annotations

import logging
import re
import threading
import unicodedata
from collections import OrderedDict

from app.core.config import settings
from app.services.llm_service import invoke_text


logger = logging.getLogger(__name__)

MYANMAR_NORMALIZER_SYSTEM_PROMPT = """You are a Myanmar language normalization engine.

Your task is only converting romanized Myanmar phonetic text into Myanmar Unicode.

Rules:
* Return only Myanmar Unicode text.
* Do not explain.
* Do not translate.
* Do not add quotes.
* Preserve original meaning."""

MYANMAR_NORMALIZER_USER_PROMPT = """Convert romanized Myanmar phonetic text into Myanmar Unicode.

Examples:
mÃ¬ je taun ca pa le -> á€„á€«á€¸á€™á€› á€›á€±á€á€»á€­á€¯á€¸á€•á€¼á€”á€º
mingalar par -> á€™á€„á€ºá€¹á€‚á€œá€¬á€•á€«

Input:
{text}

Output:"""

_MYANMAR_RE = re.compile(r"[\u1000-\u109f\uaa60-\uaa7f\ua9e0-\ua9ff]")
_LATIN_RE = re.compile(r"[A-Za-z\u00c0-\u024f]")
_TOKEN_RE = re.compile(r"[A-Za-z\u00c0-\u024f']+")
_STRONG_PHONETIC_RE = re.compile(r"[\u00e0-\u00ff\u0100-\u024f]")

# Common tokens in informal romanized Myanmar. A conservative threshold is
# used below so ordinary English text is not sent through Myanmar normalization.
_PHONETIC_MARKERS = frozenset(
    {
        "mingalar",
        "par",
        "ma",
        "ka",
        "ko",
        "lo",
        "le",
        "lar",
        "nay",
        "nei",
        "shi",
        "chin",
        "de",
        "tal",
        "pyan",
        "yae",
        "kya",
        "hma",
        "yin",
        "taw",
        "ba",
        "pa",
        "sa",
        "taun",
    }
)

_CACHE_MAX_ITEMS = 512
_KNOWN_NORMALIZATIONS = {
    "mÃ¬ je taun ca pa le": "á€„á€«á€¸á€™á€› á€›á€±á€á€»á€­á€¯á€¸á€•á€¼á€”á€º",
    "mingalar par": "á€™á€„á€ºá€¹á€‚á€œá€¬á€•á€«",
}
_cache: OrderedDict[str, str] = OrderedDict()
_cache_lock = threading.Lock()


def contains_myanmar_unicode(text: str) -> bool:
    return bool(_MYANMAR_RE.search(text))


def looks_like_romanized_myanmar(text: str) -> bool:
    candidate = unicodedata.normalize("NFKC", text).strip()
    if not candidate or contains_myanmar_unicode(candidate):
        return False

    tokens = [token.casefold() for token in _TOKEN_RE.findall(candidate)]
    if not 2 <= len(tokens) <= 30:
        return False

    if _STRONG_PHONETIC_RE.search(candidate):
        return True

    marker_count = sum(token in _PHONETIC_MARKERS for token in tokens)
    return marker_count >= 2 and marker_count / len(tokens) >= 0.5


def normalize_myanmar_text(text: str) -> str:
    original = text.strip()
    if not original or contains_myanmar_unicode(original):
        return original
    if not looks_like_romanized_myanmar(original):
        return original

    cache_key = unicodedata.normalize("NFKC", original).casefold()
    known = _KNOWN_NORMALIZATIONS.get(cache_key)
    if known:
        return known

    with _cache_lock:
        cached = _cache.get(cache_key)
        if cached is not None:
            _cache.move_to_end(cache_key)
            return cached

    try:
        generated = invoke_text(
            MYANMAR_NORMALIZER_USER_PROMPT.format(text=original),
            system_instruction=MYANMAR_NORMALIZER_SYSTEM_PROMPT,
            model=settings.chat_model,
            reasoning=False,
        )
    except Exception:
        logger.exception("Myanmar text normalization failed; using raw Whisper output")
        return original

    normalized = _clean_model_output(generated)
    if not _is_confident_normalization(original, normalized):
        logger.warning("Rejected low-confidence Myanmar normalization output: %r", generated)
        return original

    with _cache_lock:
        _cache[cache_key] = normalized
        _cache.move_to_end(cache_key)
        while len(_cache) > _CACHE_MAX_ITEMS:
            _cache.popitem(last=False)
    return normalized


def _clean_model_output(text: str) -> str:
    cleaned = unicodedata.normalize("NFC", text).strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        cleaned = cleaned[3:-3].strip()
        if cleaned.lower().startswith("text\n"):
            cleaned = cleaned[5:].strip()
    return cleaned.strip("\"'` \t\r\n")


def _is_confident_normalization(source: str, candidate: str) -> bool:
    if not candidate or not contains_myanmar_unicode(candidate):
        return False
    if _LATIN_RE.search(candidate):
        return False

    source_length = max(1, len(source))
    return source_length * 0.25 <= len(candidate) <= source_length * 4


def _clear_normalization_cache() -> None:
    """Clear process-local state; intended for tests and controlled reloads."""

    with _cache_lock:
        _cache.clear()


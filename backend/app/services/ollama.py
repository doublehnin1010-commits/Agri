from __future__ import annotations

import json
import logging
import re
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from app.core.config import settings


_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_HTTP_OPENER = build_opener()
logger = logging.getLogger(__name__)


def configure_ollama() -> None:
    if not settings.chat_model.strip():
        raise RuntimeError("CHAT_MODEL must not be empty")
    if not settings.utility_model.strip():
        raise RuntimeError("UTILITY_MODEL must not be empty")
    if settings.embedding_model.strip() in {settings.chat_model.strip(), settings.utility_model.strip()}:
        raise RuntimeError("EMBEDDING_MODEL must not be used as a chat model")


def generate_chat_response(prompt: str) -> str:
    """Generate final user-facing RAG answers with the reasoning model."""

    return _send_request(
        prompt=prompt,
        model=settings.chat_model,
        temperature=settings.chat_temperature,
        num_predict=settings.chat_num_predict,
        num_ctx=settings.chat_num_ctx,
    )


def generate_utility_response(prompt: str) -> str:
    """Generate lightweight NLP/JSON utility outputs with the fast model."""

    return _send_request(
        prompt=prompt,
        model=settings.utility_model,
        temperature=settings.utility_temperature,
        num_predict=settings.utility_num_predict,
        num_ctx=settings.utility_num_ctx,
    )


def generate_answer(prompt: str) -> str:
    """Backward-compatible utility generation entry point."""

    return generate_utility_response(prompt)


def _send_request(
    *,
    prompt: str,
    model: str,
    temperature: float,
    num_predict: int,
    num_ctx: int,
) -> str:
    if model.strip() == settings.embedding_model.strip():
        raise RuntimeError("Embedding model must not be used for chat generation")

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
            "num_ctx": num_ctx,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    request = Request(
        f"{settings.ollama_base_url.rstrip('/')}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    started_at = time.perf_counter()
    try:
        with _HTTP_OPENER.open(request, timeout=settings.ollama_timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError("Ollama generation failed") from exc

    text = body.get("response")
    if not text:
        raise RuntimeError("Ollama generation returned empty text")

    cleaned = _strip_thinking(text).strip()
    logger.info(
        "Ollama inference | Model: %s | Time: %.1f ms | Prompt Tokens: %s | Response Length: %s",
        model,
        (time.perf_counter() - started_at) * 1000,
        body.get("prompt_eval_count"),
        len(cleaned),
    )
    return cleaned


def safe_json_from_llm(text: str) -> dict[str, Any]:
    cleaned = _strip_thinking(text).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM did not return JSON")

    return json.loads(cleaned[start : end + 1])


def _strip_thinking(text: str) -> str:
    return _THINK_BLOCK_RE.sub("", text)

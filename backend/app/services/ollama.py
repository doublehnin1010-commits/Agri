from __future__ import annotations

import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import settings


_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def configure_ollama() -> None:
    if not settings.ollama_model.strip():
        raise RuntimeError("OLLAMA_MODEL must not be empty")


def generate_answer(prompt: str) -> str:
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": settings.ollama_temperature,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    request = Request(
        f"{settings.ollama_base_url.rstrip('/')}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=settings.ollama_timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError("Ollama generation failed") from exc

    text = body.get("response")
    if not text:
        raise RuntimeError("Ollama generation returned empty text")
    return _strip_thinking(text).strip()


def safe_json_from_llm(text: str) -> dict[str, Any]:
    cleaned = _strip_thinking(text).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM did not return JSON")

    return json.loads(cleaned[start : end + 1])


def _strip_thinking(text: str) -> str:
    return _THINK_BLOCK_RE.sub("", text)

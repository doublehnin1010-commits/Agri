from __future__ import annotations

import json
import re
from typing import Any

from app.services.gemini import generate_gemini_text, validate_gemini_config

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

DATASET_ONLY_SYSTEM_INSTRUCTION = """
You are a Myanmar Proverbs Tutor for children.

Strict rules:
1. Use ONLY the retrieved dataset context provided in the user message.
2. Never use outside knowledge, general facts, programming, science, history, politics, or other topics.
3. Never guess, invent, or create proverbs, meanings, or examples.
4. If the context is empty or not relevant, return the standard not-found response exactly as instructed.
5. Stay focused on Myanmar proverbs only.
""".strip()


def configure_llm() -> None:
    validate_gemini_config()


def generate_answer(prompt: str, *, system_instruction: str | None = None) -> str:
    instruction = system_instruction or DATASET_ONLY_SYSTEM_INSTRUCTION
    return generate_gemini_text(prompt, system_instruction=instruction)


def safe_json_from_llm(text: str) -> dict[str, Any]:
    cleaned = _strip_thinking(text).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM did not return JSON")

    return json.loads(cleaned[start : end + 1])


def _strip_thinking(text: str) -> str:
    return _THINK_BLOCK_RE.sub("", text)

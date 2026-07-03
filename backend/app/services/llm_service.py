from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama

from app.core.config import settings


_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
logger = logging.getLogger(__name__)

DATASET_ONLY_SYSTEM_INSTRUCTION = """
You are a Myanmar Proverbs Tutor for children.

Strict rules:
1. Use ONLY the retrieved dataset context provided in the user message.
2. Never use outside knowledge, general facts, programming, science, history, politics, or other topics.
3. Never guess, invent, or create proverbs, meanings, or examples.
4. If the context is empty or not relevant, return the standard not-found response exactly as instructed.
5. Stay focused on Myanmar proverbs only.
""".strip()

_llms: dict[str, ChatOllama] = {}


def get_llm(model: str | None = None) -> ChatOllama:
    """Return a shared ChatOllama singleton for the requested model."""

    model_name = (model or settings.utility_model).strip()
    if not model_name:
        raise RuntimeError("OLLAMA_MODEL must not be empty")
    if model_name == settings.embedding_model.strip():
        raise RuntimeError("Embedding model must not be used for chat generation")

    if model_name not in _llms:
        is_chat_model = model_name == settings.chat_model
        num_predict = settings.chat_num_predict if is_chat_model else settings.utility_num_predict
        num_ctx = settings.chat_num_ctx if is_chat_model else settings.utility_num_ctx
        temperature = settings.chat_temperature if is_chat_model else settings.utility_temperature
        _llms[model_name] = ChatOllama(
            model=model_name,
            base_url=settings.ollama_base_url,
            temperature=temperature,
            num_predict=num_predict,
            num_ctx=num_ctx,
        )
    return _llms[model_name]


def get_chat_llm() -> ChatOllama:
    return get_llm(settings.chat_model)


def get_utility_llm() -> ChatOllama:
    return get_llm(settings.utility_model)


def configure_llm() -> None:
    """Eagerly initialize the chat model."""

    get_utility_llm()
    get_chat_llm()


def generate_answer(prompt: str, *, system_instruction: str | None = None) -> str:
    return generate_utility_response(prompt, system_instruction=system_instruction)


def generate_chat_response(prompt: str, *, system_instruction: str | None = None) -> str:
    instruction = system_instruction or DATASET_ONLY_SYSTEM_INSTRUCTION
    return invoke_text(prompt, system_instruction=instruction, model=settings.chat_model)


def generate_utility_response(prompt: str, *, system_instruction: str | None = None) -> str:
    return invoke_text(prompt, system_instruction=system_instruction, model=settings.utility_model)


async def agenerate_chat_response(prompt: str, *, system_instruction: str | None = None) -> str:
    instruction = system_instruction or DATASET_ONLY_SYSTEM_INSTRUCTION
    return await ainvoke_text(prompt, system_instruction=instruction, model=settings.chat_model)


async def agenerate_utility_response(prompt: str, *, system_instruction: str | None = None) -> str:
    return await ainvoke_text(prompt, system_instruction=system_instruction, model=settings.utility_model)


def invoke_text(prompt: str, *, system_instruction: str | None = None, model: str | None = None) -> str:
    """Invoke ChatOllama and return plain text."""

    messages: list[SystemMessage | HumanMessage] = []
    if system_instruction:
        messages.append(SystemMessage(content=system_instruction))
    messages.append(HumanMessage(content=prompt))

    selected_model = (model or settings.utility_model).strip()
    started_at = time.perf_counter()
    response = get_llm(selected_model).invoke(messages)
    return _response_text(response, selected_model, started_at)


async def ainvoke_text(prompt: str, *, system_instruction: str | None = None, model: str | None = None) -> str:
    """Async invoke ChatOllama and return plain text."""

    messages: list[SystemMessage | HumanMessage] = []
    if system_instruction:
        messages.append(SystemMessage(content=system_instruction))
    messages.append(HumanMessage(content=prompt))

    selected_model = (model or settings.utility_model).strip()
    started_at = time.perf_counter()
    response = await get_llm(selected_model).ainvoke(messages)
    return _response_text(response, selected_model, started_at)


def _response_text(response: Any, model: str, started_at: float) -> str:
    content = response.content
    if isinstance(content, str):
        text = _strip_thinking(content).strip()
    else:
        text = _strip_thinking(str(content)).strip()

    usage = getattr(response, "usage_metadata", None) or {}
    response_metadata = getattr(response, "response_metadata", None) or {}
    prompt_tokens = usage.get("input_tokens") or response_metadata.get("prompt_eval_count")
    logger.info(
        "Ollama inference | Model: %s | Time: %.1f ms | Prompt Tokens: %s | Response Length: %s",
        model,
        (time.perf_counter() - started_at) * 1000,
        prompt_tokens,
        len(text),
    )
    return text


def invoke_chain(chain, inputs: dict[str, Any]) -> str:
    """Run a LangChain runnable and return plain text."""

    result = chain.invoke(inputs)
    if isinstance(result, str):
        return _strip_thinking(result).strip()
    return _strip_thinking(str(result)).strip()


def get_str_output_parser() -> StrOutputParser:
    return StrOutputParser()


def safe_json_from_llm(text: str) -> dict[str, Any]:
    cleaned = _strip_thinking(text).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM did not return JSON")

    return json.loads(cleaned[start : end + 1])


def _strip_thinking(text: str) -> str:
    return _THINK_BLOCK_RE.sub("", text)

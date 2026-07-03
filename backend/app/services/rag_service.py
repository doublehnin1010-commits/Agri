from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from app.core.config import settings
from app.services.llm_service import (
    agenerate_utility_response,
    generate_utility_response,
    get_chat_llm,
    get_str_output_parser,
    safe_json_from_llm,
)
from app.services.retriever_service import get_retriever


logger = logging.getLogger(__name__)


INTENT_CLASSIFIER_SYSTEM_INSTRUCTION = """
You classify intent for Myanmar Proverbs AI Tutor.

Return JSON only. Do not answer the user.
Use semantic understanding instead of exact phrase matching.

Valid intents:

- greeting:
  The user greets the assistant.
  Examples:
  "မင်္ဂလာပါ"
  "Hello"
  "Hi"

- role:
  The user asks who the assistant is, what the system does, or what it can help with.
  Examples:
  "မင်းဘယ်သူလဲ"
  "What can you do?"
  "ဒီ system ကဘာလဲ"

- proverb_question:
  The user asks for a proverb, the meaning of a proverb, an explanation, or a proverb related to a situation, feeling, topic, or event.
  Examples:
  "ငါးနဲ့ပတ်သက်တဲ့ စကားပုံ"
  "ဦးလှကို လူတွေက ကဲ့ရဲ့နေကြတယ်"
  "ဒီအခြေအနေနဲ့ လိုက်ဖက်တဲ့ စကားပုံရှိလား"
  "ချီးမွမ်း ခုနှစ်ရက် ကဲ့ရဲ့ ခုနှစ်ရက် ဆိုတာဘာလဲ"

- proverb_only:
  The user wants only the proverb without any explanation.
  Examples:
  "စကားပုံပဲပြော"
  "Only proverb"
  "Which proverb fits?"

- translate_previous_to_myanmar:
  The user asks to translate or explain the previous answer in Myanmar/Burmese.
  Examples:
  "မြန်မာလိုပြန်ရှင်းပေး"
  "Translate to Burmese"

- translate_previous_to_english:
  The user asks to translate or explain the previous answer in English.
  Examples:
  "Explain in English"
  "Translate to English"

- thanks:
  The user expresses gratitude.
  Examples:
  "ကျေးဇူးတင်ပါတယ်"
  "Thanks"
  "Thank you"

- goodbye:
  The user ends the conversation.
  Examples:
  "Bye"
  "Goodbye"
  "နောက်မှတွေ့မယ်"

- unrelated:
  The user's request is not related to Myanmar proverbs.
  Examples:
  "Write Python code"
  "What is cloud computing?"
  "Solve this math problem"

Valid languages:

- my:
  The response should be in Myanmar/Burmese.

- en:
  The response should be in English.

Output format:

{
    "intent": "<intent>",
    "language": "<my|en>"
}

Only return valid JSON.
Do not include markdown.
Do not answer the user's question.
""".strip()

DATASET_ONLY_SYSTEM_INSTRUCTION = """
You are a Myanmar Proverbs Tutor for children.

Strict rules:
1. Use ONLY the retrieved dataset context provided in the user message.
2. Never use outside knowledge, general facts, programming, science, history, politics, or other topics.
3. Never guess, invent, or create proverbs, meanings, or examples.
4. If the context is empty or not relevant, return the standard not-found response exactly as instructed.
5. Stay focused on Myanmar proverbs only.
""".strip()

ANSWER_PROMPT_EN = ChatPromptTemplate.from_messages(
    [
        ("system", DATASET_ONLY_SYSTEM_INSTRUCTION),
        (
            "human",
            """You are a Myanmar Proverbs AI Tutor.

Use ONLY the retrieved dataset context below.
Never use outside knowledge, general facts, programming, science, history, politics, or any topic outside Myanmar proverbs.
Never guess or invent proverbs or meanings.
If there is no exact proverb match, choose the closest meaning from the context only.
Return the best matching proverb with a warm, natural English explanation.
Explain like a kind teacher answering children.
Do not copy the source meaning word-for-word.
The meaning_simple_mm value must start with "In simple words," or "This proverb means".
Use simple, friendly language and 1-2 short sentences.
If the context does not contain a relevant proverb, return null for proverb and the standard not-found message.

Context:
{context}

User Question:
{question}

Answer in English only, using JSON with these fields:
{{
  "proverb": "...",
  "meaning_simple_mm": "...",
  "example_mm": "...",
  "sources": [...]
}}""",
        ),
    ]
)

ANSWER_PROMPT_MY = ChatPromptTemplate.from_messages(
    [
        ("system", DATASET_ONLY_SYSTEM_INSTRUCTION),
        (
            "human",
            """You are a Myanmar Proverbs AI Tutor.

Use ONLY the retrieved dataset context below.
Never use outside knowledge, general facts, programming, science, history, politics, or any topic outside Myanmar proverbs.
Never guess or invent proverbs or meanings.
If there is no exact proverb match, choose the closest meaning from the context only.
Return the best matching proverb with a warm, natural Burmese explanation.
Explain like a kind teacher answering children.
Do not copy the source meaning word-for-word.
The meaning_simple_mm value must start with "ကလေးတို့ရေ၊" or "ဆိုလိုတာက".
Use simple, friendly language and 1-2 short sentences.
If the context does not contain a relevant proverb, return null for proverb and the standard not-found message.

Context:
{context}

User Question:
{question}

Answer in Burmese only, using JSON with these fields:
{{
  "proverb": "...",
  "meaning_simple_mm": "...",
  "example_mm": "...",
  "sources": [...]
}}""",
        ),
    ]
)

FAST_DATASET_ONLY_SYSTEM_INSTRUCTION = """
You are a Myanmar Proverbs Tutor.
Use only the provided context. Do not invent proverbs or meanings.
Return JSON only. If context is empty or irrelevant, set proverb to null.
""".strip()

ANSWER_PROMPT_EN = ChatPromptTemplate.from_messages(
    [
        ("system", FAST_DATASET_ONLY_SYSTEM_INSTRUCTION),
        (
            "human",
            """Context JSON:
{context}

Question: {question}

Answer in English. Pick the best context item only. Use 1-2 short teacher-friendly sentences.
meaning_simple_mm must start with "In simple words," or "This proverb means".
Return exactly this JSON:
{{
  "proverb": "...",
  "meaning_simple_mm": "...",
  "example_mm": "...",
  "sources": [...]
}}""",
        ),
    ]
)

ANSWER_PROMPT_MY = ChatPromptTemplate.from_messages(
    [
        ("system", FAST_DATASET_ONLY_SYSTEM_INSTRUCTION),
        (
            "human",
            """Context JSON:
{context}

Question: {question}

Answer in Burmese. Pick the best context item only. Use 1-2 short teacher-friendly sentences.
meaning_simple_mm must start with "ကလေးတို့ရေ၊" or "ဆိုလိုတာက".
Return exactly this JSON:
{{
  "proverb": "...",
  "meaning_simple_mm": "...",
  "example_mm": "...",
  "sources": [...]
}}""",
        ),
    ]
)

_rag_chain = None
_answer_chains: dict[tuple[str, str], Any] = {}

def _format_sources_as_context(sources: list[dict[str, Any]]) -> str:
    context_items = []
    for index, source in enumerate(sources[: settings.rag_top_k], start=1):
        context_items.append(
            {
                "id": index,
                "proverb": source.get("proverb"),
                "meaning": source.get("meaning"),
                "english_meaning": source.get("english_meaning"),
                "example": source.get("example"),
            }
        )
    return json.dumps(context_items, ensure_ascii=False, separators=(",", ":"))


def _select_answer_prompt(language: str) -> ChatPromptTemplate:
    return ANSWER_PROMPT_EN if language == "en" else ANSWER_PROMPT_MY


def _documents_to_sources(documents: list[Any]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for doc in documents:
        metadata = doc.metadata or {}
        sources.append(
            {
                "keyword": metadata.get("keyword"),
                "keywords": metadata.get("keywords"),
                "category": metadata.get("category"),
                "proverb": metadata.get("proverb"),
                "meaning": metadata.get("meaning"),
                "english_meaning": metadata.get("english_meaning"),
                "example": metadata.get("example"),
                "score": metadata.get("score"),
                "similarity": metadata.get("similarity"),
            }
        )
    return sources


def _elapsed_ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000


def select_chat_model(question: str, *, language: str = "my", intent: str | None = None) -> str:
    """Final RAG answer generation always uses the configured chat model."""

    return settings.chat_model


def _get_answer_chain(language: str, model: str | None = None):
    model_name = model or settings.chat_model
    key = (language, model_name)
    if key not in _answer_chains:
        _answer_chains[key] = _select_answer_prompt(language) | get_chat_llm() | get_str_output_parser()
    return _answer_chains[key]


def _build_rag_chain():
    retriever = get_retriever()

    def _prepare_generation_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
        question = inputs["question"]
        language = inputs.get("language") or "my"
        documents = retriever.invoke(question)
        sources = _documents_to_sources(documents)
        return {
            "question": question,
            "language": language,
            "sources": sources,
            "context": _format_sources_as_context(sources),
        }

    def _run_generation(inputs: dict[str, Any]) -> dict[str, Any]:
        model = select_chat_model(inputs["question"], language=inputs["language"])
        text = _get_answer_chain(inputs["language"], model).invoke(
            {
                "context": inputs["context"],
                "question": inputs["question"],
            }
        )
        return {
            "sources": inputs["sources"],
            "text": text,
        }

    return RunnablePassthrough() | RunnableLambda(_prepare_generation_inputs) | RunnableLambda(_run_generation)


def get_rag_chain():
    global _rag_chain
    if _rag_chain is None:
        _rag_chain = _build_rag_chain()
    return _rag_chain


def run_rag_chain(question: str, language: str = "my") -> dict[str, Any]:
    """Run the LangChain RAG pipeline and return sources plus raw LLM text."""

    return asyncio.run(arun_rag_chain(question, language=language))


async def arun_rag_chain(question: str, language: str = "my") -> dict[str, Any]:
    """Async RAG pipeline using cached retriever and prompt chains."""

    total_start = time.perf_counter()
    retrieve_start = time.perf_counter()
    documents = await get_retriever().ainvoke(question)
    sources = _documents_to_sources(documents)
    retrieve_ms = _elapsed_ms(retrieve_start)

    generation_start = time.perf_counter()
    model = select_chat_model(question, language=language)
    text = await _get_answer_chain(language, model).ainvoke(
        {
            "context": _format_sources_as_context(sources),
            "question": question,
        }
    )
    generation_ms = _elapsed_ms(generation_start)
    logger.info(
        "RAG timing | Model: %s | Retrieval: %.1f ms | LLM Generation: %.1f ms | Total Request: %.1f ms",
        model,
        retrieve_ms,
        generation_ms,
        _elapsed_ms(total_start),
    )

    return {
        "sources": sources,
        "text": text,
    }


def parse_rag_answer(text: str) -> dict[str, Any]:
    return safe_json_from_llm(text)


def classify_intent(question: str) -> dict[str, Any]:
    prompt = f"""
Classify this user message for Myanmar Proverbs AI Tutor.

User message:
{question}

Return JSON exactly in this shape:
{{
  "intent": "role | translate_previous_to_myanmar | proverb_only | proverb_question",
  "language": "my | en"
}}
"""
    raw = generate_utility_response(prompt, system_instruction=INTENT_CLASSIFIER_SYSTEM_INSTRUCTION)
    return safe_json_from_llm(raw)


async def aclassify_intent(question: str) -> dict[str, Any]:
    prompt = f"""
Classify this user message for Myanmar Proverbs AI Tutor.

User message:
{question}

Return JSON exactly in this shape:
{{
  "intent": "role | translate_previous_to_myanmar | proverb_only | proverb_question",
  "language": "my | en"
}}
"""
    raw = await agenerate_utility_response(prompt, system_instruction=INTENT_CLASSIFIER_SYSTEM_INSTRUCTION)
    return safe_json_from_llm(raw)

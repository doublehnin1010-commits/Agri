from __future__ import annotations

import hashlib
import re
from typing import Any

from app.core.config import settings
from app.db.chroma import get_collection
from app.services.ollama import generate_answer, safe_json_from_llm
from app.services.guardrails import (
    is_context_relevant,
    validate_question,
    create_guardrailed_answer,
    create_no_result_answer,
    is_answer_valid,
)


def _row_id(keyword: str | None, proverb: str) -> str:
    raw = f"{keyword or ''}||{proverb}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def _normalize_row(row: dict[str, Any]) -> dict[str, str | None]:
    keyword = (row.get("keyword") or "").strip() or None
    proverb = (row.get("proverb") or "").strip()
    meaning = (row.get("meaning") or "").strip() or None
    example = (row.get("example") or "").strip() or None
    if not proverb:
        raise ValueError("proverb is required")
    return {"keyword": keyword, "proverb": proverb, "meaning": meaning, "example": example}


def _build_chroma_record(row: dict[str, str | None]) -> tuple[str, str, dict[str, Any]]:
    keyword = row["keyword"]
    proverb = row["proverb"]
    meaning = row["meaning"]
    example = row["example"]
    doc = f"keyword: {keyword or ''}\nproverb: {proverb}\nmeaning: {meaning or ''}\nexample: {example or ''}"
    metadata = {
        "keyword": keyword,
        "proverb": proverb,
        "meaning": meaning,
        "example": example,
    }
    return _row_id(keyword, proverb), doc, metadata


def add_proverb(row: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_row(row)
    proverb_id, doc, metadata = _build_chroma_record(normalized)
    col = get_collection()
    col.upsert(ids=[proverb_id], documents=[doc], metadatas=[metadata])
    return {"id": proverb_id, **normalized}


def update_proverb(proverb_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    col = get_collection()
    existing = col.get(ids=[proverb_id], include=["metadatas"])
    metadatas = existing.get("metadatas") or []
    if not metadatas or not metadatas[0]:
        raise ValueError("Proverb not found")

    current = metadatas[0]
    merged = {
        "keyword": updates.get("keyword", current.get("keyword")),
        "proverb": updates.get("proverb", current.get("proverb")),
        "meaning": updates.get("meaning", current.get("meaning")),
        "example": updates.get("example", current.get("example")),
    }
    normalized = _normalize_row(merged)
    new_id, doc, metadata = _build_chroma_record(normalized)

    if new_id != proverb_id:
        col.delete(ids=[proverb_id])

    col.upsert(ids=[new_id], documents=[doc], metadatas=[metadata])
    return {"id": new_id, **normalized}


def upsert_proverbs(rows: list[dict[str, Any]]) -> tuple[int, int]:
    """
    rows: [{keyword, proverb, meaning, example}]
    """
    col = get_collection()
    inserted = 0
    skipped = 0

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []

    for r in rows:
        try:
            normalized = _normalize_row(r)
        except ValueError:
            skipped += 1
            continue

        proverb_id, doc, metadata = _build_chroma_record(normalized)
        ids.append(proverb_id)
        documents.append(doc)
        metadatas.append(metadata)

    if ids:
        col.upsert(ids=ids, documents=documents, metadatas=metadatas)
        inserted = len(ids)

    return inserted, skipped


def retrieve_context(query: str, top_k: int | None = None) -> list[dict[str, Any]]:
    k = top_k or settings.rag_top_k
    return _retrieve_lexical_context(query, top_k=k)


def _retrieve_lexical_context(query: str, top_k: int) -> list[dict[str, Any]]:
    normalized_query = _normalize_search_text(query)
    if not normalized_query:
        return []

    col = get_collection()
    result = col.get(limit=100000, include=["metadatas"])
    metadatas = result.get("metadatas") or []
    matches: list[tuple[float, dict[str, Any]]] = []

    for md in metadatas:
        if not md:
            continue
        score = _lexical_distance(normalized_query, md)
        if score is None:
            continue
        if score > 1.0 - settings.rag_min_lexical_similarity:
            continue
        matches.append((score, _context_item_from_metadata(md, score)))

    matches.sort(key=lambda item: item[0])
    if matches and matches[0][0] <= 0.05:
        matches = [item for item in matches if item[0] <= 0.05]

    return [item for _, item in matches[:top_k]]


def _lexical_distance(normalized_query: str, metadata: dict[str, Any]) -> float | None:
    fields = [
        metadata.get("keyword"),
        metadata.get("proverb"),
        metadata.get("meaning"),
        metadata.get("example"),
    ]
    searchable = _normalize_search_text(" ".join(str(field or "") for field in fields))
    if not searchable:
        return None

    if normalized_query in searchable:
        return 0.0
    if searchable in normalized_query:
        return 0.0

    tokens = [token for token in normalized_query.split() if len(token) > 1]
    token_score = 0.0
    if tokens:
        matched = sum(1 for token in tokens if token in searchable)
        token_score = matched / len(tokens)

    compact_query = _compact_search_text(normalized_query)
    compact_searchable = _compact_search_text(searchable)
    ngram_score = _ngram_similarity(compact_query, compact_searchable)
    best_similarity = max(token_score, ngram_score)

    if best_similarity == 0.0:
        return None

    return 1.0 - best_similarity


def _normalize_search_text(text: str) -> str:
    normalized = re.sub(r"[၊။!?.,;:\"'`(){}\[\]<>]", " ", text.strip().lower())
    return " ".join(normalized.split())


def _compact_search_text(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _ngram_similarity(query: str, searchable: str, n: int = 3) -> float:
    if not query or not searchable:
        return 0.0
    if len(query) < n:
        return 1.0 if query in searchable else 0.0

    query_ngrams = {query[i : i + n] for i in range(len(query) - n + 1)}
    if not query_ngrams:
        return 0.0

    matched = sum(1 for ngram in query_ngrams if ngram in searchable)
    return matched / len(query_ngrams)


def _context_item_from_metadata(metadata: dict[str, Any], score: float | None) -> dict[str, Any]:
    return {
        "keyword": metadata.get("keyword"),
        "proverb": metadata.get("proverb"),
        "meaning": metadata.get("meaning"),
        "example": metadata.get("example"),
        "score": score,
    }


def _dedupe_context(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for item in items:
        key = str(item.get("proverb") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _answer_from_best_source(sources: list[dict[str, Any]]) -> dict[str, Any]:
    best = sources[0]
    return create_guardrailed_answer(
        proverb=best.get("proverb"),
        meaning_simple_mm=best.get("meaning"),
        example_mm=best.get("example"),
        sources=sources,
    )


def rag_answer(user_question: str) -> dict[str, Any]:
    # Guardrail 1: Validate the question
    is_valid, error_msg = validate_question(user_question)
    if not is_valid:
        return create_no_result_answer()

    # Guardrail 2: Retrieve context
    sources = retrieve_context(user_question, top_k=settings.rag_top_k)

    # Guardrail 3: Check if retrieved context is relevant
    if not is_context_relevant(sources):
        return create_no_result_answer()

    # Guardrail 4: Build prompt with guardrail instructions
    prompt = f"""
You are a helpful Myanmar language tutor for kids who teaches about Myanmar proverbs ONLY.

STRICT RULES:
1. Answer ONLY about Myanmar proverbs from the provided context.
2. If the user's question is not about proverbs, respond with error message.
3. Use ONLY information from the retrieved context - never generate new proverbs.
4. Always explain in simple Burmese suitable for children.
5. Never provide information about other topics (politics, history, science, general knowledge).

You MUST answer in Burmese (Myanmar).
Return ONLY valid JSON (no markdown, no extra text).
Do not include reasoning, markdown fences, or <think> tags.

User question:
{user_question}

Retrieved proverbs (context):
{sources}

JSON schema:
{{
  "proverb": "most relevant proverb (string)",
  "meaning_simple_mm": "simple Burmese explanation for kids (string)",
  "example_mm": "simple Burmese example sentence (string)",
  "sources": [{{"keyword": "...", "proverb": "...", "meaning": "...", "example": "...", "score": 0.0}}]
}}

Rules:
- Choose the best proverb from the retrieved context ONLY.
- Keep meaning very simple using words children understand.
- Use respectful Burmese and simple words.
- Include the sources array (reuse the context you got).
- If the question is NOT about proverbs, set proverb to null and meaning_simple_mm to "ဝမ်းနည်းပါတယ်။ ကျွန်ုပ်၏ စကားပုံဒေတာအတွင်း မတွေ့ရှိပါ။"
"""

    try:
        raw = generate_answer(prompt)
        answer = safe_json_from_llm(raw)
    except (ValueError, RuntimeError):
        return _answer_from_best_source(sources)

    # Guardrail 5: Validate the generated answer
    if not is_answer_valid(answer):
        return create_no_result_answer()

    # Guardrail 6: Ensure sources are included
    if "sources" not in answer or not answer["sources"]:
        answer["sources"] = sources

    return create_guardrailed_answer(
        proverb=answer.get("proverb"),
        meaning_simple_mm=answer.get("meaning_simple_mm"),
        example_mm=answer.get("example_mm"),
        sources=answer.get("sources", []),
    )

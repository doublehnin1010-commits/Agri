from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import unicodedata
from collections import OrderedDict
from typing import Any

from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import AsyncCallbackManagerForRetrieverRun, CallbackManagerForRetrieverRun
from pydantic import Field

from app.core.config import settings
from app.db.chroma import get_vectorstore
from app.services.llm_service import get_str_output_parser, get_utility_llm


logger = logging.getLogger(__name__)


class HybridProverbRetriever(BaseRetriever):
    """Semantic + lexical hybrid retriever for Myanmar proverbs."""

    top_k: int = Field(default_factory=lambda: settings.rag_top_k)

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun | None = None,
    ) -> list[Document]:
        items = retrieve_context(query, top_k=self.top_k)
        return [
            Document(
                page_content=_format_context_item(item),
                metadata={
                    "keyword": item.get("keyword"),
                    "proverb": item.get("proverb"),
                    "meaning": item.get("meaning"),
                    "example": item.get("example"),
                    "score": item.get("score"),
                    "similarity": item.get("similarity"),
                },
            )
            for item in items
        ]

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: AsyncCallbackManagerForRetrieverRun | None = None,
    ) -> list[Document]:
        items = await aretrieve_context(query, top_k=self.top_k)
        return [
            Document(
                page_content=_format_context_item(item),
                metadata={
                    "keyword": item.get("keyword"),
                    "keywords": item.get("keywords"),
                    "category": item.get("category"),
                    "proverb": item.get("proverb"),
                    "meaning": item.get("meaning"),
                    "english_meaning": item.get("english_meaning"),
                    "example": item.get("example"),
                    "score": item.get("score"),
                    "similarity": item.get("similarity"),
                },
            )
            for item in items
        ]


_semantic_retriever = None
_retriever: HybridProverbRetriever | None = None
_rewrite_chain_en = None
_rewrite_chain_my = None
_metadata_cache: list[dict[str, Any]] = []
_metadata_cache_loaded = False
_retrieval_cache: OrderedDict[tuple[str, int], tuple[float, list[dict[str, Any]]]] = OrderedDict()
_RETRIEVAL_CACHE_TTL_SECONDS = 60.0
_RETRIEVAL_CACHE_MAX_ITEMS = 256

REWRITE_PROMPT_EN = PromptTemplate.from_template(
    """Translate the following English user sentence into a short Myanmar semantic search phrase or keyword list that captures the meaning.
Keep it brief and focused on the intent and topic, not the exact words.
Return only the rewritten query.

User sentence:
{query}

Rewritten query:"""
)

REWRITE_PROMPT_MY = PromptTemplate.from_template(
    """Rewrite the following Myanmar user sentence into a short semantic search phrase or keyword list that captures the meaning.
Keep it brief and focused on the intent and topic, not the exact words.
Return only the rewritten query.

User sentence:
{query}

Rewritten query:"""
)


def _elapsed_ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000


def _get_rewrite_chain(language: str):
    global _rewrite_chain_en, _rewrite_chain_my
    if language == "en":
        if _rewrite_chain_en is None:
            _rewrite_chain_en = REWRITE_PROMPT_EN | get_utility_llm() | get_str_output_parser()
        return _rewrite_chain_en

    if _rewrite_chain_my is None:
        _rewrite_chain_my = REWRITE_PROMPT_MY | get_utility_llm() | get_str_output_parser()
    return _rewrite_chain_my


def rewrite_query(query: str, language: str) -> str:
    if not query or not query.strip():
        return query

    try:
        rewritten = _get_rewrite_chain(language).invoke({"query": query}).strip()
        return rewritten or query
    except Exception:
        return query


async def arewrite_query(query: str, language: str) -> str:
    if not query or not query.strip():
        return query

    try:
        rewritten = await _get_rewrite_chain(language).ainvoke({"query": query})
        rewritten_text = str(rewritten).strip()
        return rewritten_text or query
    except Exception:
        return query


def get_vector_store():
    return get_vectorstore()


def get_semantic_retriever():
    """LangChain similarity retriever backed by the shared Chroma vector store."""

    global _semantic_retriever
    if _semantic_retriever is None:
        _semantic_retriever = get_vectorstore().as_retriever(
            search_type="similarity",
            search_kwargs={"k": settings.rag_top_k},
        )
    return _semantic_retriever


def get_retriever() -> HybridProverbRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridProverbRetriever(top_k=settings.rag_top_k)
    return _retriever


def configure_retriever() -> None:
    get_retriever()
    if settings.lexical_cache:
        load_metadata_cache()


def retrieve_context(query: str, top_k: int | None = None) -> list[dict[str, Any]]:
    return asyncio.run(aretrieve_context(query, top_k=top_k))


def _retrieval_cache_key(query: str, top_k: int) -> tuple[str, int]:
    return (" ".join(query.split()).lower(), top_k)


def _copy_retrieval_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(item) for item in items]


def _get_cached_retrieval(key: tuple[str, int]) -> list[dict[str, Any]] | None:
    cached = _retrieval_cache.get(key)
    if cached is None:
        return None

    created_at, items = cached
    if time.monotonic() - created_at > _RETRIEVAL_CACHE_TTL_SECONDS:
        _retrieval_cache.pop(key, None)
        return None

    _retrieval_cache.move_to_end(key)
    return _copy_retrieval_items(items)


def _set_cached_retrieval(key: tuple[str, int], items: list[dict[str, Any]]) -> None:
    _retrieval_cache[key] = (time.monotonic(), _copy_retrieval_items(items))
    _retrieval_cache.move_to_end(key)
    while len(_retrieval_cache) > _RETRIEVAL_CACHE_MAX_ITEMS:
        _retrieval_cache.popitem(last=False)


async def aretrieve_context(query: str, top_k: int | None = None) -> list[dict[str, Any]]:
    k = top_k or settings.rag_top_k
    if not query or not query.strip():
        return []

    cache_key = _retrieval_cache_key(query, k)
    cached = _get_cached_retrieval(cache_key)
    if cached is not None:
        return cached

    total_start = time.perf_counter()
    language = _language_from_question(query)
    rewrite_ms = 0.0
    rewrite_status = "skipped"

    semantic_start = time.perf_counter()
    semantic_results = await _aretrieve_semantic_context(query, top_k=k)
    semantic_ms = _elapsed_ms(semantic_start)

    metadata_start = time.perf_counter()
    semantic_results = _apply_metadata_awareness(query, semantic_results) if settings.enable_metadata_filtering else semantic_results
    metadata_ms = _elapsed_ms(metadata_start)

    merged = _merge_results(semantic_results, [], top_k=k)
    lexical_ms = 0.0
    if _has_enough_results(merged, k):
        _log_retrieval_timing(semantic_ms, metadata_ms, lexical_ms, rewrite_ms, "skipped", total_start)
        _set_cached_retrieval(cache_key, merged)
        return merged

    lexical_results: list[dict[str, Any]] = []
    if settings.enable_lexical_search:
        lexical_start = time.perf_counter()
        lexical_results = _retrieve_lexical_context(query, top_k=k)
        lexical_ms = _elapsed_ms(lexical_start)
        merged = _merge_results(semantic_results, lexical_results, top_k=k)
        if _has_enough_results(merged, k):
            _log_retrieval_timing(semantic_ms, metadata_ms, lexical_ms, rewrite_ms, "skipped", total_start)
            _set_cached_retrieval(cache_key, merged)
            return merged

    if settings.enable_query_rewrite:
        rewrite_start = time.perf_counter()
        rewritten_query = await arewrite_query(query, language)
        rewrite_ms = _elapsed_ms(rewrite_start)
        rewrite_status = "used"

        if rewritten_query.strip() and rewritten_query.strip() != query.strip():
            semantic_start = time.perf_counter()
            rewritten_semantic = await _aretrieve_semantic_context(rewritten_query, top_k=k)
            semantic_ms += _elapsed_ms(semantic_start)

            metadata_start = time.perf_counter()
            rewritten_semantic = (
                _apply_metadata_awareness(rewritten_query, rewritten_semantic)
                if settings.enable_metadata_filtering
                else rewritten_semantic
            )
            metadata_ms += _elapsed_ms(metadata_start)
            merged = _merge_results(merged, rewritten_semantic, top_k=k)
        else:
            rewrite_status = "identical"

    _log_retrieval_timing(semantic_ms, metadata_ms, lexical_ms, rewrite_ms, rewrite_status, total_start)
    result = merged[:k]
    _set_cached_retrieval(cache_key, result)
    return result


def _format_context_item(item: dict[str, Any]) -> str:
    return (
        f"keyword: {item.get('keyword') or ''}\n"
        f"keywords: {item.get('keywords') or ''}\n"
        f"category: {item.get('category') or ''}\n"
        f"proverb: {item.get('proverb') or ''}\n"
        f"meaning: {item.get('meaning') or ''}\n"
        f"english_meaning: {item.get('english_meaning') or ''}\n"
        f"example: {item.get('example') or ''}"
    )


def _build_search_queries(query: str, language: str) -> list[str]:
    queries = [query]
    rewritten_query = rewrite_query(query, language)
    if rewritten_query and rewritten_query.strip() and rewritten_query.strip() != query.strip():
        queries.append(rewritten_query)
    return queries


def _retrieve_semantic_context(query: str, top_k: int) -> list[dict[str, Any]]:
    if not query or not query.strip():
        return []

    try:
        vectorstore = get_vectorstore()
        results = vectorstore.similarity_search_with_score(query, k=top_k)
        matches: list[dict[str, Any]] = []

        for doc, distance in results:
            metadata = doc.metadata or {}
            item = _context_item_from_metadata(metadata, distance)
            item["similarity"] = max(0.0, 1.0 - min(distance, 1.0))
            if item["similarity"] < settings.rag_semantic_threshold:
                continue
            matches.append(item)

        return matches[:top_k]
    except Exception:
        return []


async def _aretrieve_semantic_context(query: str, top_k: int) -> list[dict[str, Any]]:
    if not query or not query.strip():
        return []

    try:
        vectorstore = get_vectorstore()
        search = getattr(vectorstore, "asimilarity_search_with_score", None)
        if search is None:
            results = await asyncio.to_thread(vectorstore.similarity_search_with_score, query, k=top_k)
        else:
            results = await search(query, k=top_k)

        matches: list[dict[str, Any]] = []
        for doc, distance in results:
            metadata = doc.metadata or {}
            item = _context_item_from_metadata(metadata, distance)
            item["similarity"] = max(0.0, 1.0 - min(distance, 1.0))
            if item["similarity"] < settings.rag_semantic_threshold:
                continue
            matches.append(item)
        return matches[:top_k]
    except Exception as exc:
        if _is_embedding_dimension_mismatch(exc):
            logger.warning(
                "Semantic retrieval skipped because the persisted Chroma collection "
                "was built with a different embedding dimension. Rebuild the dataset "
                "with EMBEDDING_MODEL=%s. Detail: %s",
                settings.embedding_model,
                exc,
            )
        else:
            logger.exception("Semantic retrieval failed.")
        return []


def _is_embedding_dimension_mismatch(exc: Exception) -> bool:
    message = str(exc).lower()
    return "expecting embedding with dimension" in message and "got" in message


def _retrieve_lexical_context(query: str, top_k: int) -> list[dict[str, Any]]:
    normalized_query = _normalize_search_text(query)
    if not normalized_query:
        return []

    metadatas = get_metadata_cache() if settings.lexical_cache else _load_collection_metadata()
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


def load_metadata_cache(force: bool = False) -> list[dict[str, Any]]:
    global _metadata_cache, _metadata_cache_loaded
    if _metadata_cache_loaded and not force:
        return _metadata_cache

    _metadata_cache = _load_collection_metadata()
    _metadata_cache_loaded = True
    logger.info("Loaded %s Chroma metadata rows into lexical cache.", len(_metadata_cache))
    return _metadata_cache


def get_metadata_cache() -> list[dict[str, Any]]:
    if not _metadata_cache_loaded:
        return load_metadata_cache()
    return _metadata_cache


def invalidate_metadata_cache() -> None:
    global _metadata_cache, _metadata_cache_loaded
    _metadata_cache = []
    _metadata_cache_loaded = False
    _retrieval_cache.clear()


def _load_collection_metadata() -> list[dict[str, Any]]:
    collection = get_vectorstore()._collection
    result = collection.get(limit=100000, include=["metadatas"])
    return [md for md in (result.get("metadatas") or []) if md]


def _has_enough_results(results: list[dict[str, Any]], top_k: int) -> bool:
    return len(results) >= top_k


def _merge_results(
    semantic_results: list[dict[str, Any]],
    lexical_results: list[dict[str, Any]],
    *,
    top_k: int,
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen_proverbs: set[str] = set()

    for item in semantic_results + lexical_results:
        proverb_text = str(item.get("proverb") or "")
        if not proverb_text or proverb_text in seen_proverbs:
            continue
        seen_proverbs.add(proverb_text)
        merged.append(item)
        if len(merged) >= top_k:
            break

    return merged


def _apply_metadata_awareness(query: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not results:
        return results

    normalized_query = _normalize_search_text(query)
    scored: list[tuple[int, dict[str, Any]]] = []
    for item in results:
        score = _metadata_match_score(normalized_query, item)
        if score:
            item = {**item, "metadata_match_score": score}
        scored.append((score, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored]


def _metadata_match_score(normalized_query: str, metadata: dict[str, Any]) -> int:
    score = 0
    category = _normalize_search_text(str(metadata.get("category") or ""))
    if category and (category in normalized_query or normalized_query in category):
        score += 2

    keyword_values = _metadata_keyword_values(metadata)
    for keyword in keyword_values:
        normalized_keyword = _normalize_search_text(keyword)
        if normalized_keyword and (
            normalized_keyword in normalized_query
            or _compact_search_text(normalized_keyword) in _compact_search_text(normalized_query)
        ):
            score += 1
    return score


def _metadata_keyword_values(metadata: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for field in (metadata.get("keyword"), metadata.get("keywords")):
        if not field:
            continue
        if isinstance(field, list):
            values.extend(str(item) for item in field)
            continue
        if isinstance(field, str):
            try:
                parsed = json.loads(field)
            except json.JSONDecodeError:
                values.extend(part.strip() for part in field.split(","))
            else:
                if isinstance(parsed, list):
                    values.extend(str(item) for item in parsed)
                else:
                    values.append(str(parsed))
            continue
        values.append(str(field))
    return [value for value in values if value]


def _log_retrieval_timing(
    semantic_ms: float,
    metadata_ms: float,
    lexical_ms: float,
    rewrite_ms: float,
    rewrite_status: str,
    total_start: float,
) -> None:
    logger.info(
        "RAG retrieval timing | Semantic Search: %.1f ms | Metadata Filter: %.1f ms | "
        "Lexical Search: %.1f ms | Rewrite: %s%s | Total Retrieval: %.1f ms",
        semantic_ms,
        metadata_ms,
        lexical_ms,
        rewrite_status,
        f" ({rewrite_ms:.1f} ms)" if rewrite_ms else "",
        _elapsed_ms(total_start),
    )


def _language_from_question(question: str) -> str:
    normalized = (question or "").strip()
    if not normalized:
        return "my"

    myanmar_chars = len(re.findall(r"[\u1000-\u109F]", normalized))
    latin_chars = len(re.findall(r"[A-Za-z]", normalized))

    if myanmar_chars > latin_chars:
        return "my"
    return "en"


def _context_item_from_metadata(metadata: dict[str, Any], score: float | None) -> dict[str, Any]:
    return {
        "keyword": metadata.get("keyword"),
        "keywords": metadata.get("keywords"),
        "category": metadata.get("category"),
        "proverb": metadata.get("proverb"),
        "meaning": metadata.get("meaning"),
        "english_meaning": metadata.get("english_meaning"),
        "example": metadata.get("example"),
        "score": score,
    }


def _lexical_distance(normalized_query: str, metadata: dict[str, Any]) -> float | None:
    fields = [
        metadata.get("keyword"),
        metadata.get("keywords"),
        metadata.get("category"),
        metadata.get("proverb"),
        metadata.get("meaning"),
        metadata.get("english_meaning"),
        metadata.get("example"),
    ]
    searchable = _normalize_search_text(" ".join(str(field or "") for field in fields))
    if not searchable:
        return None

    query_variants = _search_text_variants(normalized_query)
    searchable_variants = _search_text_variants(searchable)

    if _has_variant_substring_match(query_variants, searchable_variants):
        return 0.0

    proverb_keyword_score = _proverb_keyword_similarity(query_variants, metadata)
    searchable_compacts = [_compact_search_text(text) for text in searchable_variants]
    tokens = [
        token
        for variant in query_variants
        for token in variant.split()
        if len(token) > 1
    ]
    token_score = 0.0
    if tokens:
        matched = sum(
            1
            for token in tokens
            if any(
                token in text or _compact_search_text(token) in compact
                for text, compact in zip(searchable_variants, searchable_compacts)
            )
        )
        token_score = matched / len(tokens)

    ngram_score = max(
        _ngram_similarity(_compact_search_text(query), _compact_search_text(searchable_text))
        for query in query_variants
        for searchable_text in searchable_variants
    )
    best_similarity = max(proverb_keyword_score, token_score, ngram_score)

    if best_similarity == 0.0:
        return None

    return 1.0 - best_similarity


def _has_variant_substring_match(query_variants: list[str], searchable_variants: list[str]) -> bool:
    for query in query_variants:
        if not query:
            continue
        compact_query = _compact_search_text(query)
        for searchable in searchable_variants:
            if not searchable:
                continue
            if query in searchable or searchable in query:
                return True
            compact_searchable = _compact_search_text(searchable)
            if compact_query in compact_searchable or compact_searchable in compact_query:
                return True
    return False


def _proverb_keyword_similarity(query_variants: list[str], metadata: dict[str, Any]) -> float:
    compact_queries = [_compact_search_text(query) for query in query_variants if query]
    if not compact_queries:
        return 0.0

    fields = [
        metadata.get("keyword"),
        metadata.get("proverb"),
    ]
    searchable = _normalize_search_text(" ".join(str(field or "") for field in fields))
    searchable_variants = _search_text_variants(searchable)
    tokens = []
    for variant in searchable_variants:
        for token in variant.split():
            compact_token = _compact_search_text(token)
            if len(compact_token) >= 4:
                tokens.append(token)
    tokens = list(dict.fromkeys(tokens))
    if not tokens:
        return 0.0

    matched = sum(
        1
        for token in tokens
        if any(
            _compact_search_text(token) in compact_query
            or _has_meaningful_prefix_overlap(_compact_search_text(token), compact_query)
            for compact_query in compact_queries
        )
    )
    if not matched:
        return 0.0

    return max(0.65, matched / len(tokens))


def _has_meaningful_prefix_overlap(left: str, right: str, min_length: int = 4) -> bool:
    common_length = 0
    for left_char, right_char in zip(left, right):
        if left_char != right_char:
            break
        common_length += 1
    shorter_length = min(len(left), len(right))
    return common_length >= min_length and common_length / shorter_length >= 0.75


def _normalize_search_text(text: str) -> str:
    normalized = text.strip().lower()
    normalized = _apply_myanmar_normalization_replacements(normalized)
    normalized = re.sub(r"[၊။!?.,;:\"'`(){}\[\]<>/\\|+=_*&^%$#@~`-]", " ", normalized)
    return " ".join(normalized.split())


def _apply_myanmar_normalization_replacements(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _search_text_variants(text: str) -> list[str]:
    variants = {text}
    variants.add(_strip_optional_myanmar_marks(text))
    return [variant for variant in variants if variant]


def _strip_optional_myanmar_marks(text: str) -> str:
    return re.sub(r"[\u1037\u1038\u1039\u103a]", "", text)


def _compact_search_text(text: str) -> str:
    compact = _apply_myanmar_normalization_replacements(text)
    compact = _strip_optional_myanmar_marks(compact)
    return re.sub(r"\s+", "", compact)


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

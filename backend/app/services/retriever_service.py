from __future__ import annotations

import asyncio
import logging
import re
import time
import unicodedata
from collections import OrderedDict
from typing import Any

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import AsyncCallbackManagerForRetrieverRun, CallbackManagerForRetrieverRun
from pydantic import Field

from app.core.config import settings
from app.db.chroma import get_vectorstore

logger = logging.getLogger(__name__)


class HybridDocumentRetriever(BaseRetriever):
    top_k: int = Field(default_factory=lambda: settings.rag_top_k)

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun | None = None) -> list[Document]:
        return [Document(page_content=item.get("content") or "", metadata=item) for item in retrieve_context(query, top_k=self.top_k)]

    async def _aget_relevant_documents(self, query: str, *, run_manager: AsyncCallbackManagerForRetrieverRun | None = None) -> list[Document]:
        return [Document(page_content=item.get("content") or "", metadata=item) for item in await aretrieve_context(query, top_k=self.top_k)]


_retriever: HybridDocumentRetriever | None = None
_metadata_cache: list[dict[str, Any]] = []
_metadata_cache_loaded = False
_retrieval_cache: OrderedDict[tuple[str, int], tuple[float, list[dict[str, Any]]]] = OrderedDict()
_RETRIEVAL_CACHE_TTL_SECONDS = 60.0
_RETRIEVAL_CACHE_MAX_ITEMS = 256


def get_retriever() -> HybridDocumentRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridDocumentRetriever(top_k=settings.rag_top_k)
    return _retriever


def configure_retriever() -> None:
    get_retriever()
    if settings.lexical_cache:
        load_metadata_cache()


def retrieve_context(query: str, top_k: int | None = None) -> list[dict[str, Any]]:
    return asyncio.run(aretrieve_context(query, top_k=top_k))


async def aretrieve_context(query: str, top_k: int | None = None) -> list[dict[str, Any]]:
    k = top_k or settings.rag_top_k
    if not query or not query.strip():
        return []
    cache_key = (" ".join(query.split()).lower(), k)
    cached = _get_cached_retrieval(cache_key)
    if cached is not None:
        return cached

    start = time.perf_counter()
    semantic = await _aretrieve_semantic_context(query, k)
    lexical = _retrieve_lexical_context(query, k) if settings.enable_lexical_search and len(semantic) < k else []
    result = _merge_results(semantic, lexical, top_k=k)
    logger.info("RAG retrieval | results=%s top_k=%s time=%.1f ms", len(result), k, (time.perf_counter() - start) * 1000)
    _set_cached_retrieval(cache_key, result)
    return result


async def _aretrieve_semantic_context(query: str, top_k: int) -> list[dict[str, Any]]:
    try:
        vectorstore = get_vectorstore()
        search = getattr(vectorstore, "asimilarity_search_with_score", None)
        if search is None:
            results = await asyncio.to_thread(vectorstore.similarity_search_with_score, query, k=top_k)
        else:
            results = await search(query, k=top_k)
        matches = []
        for doc, distance in results:
            item = _context_item_from_doc(doc, distance)
            similarity = max(0.0, 1.0 - min(float(distance or 0.0), 1.0))
            item["similarity"] = similarity
            if similarity >= settings.rag_semantic_threshold:
                matches.append(item)
        return matches[:top_k]
    except Exception:
        logger.exception("Semantic retrieval failed.")
        return []


def _retrieve_lexical_context(query: str, top_k: int) -> list[dict[str, Any]]:
    normalized_query = _normalize_search_text(query)
    if not normalized_query:
        return []
    matches: list[tuple[float, dict[str, Any]]] = []
    for metadata in get_metadata_cache():
        score = _lexical_distance(normalized_query, metadata)
        if score is not None and score <= 1.0 - settings.rag_min_lexical_similarity:
            matches.append((score, _context_item_from_metadata(metadata, score)))
    matches.sort(key=lambda item: item[0])
    return [item for _, item in matches[:top_k]]


def load_metadata_cache(force: bool = False) -> list[dict[str, Any]]:
    global _metadata_cache, _metadata_cache_loaded
    if _metadata_cache_loaded and not force:
        return _metadata_cache
    _metadata_cache = _load_collection_metadata()
    _metadata_cache_loaded = True
    return _metadata_cache


def get_metadata_cache() -> list[dict[str, Any]]:
    return _metadata_cache if _metadata_cache_loaded else load_metadata_cache()


def invalidate_metadata_cache() -> None:
    global _metadata_cache, _metadata_cache_loaded
    _metadata_cache = []
    _metadata_cache_loaded = False
    _retrieval_cache.clear()


def _load_collection_metadata() -> list[dict[str, Any]]:
    result = get_vectorstore()._collection.get(limit=100000, include=["metadatas", "documents"])
    metadatas = result.get("metadatas") or []
    documents = result.get("documents") or []
    return [{**(md or {}), "content": doc or (md or {}).get("content") or ""} for md, doc in zip(metadatas, documents)]


def _context_item_from_doc(doc: Document, score: float | None) -> dict[str, Any]:
    return _context_item_from_metadata({**(doc.metadata or {}), "content": doc.page_content}, score)


def _context_item_from_metadata(metadata: dict[str, Any], score: float | None) -> dict[str, Any]:
    return {
        "document_id": metadata.get("document_id"),
        "filename": metadata.get("filename"),
        "file_type": metadata.get("file_type"),
        "file_size": metadata.get("file_size"),
        "chunk_id": metadata.get("chunk_id"),
        "page_number": metadata.get("page_number"),
        "upload_date": metadata.get("upload_date"),
        "source": metadata.get("source") or metadata.get("filename"),
        "content": metadata.get("content") or "",
        "score": score,
    }


def _merge_results(semantic_results: list[dict[str, Any]], lexical_results: list[dict[str, Any]], *, top_k: int) -> list[dict[str, Any]]:
    merged = []
    seen = set()
    for item in semantic_results + lexical_results:
        key = f"{item.get('document_id')}:{item.get('chunk_id')}:{item.get('content')[:40]}"
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
        if len(merged) >= top_k:
            break
    return merged


def _lexical_distance(normalized_query: str, metadata: dict[str, Any]) -> float | None:
    searchable = _normalize_search_text(" ".join(str(metadata.get(field) or "") for field in ["filename", "source", "content"]))
    if not searchable:
        return None
    tokens = [token for token in normalized_query.split() if len(token) > 1]
    if not tokens:
        return None
    if normalized_query in searchable or searchable in normalized_query:
        return 0.0
    matched = sum(1 for token in tokens if token in searchable)
    if matched == 0:
        return None
    return 1.0 - (matched / len(tokens))


def _get_cached_retrieval(key: tuple[str, int]) -> list[dict[str, Any]] | None:
    cached = _retrieval_cache.get(key)
    if cached is None:
        return None
    created_at, items = cached
    if time.monotonic() - created_at > _RETRIEVAL_CACHE_TTL_SECONDS:
        _retrieval_cache.pop(key, None)
        return None
    _retrieval_cache.move_to_end(key)
    return [dict(item) for item in items]


def _set_cached_retrieval(key: tuple[str, int], items: list[dict[str, Any]]) -> None:
    _retrieval_cache[key] = (time.monotonic(), [dict(item) for item in items])
    _retrieval_cache.move_to_end(key)
    while len(_retrieval_cache) > _RETRIEVAL_CACHE_MAX_ITEMS:
        _retrieval_cache.popitem(last=False)


def _normalize_search_text(text: str) -> str:
    normalized = unicodedata.normalize("NFC", (text or "").strip().lower())
    normalized = re.sub(r"[!?.,;:\"'`(){}\[\]<>/\\|+=_*&^%$#@~`-]", " ", normalized)
    return " ".join(normalized.split())


def _compact_search_text(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", text or ""))

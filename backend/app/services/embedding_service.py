from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Callable

from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings

from app.core.config import settings
from app.db.chroma import get_vectorstore
from app.services.metadata_service import GeneratedMetadata
from app.services.retriever_service import invalidate_metadata_cache


logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_BATCH_SIZE = 100
ProgressCallback = Callable[[int, int], None]

_embeddings: OllamaEmbeddings | None = None


def get_embeddings() -> OllamaEmbeddings:
    """Return the shared OllamaEmbeddings singleton."""

    global _embeddings
    if _embeddings is None:
        if not settings.embedding_model.strip():
            raise RuntimeError("EMBEDDING_MODEL must not be empty")
        _embeddings = OllamaEmbeddings(
            model=settings.embedding_model,
            base_url=settings.ollama_base_url,
        )
    return _embeddings


def configure_embeddings() -> None:
    """Eagerly initialize the embedding model."""

    get_embeddings()


@dataclass(frozen=True)
class EmbeddingDocument:
    """Document payload prepared for ChromaDB embedding and storage."""

    id: str
    page_content: str
    metadata: dict[str, Any]


def _stable_document_id(proverb: str) -> str:
    raw = f"||{proverb}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def build_embedding_documents(
    rows: list[tuple[str, str, str]],
    metadata_rows: list[GeneratedMetadata],
) -> list[EmbeddingDocument]:
    """Create LangChain-ready documents from merged proverb rows and metadata."""

    documents: list[EmbeddingDocument] = []
    for (proverb, meaning, english_meaning), generated in zip(rows, metadata_rows):
        keywords_list = list(generated.keywords)
        keywords_text = ", ".join(keywords_list)

        documents.append(
            EmbeddingDocument(
                id=_stable_document_id(proverb),
                page_content=(
                    f"Proverb:\n{proverb}\n\n"
                    f"Meaning:\n{meaning}\n\n"
                    f"English Meaning:\n{english_meaning}"
                ),
                metadata={
                    "keyword": keywords_text,
                    "meaning": meaning,
                    "example": "",
                    "proverb": proverb,
                    "category": generated.category,
                    "keywords": json.dumps(keywords_list, ensure_ascii=False),
                    "english_meaning": english_meaning,
                },
            )
        )

    return documents


def to_langchain_documents(documents: list[EmbeddingDocument]) -> list[Document]:
    return [
        Document(page_content=item.page_content, metadata=item.metadata, id=item.id)
        for item in documents
    ]


def _upsert_documents_sync(
    documents: list[EmbeddingDocument],
    batch_size: int,
    progress_callback: ProgressCallback | None = None,
) -> int:
    vectorstore = get_vectorstore()
    langchain_docs = to_langchain_documents(documents)
    created = 0

    for index in range(0, len(langchain_docs), batch_size):
        batch = langchain_docs[index : index + batch_size]
        vectorstore.add_documents(batch, ids=[doc.id for doc in batch])
        created += len(batch)
        if progress_callback is not None:
            progress_callback(created, len(documents))

    return created


async def upsert_embedding_documents(
    documents: list[EmbeddingDocument],
    batch_size: int = DEFAULT_EMBEDDING_BATCH_SIZE,
    progress_callback: ProgressCallback | None = None,
) -> int:
    """Upsert LangChain documents on a worker thread to avoid blocking the event loop."""

    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")
    if not documents:
        return 0

    logger.info("Saving %s documents to ChromaDB via LangChain.", len(documents))
    created = await asyncio.to_thread(
        _upsert_documents_sync,
        documents,
        batch_size,
        progress_callback,
    )
    invalidate_metadata_cache()
    return created

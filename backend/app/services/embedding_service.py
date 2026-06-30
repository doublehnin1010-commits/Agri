from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from typing import Any

from app.db.chroma import get_collection
from app.services.metadata_service import GeneratedMetadata


logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_BATCH_SIZE = 100


@dataclass(frozen=True)
class EmbeddingDocument:
    """Document payload prepared for ChromaDB embedding and storage."""

    id: str
    page_content: str
    metadata: dict[str, Any]


def _stable_document_id(proverb: str) -> str:
    """Create the same ID shape as the existing empty-keyword proverb import."""

    raw = f"||{proverb}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def build_embedding_documents(
    rows: list[tuple[str, str, str]],
    metadata_rows: list[GeneratedMetadata],
) -> list[EmbeddingDocument]:
    """Create Chroma-ready documents from merged proverb rows and metadata."""

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
                    # Preserve existing comma-joined field for compatibility
                    "keyword": keywords_text,
                    "meaning": meaning,
                    "example": "",
                    # Required fields (per spec)
                    "proverb": proverb,
                    "category": generated.category,
                    "keywords": keywords_list,
                    "english_meaning": english_meaning,
                },
            )
        )

    return documents


def _upsert_documents_sync(
    documents: list[EmbeddingDocument],
    batch_size: int,
) -> int:
    """Synchronously upsert documents into the existing ChromaDB collection."""

    collection = get_collection()
    created = 0

    for index in range(0, len(documents), batch_size):
        batch = documents[index : index + batch_size]
        collection.upsert(
            ids=[item.id for item in batch],
            documents=[item.page_content for item in batch],
            metadatas=[item.metadata for item in batch],
        )
        created += len(batch)

    return created


async def upsert_embedding_documents(
    documents: list[EmbeddingDocument],
    batch_size: int = DEFAULT_EMBEDDING_BATCH_SIZE,
) -> int:
    """Upsert Chroma documents on a worker thread to avoid blocking the event loop."""

    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")
    if not documents:
        return 0

    logger.info("Saving %s documents to ChromaDB.", len(documents))
    return await asyncio.to_thread(_upsert_documents_sync, documents, batch_size)

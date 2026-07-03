from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any

from langchain_chroma import Chroma

from app.core.config import BACKEND_DIR, settings


class ChromaStore:
    vectorstore: Chroma | None = None


chroma_store = ChromaStore()


def _resolve_chroma_path(path: str) -> str:
    persist_path = Path(path)
    if persist_path.is_absolute():
        return str(persist_path)
    return str(BACKEND_DIR / persist_path)


def connect_chroma() -> None:
    """Initialize the LangChain Chroma vector store with OllamaEmbeddings."""

    from app.services.embedding_service import get_embeddings

    chroma_store.vectorstore = Chroma(
        collection_name=settings.chroma_collection_name,
        embedding_function=get_embeddings(),
        persist_directory=_resolve_chroma_path(settings.chroma_persist_dir),
        collection_metadata={"hnsw:space": "cosine"},
    )


def get_vectorstore() -> Chroma:
    if chroma_store.vectorstore is None:
        connect_chroma()
    return chroma_store.vectorstore


def get_collection() -> Any:
    """Backward-compatible access to the underlying ChromaDB collection."""

    return get_vectorstore()._collection


def reset_chroma_collection() -> None:
    """Drop and recreate the Chroma collection.

    This is required when changing embedding models because Chroma fixes a
    collection's vector dimension after the first inserted embedding.
    """

    try:
        get_vectorstore().delete_collection()
    except Exception:
        pass

    chroma_store.vectorstore = None
    try:
        from app.services.retriever_service import invalidate_metadata_cache

        invalidate_metadata_cache()
    except Exception:
        pass

    connect_chroma()


def delete_chroma_store() -> bool:
    """Delete the persistent Chroma dataset storage."""

    chroma_store.vectorstore = None
    try:
        from app.services.retriever_service import invalidate_metadata_cache

        invalidate_metadata_cache()
    except Exception:
        pass

    persist_path = Path(_resolve_chroma_path(settings.chroma_persist_dir))
    if not persist_path.exists():
        return False

    for attempt in range(3):
        try:
            shutil.rmtree(persist_path)
            return True
        except PermissionError:
            if attempt == 2:
                return False
            time.sleep(0.5)
        except OSError:
            return False

    return False

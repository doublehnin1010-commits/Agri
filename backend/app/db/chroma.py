from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

from app.core.config import settings


class Chroma:
    client: Any | None = None
    collection: Any | None = None


chroma = Chroma()


def connect_chroma() -> None:
    chroma.client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()
    chroma.collection = chroma.client.get_or_create_collection(
        name=settings.chroma_collection_name,
        metadata={"hnsw:space": "cosine"},
        embedding_function=embedding_fn,
    )


def get_collection():
    if not chroma.collection:
        connect_chroma()
    return chroma.collection


def delete_chroma_store() -> bool:
    """Delete the persistent Chroma dataset storage."""
    # Reset the Chroma client and collection to release any open handles.
    if chroma.client is not None:
        try:
            chroma.client.reset()
        except Exception:
            pass
        try:
            chroma.client.close()
        except Exception:
            pass

    chroma.collection = None
    chroma.client = None

    persist_path = Path(settings.chroma_persist_dir)
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

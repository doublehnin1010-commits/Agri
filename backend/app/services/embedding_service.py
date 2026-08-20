from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections import Counter
from typing import Any

from app.core.config import settings

_TOKEN_RE = re.compile(r"[\u1000-\u109F]+|[A-Za-z0-9]+")


class LocalHashEmbeddings:
    """Small local embedding function for Chroma without API calls or quotas.

    It uses hashed word/character n-gram features. This is not as semantically
    rich as a hosted embedding model, but it is deterministic, offline, and good
    enough for exact/near-exact document retrieval over uploaded knowledge.
    """

    def __init__(self, dimensions: int = 768):
        self.dimensions = dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    async def aembed_query(self, text: str) -> list[float]:
        return self.embed_query(text)

    def _embed(self, text: str) -> list[float]:
        features = _features(text)
        vector = [0.0] * self.dimensions
        if not features:
            return vector

        counts = Counter(features)
        for feature, count in counts.items():
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            raw = int.from_bytes(digest, "big")
            index = raw % self.dimensions
            sign = 1.0 if (raw >> 63) == 0 else -1.0
            vector[index] += sign * (1.0 + math.log(count))

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]


def _features(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFC", (text or "").lower())
    tokens = _TOKEN_RE.findall(normalized)
    features: list[str] = []
    for token in tokens:
        features.append(f"w:{token}")
        compact = re.sub(r"\s+", "", token)
        if len(compact) >= 3:
            for size in (3, 4):
                if len(compact) >= size:
                    features.extend(f"c{size}:{compact[i:i + size]}" for i in range(len(compact) - size + 1))
    return features


_embeddings: LocalHashEmbeddings | None = None


def get_embeddings() -> LocalHashEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = LocalHashEmbeddings(settings.local_embedding_dimensions)
    return _embeddings


def configure_embeddings() -> None:
    get_embeddings()


class EmbeddingDocument:
    def __init__(self, id: str, page_content: str, metadata: dict[str, Any]):
        self.id = id
        self.page_content = page_content
        self.metadata = metadata

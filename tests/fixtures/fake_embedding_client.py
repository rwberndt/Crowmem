"""Deterministic, hash-based embeddings for tests -- no model download, and
identical text always yields identical vectors so cosine-similarity-based
assertions are exact and reproducible.
"""

import hashlib

DIMENSION = 384


class FakeEmbeddingClient:
    @property
    def dimension(self) -> int:
        return DIMENSION

    def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = []
        while len(values) < DIMENSION:
            digest = hashlib.sha256(digest).digest()
            values.extend(b / 255.0 - 0.5 for b in digest)
        return values[:DIMENSION]

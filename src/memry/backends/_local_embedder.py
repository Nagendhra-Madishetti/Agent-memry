"""A deterministic, dependency-free embedder for Graphiti.

It is NOT semantic: vectors are derived from a SHA-256 stream of the text. That is
deliberate and sufficient for the temporal-supersession heartbeat, where the LLM
(not cosine similarity) drives contradiction detection, and candidate edges are
found via BM25 full-text search. It lets the FalkorDB backend run with no embedding
API key. Swap in a real embedder (OpenAI/NVIDIA/sentence-transformers) for
production semantic recall.
"""

from __future__ import annotations

import hashlib

from graphiti_core.embedder.client import EmbedderClient, EmbedderConfig


class LocalDeterministicEmbedder(EmbedderClient):
    """A Graphiti ``EmbedderClient`` that returns deterministic, non-semantic vectors."""

    def __init__(self, embedding_dim: int = 1024) -> None:
        self.config = EmbedderConfig(embedding_dim=embedding_dim)

    @property
    def embedding_dim(self) -> int:
        return self.config.embedding_dim

    def _embed(self, text: str) -> list[float]:
        out: list[float] = []
        counter = 0
        while len(out) < self.embedding_dim:
            digest = hashlib.sha256(f"{text}|{counter}".encode()).digest()
            for byte in digest:
                out.append((byte / 127.5) - 1.0)
                if len(out) >= self.embedding_dim:
                    break
            counter += 1
        return out

    async def create(self, input_data: str | list[str]) -> list[float]:
        if isinstance(input_data, str):
            return self._embed(input_data)
        if isinstance(input_data, list) and input_data and isinstance(input_data[0], str):
            return self._embed(" ".join(input_data))
        return self._embed(str(input_data))

    async def create_batch(self, input_data_list: list[str]) -> list[list[float]]:
        return [self._embed(t if isinstance(t, str) else str(t)) for t in input_data_list]

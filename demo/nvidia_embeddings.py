"""A real LlamaIndex embedding model backed by NVIDIA's OpenAI-compatible endpoint.

Used by the head-to-head demo so the plain-RAG baseline retrieves with *genuine*
semantic embeddings (no mock), making its failure honest rather than rigged. Uses the
same MEMRY_LLM_API_KEY; stdlib HTTP only.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any

from llama_index.core.base.embeddings.base import BaseEmbedding


class NvidiaEmbedding(BaseEmbedding):
    api_key: str
    base_url: str
    embed_model: str = "nvidia/nv-embedqa-e5-v5"

    def __init__(
        self,
        api_key: str,
        base_url: str,
        embed_model: str = "nvidia/nv-embedqa-e5-v5",
        **kw: Any,
    ):
        super().__init__(
            api_key=api_key, base_url=base_url, embed_model=embed_model,
            model_name=embed_model, **kw,
        )

    def _embed(self, texts: list[str], input_type: str) -> list[list[float]]:
        req = urllib.request.Request(
            self.base_url.rstrip("/") + "/embeddings",
            data=json.dumps(
                {
                    "model": self.embed_model,
                    "input": texts,
                    "input_type": input_type,
                    "truncate": "END",
                }
            ).encode(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)["data"]
        return [row["embedding"] for row in data]

    def _get_query_embedding(self, query: str) -> list[float]:
        return self._embed([query], "query")[0]

    def _get_text_embedding(self, text: str) -> list[float]:
        return self._embed([text], "passage")[0]

    def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, "passage")

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return self._get_query_embedding(query)

    async def _aget_text_embedding(self, text: str) -> list[float]:
        return self._get_text_embedding(text)

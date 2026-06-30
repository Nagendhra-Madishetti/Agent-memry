"""Pluggable embedders - config-selected, fail-loud, bring-your-own.

The embedder is a commodity layer like backends and policies: selectable by config name, not
by editing code. The hash embedder stays the key-free default (correctness tests do not depend
on embeddings); a real NVIDIA-API embedder (default ``baai/bge-m3``) puts genuine semantic
vectors in the loop for the end-to-end and demo paths.

Two safety properties are load-bearing:
  A. Fail-loud. A selected embedder with a missing key/dependency, or an unknown/excluded
     name, raises at construction - it NEVER silently falls back to the hash embedder. A
     silent fallback would serve meaning-blind retrieval that still returns results: no error,
     just silently wrong answers, the worst failure mode for a retrieval system.
  B. The dimension travels with the embedder and is validated against the store at startup,
     hard-crashing on mismatch (``check_embedding_dimension``). Mixing dimensions silently
     corrupts the vector space.

Model policy (see docs/EMBEDDERS.md): default ``baai/bge-m3`` (the self-hosted production
target; later swap to a local BGE-M3 with no code change), proven fallback
``nvidia/nv-embedqa-e5-v5``. ``nvidia/nv-embed-v1`` is EXCLUDED - non-commercial license -
and is never a default or selectable option.
"""

from __future__ import annotations

import asyncio
import json
import os
import urllib.request

from graphiti_core.embedder.client import EmbedderClient, EmbedderConfig

from ._local_embedder import LocalDeterministicEmbedder

_DEFAULT_NVIDIA_BASE = "https://integrate.api.nvidia.com/v1"

# Config name -> NVIDIA model string. The default is bge-m3.
_NVIDIA_MODELS: dict[str, str] = {
    "bge-m3": "baai/bge-m3",
    "nvidia-e5": "nvidia/nv-embedqa-e5-v5",
}

# Deliberately excluded, with the reason. Never a default or selectable embedder.
EXCLUDED_MODELS: dict[str, str] = {
    "nvidia/nv-embed-v1": "non-commercial license; would poison open-source/enterprise adoption",
    "nv-embed-v1": "non-commercial license; would poison open-source/enterprise adoption",
}


class EmbedderError(RuntimeError):
    """Fail-loud embedder selection/configuration error (safety property A)."""


class EmbedderDimensionMismatch(EmbedderError):
    """The embedder's dimension does not match the existing store (safety property B)."""


class NvidiaEmbedder(EmbedderClient):
    """A Graphiti ``EmbedderClient`` backed by an NVIDIA OpenAI-compatible embeddings
    endpoint. Carries its vector dimension (the contract detail that makes 'any embedder'
    safe). Stdlib HTTP only - no extra dependency."""

    def __init__(
        self,
        api_key: str,
        model: str = "baai/bge-m3",
        base_url: str = _DEFAULT_NVIDIA_BASE,
        embedding_dim: int = 1024,
        timeout: float = 60.0,
    ) -> None:
        self.config = EmbedderConfig(embedding_dim=embedding_dim)
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

    @property
    def embedding_dim(self) -> int:
        return self.config.embedding_dim

    def _post(self, texts: list[str], input_type: str) -> list[list[float]]:
        req = urllib.request.Request(
            self.base_url.rstrip("/") + "/embeddings",
            data=json.dumps(
                {"model": self.model, "input": texts, "input_type": input_type, "truncate": "END"}
            ).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            payload = json.loads(resp.read())
        return [row["embedding"] for row in payload["data"]]

    async def create(self, input_data: str | list[str]) -> list[float]:
        text = input_data if isinstance(input_data, str) else " ".join(map(str, input_data))
        vectors = await asyncio.to_thread(self._post, [text], "query")
        return vectors[0]

    async def create_batch(self, input_data_list: list[str]) -> list[list[float]]:
        if not input_data_list:
            return []
        return await asyncio.to_thread(self._post, list(input_data_list), "passage")


def available_embedders() -> list[str]:
    return ["hash", *sorted(_NVIDIA_MODELS)]


def create_embedder(
    name: str | None = "hash",
    *,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    embedding_dim: int = 1024,
) -> EmbedderClient:
    """Construct an embedder by config name. Fail-loud (safety property A): a missing key,
    an excluded model, or an unknown name raises - it never silently returns the hash embedder.
    """
    name = (name or "hash").strip()

    if name == "hash":
        return LocalDeterministicEmbedder(embedding_dim)

    if name in EXCLUDED_MODELS or (model and model in EXCLUDED_MODELS):
        reason = EXCLUDED_MODELS.get(name) or EXCLUDED_MODELS.get(model or "", "excluded")
        raise EmbedderError(f"embedder {name!r} is excluded: {reason}. See docs/EMBEDDERS.md.")

    if name in _NVIDIA_MODELS:
        resolved_model = model or _NVIDIA_MODELS[name]
        key = api_key or os.getenv("COGNIFLOW_EMBEDDER_API_KEY") or os.getenv("NVIDIA_API_KEY")
        if not key:
            raise EmbedderError(
                f"embedder {name!r} needs an API key; set COGNIFLOW_EMBEDDER_API_KEY "
                "(or pass api_key). Refusing to silently fall back to the hash embedder."
            )
        return NvidiaEmbedder(
            api_key=key,
            model=resolved_model,
            base_url=base_url or _DEFAULT_NVIDIA_BASE,
            embedding_dim=embedding_dim,
        )

    raise EmbedderError(
        f"unknown embedder {name!r}; available: {available_embedders()} "
        "(or plug a new EmbedderClient). Refusing to silently fall back to the hash embedder."
    )


def check_embedding_dimension(store_dim: int | None, embedder_dim: int) -> None:
    """Validate the selected embedder's dimension against the existing store (safety
    property B). Hard-crash on a definite mismatch; a ``None`` store_dim (empty/undetectable
    store) is a no-op - there is nothing yet to corrupt."""
    if store_dim is not None and store_dim != embedder_dim:
        raise EmbedderDimensionMismatch(
            f"embedding dimension mismatch: the store holds {store_dim}-dim vectors but the "
            f"selected embedder produces {embedder_dim}-dim vectors. Mixing dimensions "
            "corrupts the vector space. Re-ingest into a fresh store with a matching embedder, "
            "or select an embedder whose dimension matches the store."
        )

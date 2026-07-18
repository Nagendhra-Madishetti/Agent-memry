"""TemporalGraphRetriever (seam a) - a LlamaIndex retriever backed by a memry
``AsyncSubstrate``.

Design decision (thin slice): ``as_of`` is bound per retriever instance, not threaded
through ``QueryBundle``. The agent factory builds one retriever per as_of. This keeps
the slice minimal; threading as_of through the query is a later refinement.

The async ``_aretrieve`` is overridden because that is the path the agent actually
runs; the sync ``_retrieve`` (the abstract method) bridges to it for non-async callers.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from llama_index.core.base.base_retriever import BaseRetriever
from llama_index.core.callbacks.base import CallbackManager
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode

from ...core.contracts import AsyncSubstrate
from ...core.types import RetrievalQuery

# Temporal/identity metadata must not pollute embeddings or the LLM prompt.
TEMPORAL_METADATA_KEYS = [
    "belief_id",
    "valid_at",
    "invalid_at",
    "created_at",
    "expired_at",
    "provenance",
]


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


class TemporalGraphRetriever(BaseRetriever):
    """Retrieve point-in-time beliefs from a substrate as LlamaIndex nodes."""

    def __init__(
        self,
        substrate: AsyncSubstrate,
        as_of: datetime | None = None,
        top_k: int = 5,
        include_expired: bool = False,
        callback_manager: CallbackManager | None = None,
    ) -> None:
        self._substrate = substrate
        self._as_of = as_of
        self._top_k = top_k
        self._include_expired = include_expired
        super().__init__(callback_manager=callback_manager)

    async def _aretrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        result = await self._substrate.read(
            RetrievalQuery(
                text=query_bundle.query_str,
                as_of=self._as_of,
                top_k=self._top_k,
                include_expired=self._include_expired,
            )
        )
        nodes: list[NodeWithScore] = []
        for scored in result.results:
            belief = scored.belief
            node = TextNode(
                text=belief.statement,
                metadata={
                    "belief_id": belief.id,
                    "valid_at": _iso(belief.valid_at),
                    "invalid_at": _iso(belief.invalid_at),
                    "created_at": _iso(belief.created_at),
                    "expired_at": _iso(belief.expired_at),
                    "provenance": list(belief.provenance),
                },
                excluded_embed_metadata_keys=list(TEMPORAL_METADATA_KEYS),
                excluded_llm_metadata_keys=list(TEMPORAL_METADATA_KEYS),
            )
            nodes.append(NodeWithScore(node=node, score=scored.score))
        return nodes

    def _retrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._aretrieve(query_bundle))
        raise RuntimeError(
            "TemporalGraphRetriever is async-first; call aretrieve() (or use the "
            "agent path) when inside an event loop."
        )

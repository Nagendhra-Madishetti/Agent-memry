"""GraphitiFalkorDBBackend - the canonical async Substrate.

Wraps graphiti-core (bi-temporal knowledge graph) on a FalkorDB driver and adapts
it to the cogniflow ``AsyncSubstrate`` contract (write / read / falsify). The LLM
is configurable (any OpenAI-compatible endpoint); embeddings use a local
deterministic embedder so no embedding key is required.

This module imports graphiti-core and falkordb, so it is imported only when the
backend is actually used (never from ``cogniflow.backends.__init__``), keeping the
core import-free.
"""

from __future__ import annotations

import inspect
import os
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone

from graphiti_core import Graphiti
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
from graphiti_core.driver.falkordb_driver import FalkorDriver
from graphiti_core.edges import EntityEdge
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
from graphiti_core.nodes import EntityNode, EpisodeType
from graphiti_core.search.search_filters import ComparisonOperator, DateFilter, SearchFilters

from ..core.types import (
    Belief,
    Episode,
    FalsificationVerdict,
    RetrievalQuery,
    RetrievalResult,
    ScoredBelief,
    WriteReceipt,
)
from ._local_embedder import LocalDeterministicEmbedder


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class GraphitiFalkorDBConfig:
    """Connection + model configuration for the backend."""

    host: str = "localhost"
    port: int = 6379
    group_id: str = "cogniflow"
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None
    embedding_dim: int = 1024

    @classmethod
    def from_env(cls, group_id: str = "cogniflow") -> GraphitiFalkorDBConfig:
        """Build config from environment (loads a local .env if present)."""
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except Exception:
            pass
        return cls(
            host=os.getenv("COGNIFLOW_FALKORDB_HOST", "localhost"),
            port=int(os.getenv("COGNIFLOW_FALKORDB_PORT", "6379")),
            group_id=group_id,
            llm_api_key=os.getenv("COGNIFLOW_LLM_API_KEY"),
            llm_base_url=os.getenv("COGNIFLOW_LLM_BASE_URL"),
            llm_model=os.getenv("COGNIFLOW_LLM_MODEL"),
        )


def _edge_to_belief(edge: EntityEdge) -> Belief:
    return Belief(
        id=edge.uuid,
        statement=edge.fact,
        created_at=edge.created_at,
        valid_at=edge.valid_at,
        invalid_at=edge.invalid_at,
        expired_at=edge.expired_at,
        predicate=edge.name,
        provenance=tuple(edge.episodes or ()),
        metadata={
            "group_id": edge.group_id,
            "source_node_uuid": edge.source_node_uuid,
            "target_node_uuid": edge.target_node_uuid,
        },
    )


class GraphitiFalkorDBBackend:
    """Async :class:`~cogniflow.core.contracts.AsyncSubstrate` over Graphiti+FalkorDB."""

    name = "graphiti-falkordb"

    def __init__(self, config: GraphitiFalkorDBConfig) -> None:
        self.config = config
        self.group_id = config.group_id
        self._driver = FalkorDriver(host=config.host, port=config.port, database=config.group_id)
        llm_config = LLMConfig(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
            model=config.llm_model,
        )
        self._graphiti = Graphiti(
            graph_driver=self._driver,
            llm_client=OpenAIGenericClient(config=llm_config),
            embedder=LocalDeterministicEmbedder(config.embedding_dim),
            cross_encoder=OpenAIRerankerClient(config=llm_config),
        )

    async def setup(self) -> None:
        """Create indices/constraints. Idempotent; call once before use."""
        await self._graphiti.build_indices_and_constraints()

    async def close(self) -> None:
        await self._graphiti.close()
        # Best-effort: close the underlying FalkorDB async client so its redis
        # connection does not emit "event loop is closed" on GC (Windows).
        client = getattr(self._driver, "client", None) or getattr(self._driver, "falkor_db", None)
        closer = getattr(client, "aclose", None) or getattr(client, "close", None)
        if closer is not None:
            try:
                result = closer()
                if inspect.isawaitable(result):
                    await result
            except Exception:
                pass

    # --- AsyncSubstrate contract -------------------------------------------------

    async def write(self, episode: Episode) -> WriteReceipt:
        """Ingest an episode. If ``episode.metadata['triple']`` is present, inject it
        as a structured fact (``add_triplet``); otherwise extract via ``add_episode``.
        Both run Graphiti's dedup + temporal invalidation.
        """
        triple = (episode.metadata or {}).get("triple")
        if triple:
            return await self._write_triplet(episode, triple)
        return await self._write_episode(episode)

    async def _write_episode(self, episode: Episode) -> WriteReceipt:
        result = await self._graphiti.add_episode(
            name=episode.id,
            episode_body=episode.content,
            source_description=episode.source_description or episode.source,
            reference_time=episode.reference_time,
            source=EpisodeType.text,
            group_id=self.group_id,
        )
        created, invalidated = [], []
        for edge in result.edges:
            (invalidated if edge.expired_at is not None else created).append(edge.uuid)
        return WriteReceipt(
            episode_id=episode.id,
            created_belief_ids=tuple(created),
            invalidated_belief_ids=tuple(invalidated),
        )

    async def _write_triplet(self, episode: Episode, triple: dict) -> WriteReceipt:
        gid = self.group_id
        now = _utc_now()
        source = EntityNode(name=triple["source"], group_id=gid, labels=["Entity"], created_at=now)
        target = EntityNode(name=triple["target"], group_id=gid, labels=["Entity"], created_at=now)
        edge = EntityEdge(
            source_node_uuid=source.uuid,
            target_node_uuid=target.uuid,
            name=triple["predicate"],
            fact=triple.get("fact", triple["predicate"]),
            group_id=gid,
            created_at=now,
            valid_at=episode.reference_time,
            episodes=[],
        )
        result = await self._graphiti.add_triplet(source, edge, target)
        created = [e.uuid for e in result.edges if e.expired_at is None]
        invalidated = [e.uuid for e in result.edges if e.expired_at is not None]
        return WriteReceipt(
            episode_id=episode.id,
            created_belief_ids=tuple(created),
            invalidated_belief_ids=tuple(invalidated),
        )

    async def read(self, query: RetrievalQuery) -> RetrievalResult:
        edges = await self._graphiti.search(
            query=query.text,
            group_ids=[self.group_id],
            num_results=query.top_k,
            search_filter=self._as_of_filter(query.as_of),
        )
        beliefs = [_edge_to_belief(e) for e in edges]
        # Deterministic safety net (seam b): the DB-side SearchFilters is
        # best-effort, so enforce point-in-time validity in-process. This is the
        # invariant the heartbeat depends on.
        kept = [b for b in beliefs if self._is_visible(b, query)]
        results = tuple(ScoredBelief(belief=b) for b in kept)
        return RetrievalResult(query=query, results=results, as_of=query.as_of)

    @staticmethod
    def _is_visible(belief: Belief, query: RetrievalQuery) -> bool:
        """Point-in-time visibility. With as_of set, event-time validity rules
        (and supersedes include_expired). Without as_of, include_expired controls
        whether system-time-expired beliefs are shown."""
        if query.as_of is not None:
            return belief.is_valid_at(query.as_of)
        if not query.include_expired and belief.expired_at is not None:
            return False
        return True

    async def falsify(
        self,
        target: Belief | str,
        against: Sequence[Belief] | None = None,
    ) -> FalsificationVerdict:
        """Report the stored falsification state of a belief (the explicit
        falsification engine is deferred; supersession happens at write time)."""
        target_id = target if isinstance(target, str) else target.id
        try:
            edge = await EntityEdge.get_by_uuid(self._driver, target_id)
        except Exception:
            return FalsificationVerdict(
                target_id=target_id, superseded=False, rationale="belief not found"
            )
        superseded = edge.expired_at is not None or edge.invalid_at is not None
        return FalsificationVerdict(
            target_id=target_id,
            superseded=superseded,
            invalid_at=edge.invalid_at,
            rationale="reflects stored bi-temporal invalidation state",
        )

    @staticmethod
    def _as_of_filter(as_of: datetime | None) -> SearchFilters:
        """Compile point-in-time semantics: valid_at <= T AND (invalid_at IS NULL OR
        invalid_at > T). Opt-in; an absent as_of returns everything."""
        if as_of is None:
            return SearchFilters()
        return SearchFilters(
            valid_at=[
                [DateFilter(date=as_of, comparison_operator=ComparisonOperator.less_than_equal)]
            ],
            invalid_at=[
                [DateFilter(comparison_operator=ComparisonOperator.is_null)],
                [DateFilter(date=as_of, comparison_operator=ComparisonOperator.greater_than)],
            ],
        )

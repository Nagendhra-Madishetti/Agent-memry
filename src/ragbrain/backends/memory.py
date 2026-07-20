"""In-memory bi-temporal substrate: the zero-infrastructure path.

`pip install ragbrain` and this runs. No Docker, no database, no API keys, no
network. It exists so the core guarantee (as-of retrieval and system-time replay
with the un-knowing invariant) can be seen in seconds rather than after a
compose file.

It is a real ledger, not a demo prop: it satisfies the same `AsyncSubstrate`
conformance suite the graph backends satisfy, and it delegates every temporal
decision to `ragbrain.core.audit`, the same pure functions the FalkorDB and
Neo4j backends use. There is no second implementation of the invariant to drift.

What it deliberately does NOT do, and what the graph backends are for:

* No entity extraction. A written episode becomes exactly one belief; supersession
  is by an explicit `key`, never inferred by a model. Nothing here guesses.
* No semantic retrieval. Matching is lexical token overlap, so paraphrases with no
  shared words will not retrieve. Configure a real embedder and a graph backend for
  meaning-based recall.
* No persistence and no concurrency story. State lives in one process and dies with it.

Use it for the quickstart, for tests, and for reasoning about temporal behaviour
without infrastructure. Use FalkorDB or Neo4j for anything real.
"""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from ragbrain.core import audit
from ragbrain.core.types import (
    Belief,
    Episode,
    FalsificationVerdict,
    RetrievalQuery,
    RetrievalResult,
    ScoredBelief,
    WriteReceipt,
    utc_now,
)

__all__ = ["MemoryLedger", "MemorySubstrate"]

_WORD = re.compile(r"[a-z0-9]+")


def _coerce(value: datetime | str | None) -> datetime | None:
    """Accept a datetime or an ISO-8601 string; always return it tz-aware in UTC."""
    if value is None:
        return None
    dt = datetime.fromisoformat(value) if isinstance(value, str) else value
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


class MemorySubstrate:
    """An `AsyncSubstrate` plus `AuditLedger` held entirely in process memory.

    Supersession is explicit: two episodes carrying the same ``metadata["key"]``
    describe the same slot, so the later one closes the earlier one on both time
    axes and stamps a ``superseded_by`` back-link. Facts written without a key
    never supersede anything.
    """

    def __init__(self) -> None:
        self._beliefs: list[Belief] = []
        self._counter = 0

    # ---------------------------------------------------------------- writing
    def _next_id(self) -> str:
        self._counter += 1
        return f"belief-{self._counter}"

    def _record(
        self,
        statement: str,
        *,
        key: str | None,
        valid_at: datetime | None,
        learned_at: datetime | None,
        provenance: tuple[str, ...] = (),
    ) -> tuple[Belief, tuple[str, ...]]:
        """Append a belief, closing any live predecessor sharing its key."""
        created = learned_at or valid_at or utc_now()
        belief = Belief(
            id=self._next_id(),
            statement=statement,
            created_at=created,
            valid_at=valid_at,
            provenance=provenance,
            metadata={"key": key} if key else {},
        )

        invalidated: list[str] = []
        if key:
            for i, prior in enumerate(self._beliefs):
                if prior.metadata.get("key") != key or prior.id == belief.id:
                    continue
                if prior.invalid_at is not None or prior.expired_at is not None:
                    continue  # already closed
                # event time closes when the successor becomes true; system time
                # closes when this correction was learned.
                self._beliefs[i] = replace(
                    prior,
                    invalid_at=valid_at or created,
                    expired_at=created,
                    metadata={**dict(prior.metadata), "superseded_by": belief.id},
                )
                invalidated.append(prior.id)

        self._beliefs.append(belief)
        return belief, tuple(invalidated)

    async def write(self, episode: Episode) -> WriteReceipt:
        """Ingest one episode as exactly one belief. No extraction, no inference."""
        meta = dict(episode.metadata or {})
        belief, invalidated = self._record(
            episode.content,
            key=meta.get("key"),
            valid_at=_coerce(meta.get("valid_at")) or episode.reference_time,
            learned_at=_coerce(meta.get("learned_at")),
            provenance=(episode.id,),
        )
        return WriteReceipt(
            episode_id=episode.id,
            created_belief_ids=(belief.id,),
            invalidated_belief_ids=invalidated,
        )

    # ---------------------------------------------------------------- reading
    def _live_at(self, as_of: datetime | None, include_expired: bool) -> list[Belief]:
        if include_expired:
            return list(self._beliefs)
        if as_of is None:
            return [b for b in self._beliefs if b.invalid_at is None]
        return audit.event_time_query(self._beliefs, as_of)

    async def read(self, query: RetrievalQuery) -> RetrievalResult:
        """Validity-filter first, then rank. Never rank a fact that was not true."""
        candidates = self._live_at(query.as_of, query.include_expired)
        wanted = _tokens(query.text)
        scored: list[ScoredBelief] = []
        for belief in candidates:
            overlap = wanted & _tokens(belief.statement)
            score = len(overlap) / len(wanted) if wanted else 0.0
            scored.append(ScoredBelief(belief=belief, score=score))
        # strongest match first; ties keep the most recently learned fact ahead
        scored.sort(key=lambda s: (s.score, s.belief.created_at), reverse=True)
        return RetrievalResult(
            query=query, results=tuple(scored[: query.top_k]), as_of=query.as_of
        )

    async def falsify(
        self, target: Belief | str, against: Any = None
    ) -> FalsificationVerdict:
        """Report whether a stored belief has been superseded. Never mutates."""
        target_id = target if isinstance(target, str) else target.id
        found = next((b for b in self._beliefs if b.id == target_id), None)
        if found is None:
            return FalsificationVerdict(
                target_id=target_id,
                superseded=False,
                indeterminate=True,
                rationale="belief not held by this substrate",
            )
        superseded_by = found.metadata.get("superseded_by")
        return FalsificationVerdict(
            target_id=target_id,
            superseded=found.invalid_at is not None,
            invalid_at=found.invalid_at,
            superseded_by=superseded_by,
            rationale="superseded by a later fact on the same key"
            if superseded_by
            else "no successor recorded",
        )

    # ------------------------------------------------------------ audit ledger
    async def event_time_query(
        self, as_of: datetime, group_id: str | None = None
    ) -> list[Belief]:
        return audit.event_time_query(self._beliefs, as_of)

    async def system_time_replay(
        self, system_time: datetime, group_id: str | None = None
    ) -> list[Belief]:
        return audit.system_time_replay(self._beliefs, system_time)

    async def bitemporal_query(
        self, as_of: datetime, system_time: datetime, group_id: str | None = None
    ) -> list[Belief]:
        return audit.bitemporal_query(self._beliefs, as_of, system_time)

    def all_beliefs(self) -> list[Belief]:
        """Every version ever written, in write order. Nothing is deleted."""
        return list(self._beliefs)


class MemoryLedger:
    """A small synchronous facade over `MemorySubstrate` for scripts and demos.

    The async substrate is the real contract; this exists so an example can be
    six honest lines instead of asyncio boilerplate.
    """

    def __init__(self) -> None:
        self.substrate = MemorySubstrate()

    def remember(
        self,
        statement: str,
        *,
        key: str | None = None,
        valid_at: datetime | str | None = None,
        learned_at: datetime | str | None = None,
        source: str | None = None,
    ) -> Belief:
        """Record a fact. Facts sharing a ``key`` supersede one another in order.

        ``learned_at`` defaults to ``valid_at``: the system is assumed to have
        learned the fact when it became true. Pass it explicitly to model a
        correction that arrived late.
        """
        valid = _coerce(valid_at)
        belief, _ = self.substrate._record(
            statement,
            key=key,
            valid_at=valid,
            learned_at=_coerce(learned_at) or valid,
            provenance=(source,) if source else (),
        )
        return belief

    def facts(self, as_of: datetime | str | None = None) -> list[Belief]:
        """Facts true at ``as_of`` (default: now)."""
        return self.substrate._live_at(_coerce(as_of), include_expired=False)

    def replay(self, system_time: datetime | str | None = None) -> list[Belief]:
        """What the ledger believed at ``system_time``, with later knowledge un-known."""
        moment = _coerce(system_time) or utc_now()
        return audit.system_time_replay(self.substrate.all_beliefs(), moment)

    def answer(self, question: str, as_of: datetime | str | None = None) -> str:
        """The best-matching fact as of a moment. Retrieval only, no generation."""
        candidates = self.facts(as_of)
        if not candidates:
            return "No fact on record for that moment."
        wanted = _tokens(question)
        best = max(
            candidates,
            key=lambda b: (len(wanted & _tokens(b.statement)), b.created_at),
        )
        return best.statement

    def timeline(self, key: str) -> list[Belief]:
        """Every version recorded under ``key``, oldest first, including superseded."""
        return [b for b in self.substrate.all_beliefs() if b.metadata.get("key") == key]

    def get(self, key: str, index: int = 0) -> Belief:
        """One version from a key's timeline, by position."""
        return self.timeline(key)[index]

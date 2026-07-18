"""A contract-conformant backend that does nothing.

Every method returns a well-formed, neutral value of the correct type. Its only
job is to prove the contracts are satisfiable and to give the conformance harness
something to run against. All real behavior (extraction, bi-temporal storage,
invalidation) is deferred to the Graphiti backend.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..core.types import (
    Belief,
    Episode,
    FalsificationVerdict,
    RetrievalQuery,
    RetrievalResult,
    WriteReceipt,
)


class NoOpBackend:
    """No-op synchronous :class:`~memry.core.contracts.Substrate`."""

    name = "noop"

    def write(self, episode: Episode) -> WriteReceipt:
        return WriteReceipt(episode_id=episode.id)

    def read(self, query: RetrievalQuery) -> RetrievalResult:
        return RetrievalResult(query=query, results=(), as_of=query.as_of)

    def falsify(
        self,
        target: Belief | str,
        against: Sequence[Belief] | None = None,
    ) -> FalsificationVerdict:
        target_id = target if isinstance(target, str) else target.id
        return FalsificationVerdict(
            target_id=target_id,
            superseded=False,
            rationale="NoOpBackend: falsification deferred",
        )


class AsyncNoOpBackend:
    """No-op asynchronous :class:`~memry.core.contracts.AsyncSubstrate`.

    Mirrors :class:`NoOpBackend` but with awaitable operations. Its purpose is to
    prove the async conformance driver actually awaits an async backend, and to be
    the canonical fixture the FalkorDB backend later replaces.
    """

    name = "async-noop"

    async def write(self, episode: Episode) -> WriteReceipt:
        return WriteReceipt(episode_id=episode.id)

    async def read(self, query: RetrievalQuery) -> RetrievalResult:
        return RetrievalResult(query=query, results=(), as_of=query.as_of)

    async def falsify(
        self,
        target: Belief | str,
        against: Sequence[Belief] | None = None,
    ) -> FalsificationVerdict:
        target_id = target if isinstance(target, str) else target.id
        return FalsificationVerdict(
            target_id=target_id,
            superseded=False,
            rationale="AsyncNoOpBackend: falsification deferred",
        )

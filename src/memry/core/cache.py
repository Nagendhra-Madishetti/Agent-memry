"""Dual-axis caching for the audit ledger.

"The past doesn't move" is true for ONE axis only:

- system-time replay to a past S, and bitemporal (past-S, T): FROZEN. A future write
  has ``created_at`` > S, so it can never change a replay to a fixed past S. Cache
  permanently, never invalidate. The big, safe win.
- event-time query over CURRENT knowledge ("true at T, as we understand it now"): LIVE.
  A later write can change the answer, so these entries MUST invalidate on any write to
  the group_id.

Conflating them serves a stale current-knowledge answer after a write - the same
looks-right/is-right trap as the un-knowing logic, now in the cache. This wrapper keeps
them in separate maps: the current-knowledge key carries a per-group generation that
``note_write`` bumps; the frozen keys carry no generation.

Assumption: replay is to a past or present S (S <= now). A replay to a *future* S is
not meaningful and is not guaranteed fresh by this cache.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .types import Belief


def _iso(value: datetime | None) -> str:
    return value.isoformat() if value is not None else "none"


class CachingAuditLedger:
    """Wrap an AuditLedger; cache frozen past-S answers permanently and current-
    knowledge answers per write-generation. Call :meth:`note_write` on every write to
    a group (the backend's write listener does this)."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self._frozen: dict[tuple, list[Belief]] = {}
        self._current: dict[tuple, list[Belief]] = {}
        self._generation: dict[str | None, int] = {}

    def note_write(self, group_id: str | None = None) -> None:
        """Invalidate current-knowledge entries for this group (bump its generation).
        Frozen past-S entries are intentionally untouched."""
        self._generation[group_id] = self._generation.get(group_id, 0) + 1

    def _gen(self, group_id: str | None) -> int:
        return self._generation.get(group_id, 0)

    async def event_time_query(
        self, as_of: datetime, group_id: str | None = None
    ) -> list[Belief]:
        # LIVE axis: key includes the write-generation, so a write invalidates it.
        key = ("event_time", _iso(as_of), group_id, self._gen(group_id))
        if key not in self._current:
            self._current[key] = list(await self._inner.event_time_query(as_of, group_id))
        return self._current[key]

    async def system_time_replay(
        self, system_time: datetime, group_id: str | None = None
    ) -> list[Belief]:
        # FROZEN axis: no generation in the key; cached permanently.
        key = ("system_time", _iso(system_time), group_id)
        if key not in self._frozen:
            self._frozen[key] = list(await self._inner.system_time_replay(system_time, group_id))
        return self._frozen[key]

    async def bitemporal_query(
        self, system_time: datetime, event_time: datetime, group_id: str | None = None
    ) -> list[Belief]:
        # FROZEN axis: a fixed past S cannot be changed by a future write.
        key = ("bitemporal", _iso(system_time), _iso(event_time), group_id)
        if key not in self._frozen:
            self._frozen[key] = list(
                await self._inner.bitemporal_query(system_time, event_time, group_id)
            )
        return self._frozen[key]

    async def provenance_trace(self, belief_id: str, group_id: str | None = None) -> Any:
        # Pass-through (provenance of a specific belief is not a hot path).
        return await self._inner.provenance_trace(belief_id, group_id)

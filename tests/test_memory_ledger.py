"""The zero-infrastructure path must be a real bi-temporal ledger, not a demo prop.

These tests hold it to the same contract the graph backends meet: substrate
conformance, supersession stamped on both time axes, as-of reads, and the
un-knowing invariant. The final test pins the README quickstart itself, so the
advertised six lines cannot drift from what the code actually does.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from ragbrain.backends.memory import MemoryLedger, MemorySubstrate
from ragbrain.conformance import assert_conforms_async
from ragbrain.core.types import Episode, RetrievalQuery


def _dt(y: int, m: int = 1, d: int = 1) -> datetime:
    return datetime(y, m, d, tzinfo=timezone.utc)


def _seeded() -> MemoryLedger:
    """Acme moves: Boston is filed in 2019, Denver corrects it in 2022."""
    db = MemoryLedger()
    db.remember("Acme Corp is headquartered in Boston", key="acme.hq", valid_at="2019-01-01")
    db.remember("Acme Corp is headquartered in Denver", key="acme.hq", valid_at="2022-01-01")
    return db


def test_substrate_passes_the_same_conformance_suite_as_the_graph_backends() -> None:
    asyncio.run(assert_conforms_async(MemorySubstrate()))


def test_supersession_stamps_both_axes_and_a_back_link() -> None:
    db = _seeded()
    boston = db.get("acme.hq", index=0)
    denver = db.get("acme.hq", index=1)

    # event time closed at the successor's start, system time closed when learned
    assert boston.invalid_at == _dt(2022)
    assert boston.expired_at == _dt(2022)
    assert boston.metadata["superseded_by"] == denver.id

    # the correction itself is live on both axes
    assert denver.invalid_at is None
    assert denver.expired_at is None


def test_reading_as_of_a_past_date_returns_what_was_true_then() -> None:
    db = _seeded()
    assert "Denver" in db.answer("Where is Acme headquartered?")
    assert "Boston" in db.answer("Where is Acme headquartered?", as_of="2020-06-01")


def test_replay_un_knows_a_correction_learned_after_that_moment() -> None:
    """The invariant: from 2021's vantage the 2022 correction has not arrived."""
    db = _seeded()
    facts = db.replay("2021-06-01")

    assert [f.statement for f in facts] == ["Acme Corp is headquartered in Boston"]
    # and it reads live from that vantage: the supersession is un-known, not merely hidden
    assert facts[0].invalid_at is None
    assert facts[0].expired_at is None


def test_replay_after_the_correction_shows_the_correction() -> None:
    db = _seeded()
    facts = db.replay("2023-06-01")
    assert [f.statement for f in facts] == ["Acme Corp is headquartered in Denver"]


def test_replay_before_anything_was_learned_is_empty() -> None:
    assert _seeded().replay("2018-06-01") == []


def test_the_ledger_never_deletes_a_superseded_fact() -> None:
    db = _seeded()
    assert len(db.timeline("acme.hq")) == 2  # both versions retained, in order


def test_async_substrate_write_and_as_of_read() -> None:
    async def run() -> None:
        sub = MemorySubstrate()
        await sub.write(Episode(id="e1", content="Acme Corp is headquartered in Boston",
                                reference_time=_dt(2019), metadata={"key": "acme.hq"}))
        await sub.write(Episode(id="e2", content="Acme Corp is headquartered in Denver",
                                reference_time=_dt(2022), metadata={"key": "acme.hq"}))
        now = await sub.read(RetrievalQuery(text="Acme headquarters"))
        past = await sub.read(RetrievalQuery(text="Acme headquarters", as_of=_dt(2020, 6)))
        assert "Denver" in now.results[0].belief.statement
        assert "Boston" in past.results[0].belief.statement

    asyncio.run(run())


def test_readme_quickstart_is_exactly_what_ships() -> None:
    """Pins the advertised example. If this breaks, the README is lying."""
    db = MemoryLedger()
    db.remember("Acme HQ is Boston", key="acme.hq", valid_at="2019-01-01")
    db.remember("Acme HQ is Denver", key="acme.hq", valid_at="2022-01-01")

    assert "Denver" in db.answer("Where is Acme HQ?")
    assert "Boston" in db.answer("Where is Acme HQ?", as_of="2020-01-01")
    assert "Boston" in db.replay("2021-06-01")[0].statement

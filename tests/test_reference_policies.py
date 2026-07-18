"""Reference policies pass their family conformance suites (T3 + T4), and the
read-time interval_overlap falsification policy behaves correctly without mutation
(acceptance #5, read-time half). CI-safe.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from memry.conformance import assert_policy_conforms
from memry.core.types import Belief
from memry.registry import available_policies, create_policy


def _dt(year: int) -> datetime:
    return datetime(year, 1, 1, tzinfo=timezone.utc)


class _FakeCrossEncoder:
    """Deterministic scorer so the reranker policy conforms without an external model."""

    def score(self, query: str, passages: list[str]) -> list[float]:
        return [float(len(p)) for p in passages]


@pytest.mark.parametrize(
    "family,name",
    [
        (family, name)
        for family in ("validity", "retrieval", "falsification", "writeback")
        for name in available_policies(family)
    ],
)
def test_reference_policy_passes_conformance(family: str, name: str) -> None:
    # grace_window needs a param; the reranker needs a cross-encoder (an external model, here
    # a deterministic fake); others construct with defaults.
    if name == "grace_window":
        kwargs = {"grace_days": 30}
    elif name == "reranker":
        kwargs = {"cross_encoder": _FakeCrossEncoder()}
    else:
        kwargs = {}
    policy = create_policy(family, name, **kwargs)
    assert_policy_conforms(family, policy)


def test_interval_overlap_assesses_supersession_read_only() -> None:
    policy = create_policy("falsification", "interval_overlap")
    target = Belief(
        id="denver",
        statement="HQ Denver",
        created_at=_dt(2022),
        valid_at=_dt(2022),
        invalid_at=None,
    )
    later = Belief(id="seattle", statement="HQ Seattle", created_at=_dt(2024), valid_at=_dt(2024))

    verdict = policy.assess(target, [target, later])
    assert verdict.superseded is True
    assert verdict.superseded_by == "seattle"
    assert verdict.invalid_at == _dt(2024)

    # read-only: the stored target is untouched (no write-time mutation)
    assert target.invalid_at is None
    assert target.expired_at is None


def test_interval_overlap_no_earlier_or_nonoverlapping_candidate() -> None:
    policy = create_policy("falsification", "interval_overlap")
    target = Belief(id="t", statement="x", created_at=_dt(2022), valid_at=_dt(2022))
    earlier = Belief(id="e", statement="x", created_at=_dt(2019), valid_at=_dt(2019))

    assert policy.assess(target, [target, earlier]).superseded is False


def test_recency_ranker_orders_by_valid_at_desc() -> None:
    from memry.core.types import RetrievalQuery

    policy = create_policy("retrieval", "recency")
    beliefs = [
        Belief(id="old", statement="x", created_at=_dt(2019), valid_at=_dt(2019)),
        Belief(id="new", statement="x", created_at=_dt(2023), valid_at=_dt(2023)),
        Belief(id="mid", statement="x", created_at=_dt(2021), valid_at=_dt(2021)),
    ]
    ranked = list(policy.rank(RetrievalQuery(text="q"), beliefs))
    assert [s.belief.id for s in ranked] == ["new", "mid", "old"]

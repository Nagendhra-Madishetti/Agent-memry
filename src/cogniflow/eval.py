"""L6 eval harness: measure probabilistic capabilities instead of asserting them with
one green run.

``score_falsification`` runs a FalsificationPolicy over a labeled set and reports
precision/recall on contradiction detection. An indeterminate verdict counts as "no
positive prediction" (it is honest uncertainty, not a false clean). Standard library
only.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from .core.types import Belief


@dataclass(frozen=True, slots=True)
class FalsificationCase:
    target: Belief
    candidates: tuple[Belief, ...]
    expected_superseded: bool


@dataclass(frozen=True, slots=True)
class EvalReport:
    total: int
    true_pos: int
    false_pos: int
    false_neg: int
    true_neg: int
    indeterminate: int

    @property
    def precision(self) -> float:
        denom = self.true_pos + self.false_pos
        return 1.0 if denom == 0 else self.true_pos / denom

    @property
    def recall(self) -> float:
        denom = self.true_pos + self.false_neg
        return 1.0 if denom == 0 else self.true_pos / denom

    @property
    def accuracy(self) -> float:
        return (self.true_pos + self.true_neg) / self.total if self.total else 1.0


def score_falsification(policy: Any, cases: Sequence[FalsificationCase]) -> EvalReport:
    tp = fp = fn = tn = ind = 0
    for case in cases:
        verdict = policy.assess(case.target, list(case.candidates))
        if verdict.indeterminate:
            ind += 1
        predicted = verdict.superseded and not verdict.indeterminate
        if case.expected_superseded and predicted:
            tp += 1
        elif case.expected_superseded and not predicted:
            fn += 1
        elif (not case.expected_superseded) and predicted:
            fp += 1
        else:
            tn += 1
    return EvalReport(
        total=len(cases),
        true_pos=tp,
        false_pos=fp,
        false_neg=fn,
        true_neg=tn,
        indeterminate=ind,
    )

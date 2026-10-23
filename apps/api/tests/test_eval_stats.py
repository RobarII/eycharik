"""The statistics a quality claim rests on.

Wilson bounds decide what a gate is allowed to claim, and a paired bootstrap decides whether two
runs differ. Both are cheap, both are easy to get subtly wrong, so both are pinned here.
"""

from __future__ import annotations

import pytest

from onboarding.core.metrics import wilson_lower_bound
from onboarding.evals.stats import (
    bootstrap_interval,
    matched_pairs,
    paired_delta,
)


def test_a_perfect_run_on_twelve_cases_cannot_claim_more_than_seventy_six_percent() -> None:
    assert wilson_lower_bound(1.0, 12) == pytest.approx(0.757, abs=0.01)


def test_a_perfect_run_on_a_hundred_cases_can_claim_ninety_six_percent() -> None:
    assert wilson_lower_bound(1.0, 100) == pytest.approx(0.963, abs=0.01)


def test_the_bound_tightens_with_more_cases() -> None:
    bounds = [wilson_lower_bound(0.95, n) for n in (10, 30, 100, 400)]

    assert bounds == sorted(bounds)
    assert bounds[-1] > bounds[0]


def test_a_bound_needs_at_least_one_case() -> None:
    assert wilson_lower_bound(1.0, 0) == 0.0


def test_a_bound_rejects_an_impossible_share() -> None:
    with pytest.raises(ValueError, match="share must be within"):
        wilson_lower_bound(1.5, 10)


def test_the_same_seed_gives_the_same_interval() -> None:
    deltas = [0.1, -0.1, 0.2, 0.0, 0.3]

    assert bootstrap_interval(deltas, seed=7) == bootstrap_interval(deltas, seed=7)


def test_a_uniform_improvement_is_not_a_regression() -> None:
    pairs = [(1.0, 0.0) for _ in range(20)]

    delta = paired_delta("recall", pairs)

    assert delta.delta == 1.0
    assert delta.p_le_zero == 0.0
    assert not delta.regression


def test_a_uniform_loss_is_a_regression() -> None:
    pairs = [(0.0, 1.0) for _ in range(20)]

    delta = paired_delta("recall", pairs)

    assert delta.high < 0.0
    assert delta.regression


def test_a_single_flipped_case_on_twenty_is_not_a_regression() -> None:
    """Two standalone numbers would call this a loss; the paired interval does not."""
    pairs = [(1.0, 1.0) for _ in range(19)] + [(0.0, 1.0)]

    delta = paired_delta("recall", pairs)

    assert delta.delta < 0.0
    assert not delta.regression


def test_a_metric_over_no_shared_cases_says_nothing() -> None:
    delta = paired_delta("recall", [])

    assert delta.n == 0
    assert delta.p_le_zero == 1.0


def test_only_cases_both_runs_scored_are_compared() -> None:
    pairs = matched_pairs({"a": 1.0, "b": 0.0}, {"b": 1.0, "c": 0.0})

    assert pairs == ((0.0, 1.0),)

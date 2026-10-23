"""Paired resampling for two eval runs.

Two standalone accuracies are not a comparison. This module resamples the cases both runs scored,
together, and reports the delta with a 95% interval and the share of resamples where the delta did
not improve. It is the only honest way to say "run B is better than run A" on a set of this size.

``random`` lives here and not in ``core/``: a bootstrap is not a pure function of its arguments
unless it is given a seed, and ``core/`` is not allowed to own a global source of entropy.
"""

from __future__ import annotations

import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

DEFAULT_SEED = 20261023
DEFAULT_ITERATIONS = 2000


@dataclass(frozen=True, slots=True)
class PairedDelta:
    """One metric, compared case by case between a current and a baseline run."""

    metric: str
    current: float
    baseline: float
    delta: float
    low: float
    high: float
    p_le_zero: float
    n: int

    @property
    def regression(self) -> bool:
        """True when the interval excludes zero on the losing side."""
        return self.high < 0.0


def bootstrap_interval(
    deltas: Sequence[float],
    *,
    iterations: int = DEFAULT_ITERATIONS,
    seed: int = DEFAULT_SEED,
) -> tuple[float, float, float]:
    """Resample ``deltas`` with replacement; return ``(low, high, p(delta <= 0))``.

    ``low`` and ``high`` are the 2.5th and 97.5th percentiles of the resampled mean.
    """
    if not deltas:
        return 0.0, 0.0, 1.0
    rng = random.Random(seed)  # noqa: S311 - resampling, not cryptography
    size = len(deltas)
    means: list[float] = []
    for _ in range(iterations):
        total = 0.0
        for _ in range(size):
            total += deltas[rng.randrange(size)]
        means.append(total / size)
    means.sort()
    low = means[max(0, int(0.025 * iterations) - 1)]
    high = means[min(iterations - 1, int(0.975 * iterations))]
    non_positive = sum(1 for value in means if value <= 0.0) / iterations
    return low, high, non_positive


def paired_delta(
    metric: str,
    pairs: Iterable[tuple[float, float]],
    *,
    iterations: int = DEFAULT_ITERATIONS,
    seed: int = DEFAULT_SEED,
) -> PairedDelta:
    """Compare ``(current, baseline)`` pairs on the same cases."""
    collected = list(pairs)
    if not collected:
        return PairedDelta(metric, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0)
    current = sum(pair[0] for pair in collected) / len(collected)
    baseline = sum(pair[1] for pair in collected) / len(collected)
    deltas = [pair[0] - pair[1] for pair in collected]
    low, high, p_le_zero = bootstrap_interval(deltas, iterations=iterations, seed=seed)
    return PairedDelta(
        metric=metric,
        current=current,
        baseline=baseline,
        delta=current - baseline,
        low=low,
        high=high,
        p_le_zero=p_le_zero,
        n=len(collected),
    )


def matched_pairs(
    current: dict[str, float],
    baseline: dict[str, float],
) -> tuple[tuple[float, float], ...]:
    """Cases both runs scored, in a stable order. A case only one run saw proves nothing."""
    shared = sorted(set(current) & set(baseline))
    return tuple((current[case], baseline[case]) for case in shared)

"""Quality metrics for the golden set.

Pure functions over ids and numbers: the evaluator can be tested without a database, a model, or a
network, which is the only way to trust the gate it enforces.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def recall_at_k(expected: Sequence[str], retrieved: Sequence[str], *, k: int = 5) -> float:
    """Share of expected document ids present in the first ``k`` retrieved ids."""
    if not expected:
        return 1.0
    if k < 1:
        raise ValueError("k must be at least 1")
    top = set(retrieved[:k])
    return sum(1 for doc_id in dict.fromkeys(expected) if doc_id in top) / len(
        dict.fromkeys(expected)
    )


def reciprocal_rank(expected: Sequence[str], retrieved: Sequence[str]) -> float:
    """One over the rank of the first expected id; zero when nothing matches."""
    wanted = set(expected)
    for rank, doc_id in enumerate(retrieved, start=1):
        if doc_id in wanted:
            return 1.0 / rank
    return 0.0


def percentile(values: Sequence[float], *, p: float) -> float:
    """Nearest-rank percentile. ``p`` is in ``[0, 100]``; empty input returns zero."""
    if not 0.0 <= p <= 100.0:
        raise ValueError("p must be within [0, 100]")
    if not values:
        return 0.0
    ordered = sorted(values)
    index = math.ceil((p / 100.0) * len(ordered)) - 1
    return ordered[max(0, min(len(ordered) - 1, index))]


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def wilson_lower_bound(share: float, n: int, *, z: float = 1.96) -> float:
    """Lower edge of the Wilson score interval for a share observed on ``n`` cases.

    This is what a gate may claim, not what was measured. At ``share = 1.0`` the bound is
    ``n / (n + z²)``: 0.76 on 12 cases, 0.96 on 100, 0.99 on 400. A gate above that number would
    be arithmetic, not evidence.
    """
    if n < 1:
        return 0.0
    if not 0.0 <= share <= 1.0:
        raise ValueError("share must be within [0, 1]")
    z2 = z * z
    denominator = 1.0 + z2 / n
    centre = share + z2 / (2.0 * n)
    margin = z * math.sqrt(share * (1.0 - share) / n + z2 / (4.0 * n * n))
    return max(0.0, min(1.0, (centre - margin) / denominator))

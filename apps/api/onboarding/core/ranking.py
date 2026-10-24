"""Ranking fusion.

Two retrievers disagree: the vector search finds paraphrases, the lexical search finds acronyms and
document numbers. Reciprocal rank fusion combines their orders without pretending their scores are
comparable.

A weight says how much a list is allowed to outvote another. Equal weights are right when both
retrievers are equally good; they are wrong when one is a candidate generator for the other, and
the second list then spends its budget displacing documents the first list already had right.
"""

from __future__ import annotations

from collections.abc import Sequence

from .models import ChunkId

DEFAULT_RRF_K = 60
# The lexical list is a candidate generator for the vector list, not a second opinion of equal
# weight: at equal weights its top hit outscores the vector list's top hit, and one matching
# question word is weaker evidence than a whole-question embedding match. Half weight lets it
# still promote a genuine find — it needs its own rank and half the vector list's ranking — and
# keeps the vector order at the head. Measured on the shipped corpus and golden set; see
# docs/measurements/2026-10-24-eval-retrieval-lexical-gated-05.md.
LEXICAL_WEIGHT = 0.5


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[ChunkId]],
    *,
    k: int = DEFAULT_RRF_K,
    weights: Sequence[float] | None = None,
    limit: int | None = None,
) -> tuple[tuple[ChunkId, float], ...]:
    """Fuse ranked lists into one order.

    A chunk scores ``weight / (k + rank)`` for every list it appears in, where ``rank`` is one-based
    and ``weight`` defaults to one. Ties are broken by first appearance, so the result is
    deterministic for equal inputs.
    """
    if k < 1:
        raise ValueError("k must be at least 1")
    if limit is not None and limit < 0:
        raise ValueError("limit must not be negative")
    if weights is None:
        weights = (1.0,) * len(rankings)
    if len(weights) != len(rankings):
        raise ValueError("weights and rankings must have the same length")
    if any(weight <= 0.0 for weight in weights):
        raise ValueError("weights must be positive")

    scores: dict[ChunkId, float] = {}
    first_seen: dict[ChunkId, int] = {}
    for ranking, weight in zip(rankings, weights, strict=True):
        seen_in_list: set[ChunkId] = set()
        for rank, chunk_id in enumerate(ranking, start=1):
            if chunk_id in seen_in_list:
                continue
            seen_in_list.add(chunk_id)
            scores[chunk_id] = scores.get(chunk_id, 0.0) + weight / (k + rank)
            first_seen.setdefault(chunk_id, len(first_seen))

    ordered = sorted(scores.items(), key=lambda item: (-item[1], first_seen[item[0]]))
    if limit is not None:
        ordered = ordered[:limit]
    return tuple(ordered)


def dedupe(ranking: Sequence[ChunkId]) -> tuple[ChunkId, ...]:
    """Drop repeats while preserving order."""
    return tuple(dict.fromkeys(ranking))

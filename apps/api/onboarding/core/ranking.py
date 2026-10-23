"""Ranking fusion.

Two retrievers disagree: the vector search finds paraphrases, the lexical search finds acronyms and
document numbers. Reciprocal rank fusion combines their orders without pretending their scores are
comparable.
"""

from __future__ import annotations

from collections.abc import Sequence

from .models import ChunkId

DEFAULT_RRF_K = 60


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[ChunkId]],
    *,
    k: int = DEFAULT_RRF_K,
    limit: int | None = None,
) -> tuple[tuple[ChunkId, float], ...]:
    """Fuse ranked lists into one order.

    A chunk scores ``1 / (k + rank)`` for every list it appears in, where ``rank`` is one-based.
    Ties are broken by first appearance, so the result is deterministic for equal inputs.
    """
    if k < 1:
        raise ValueError("k must be at least 1")
    if limit is not None and limit < 0:
        raise ValueError("limit must not be negative")

    scores: dict[ChunkId, float] = {}
    first_seen: dict[ChunkId, int] = {}
    for ranking in rankings:
        seen_in_list: set[ChunkId] = set()
        for rank, chunk_id in enumerate(ranking, start=1):
            if chunk_id in seen_in_list:
                continue
            seen_in_list.add(chunk_id)
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
            first_seen.setdefault(chunk_id, len(first_seen))

    ordered = sorted(scores.items(), key=lambda item: (-item[1], first_seen[item[0]]))
    if limit is not None:
        ordered = ordered[:limit]
    return tuple(ordered)


def dedupe(ranking: Sequence[ChunkId]) -> tuple[ChunkId, ...]:
    """Drop repeats while preserving order."""
    return tuple(dict.fromkeys(ranking))

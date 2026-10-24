from __future__ import annotations

import pytest

from onboarding.core.models import ChunkId
from onboarding.core.ranking import dedupe, reciprocal_rank_fusion


def ids(*values: str) -> tuple[ChunkId, ...]:
    return tuple(ChunkId(value) for value in values)


def test_chunk_in_both_lists_wins() -> None:
    fused = reciprocal_rank_fusion([ids("a", "b", "c"), ids("d", "b")])

    assert [chunk for chunk, _ in fused][:2] == [ChunkId("b"), ChunkId("a")]


def test_fusion_is_deterministic_for_equal_scores() -> None:
    first = reciprocal_rank_fusion([ids("a"), ids("b")])
    second = reciprocal_rank_fusion([ids("a"), ids("b")])

    assert first == second
    assert [chunk for chunk, _ in first] == [ChunkId("a"), ChunkId("b")]


def test_duplicates_inside_one_list_count_once() -> None:
    fused = reciprocal_rank_fusion([ids("a", "a", "b")])

    assert dict(fused)[ChunkId("a")] == pytest.approx(1 / 61)


def test_limit_truncates_after_sorting() -> None:
    fused = reciprocal_rank_fusion([ids("a", "b", "c")], limit=2)

    assert [chunk for chunk, _ in fused] == [ChunkId("a"), ChunkId("b")]


def test_smaller_k_weights_the_top_ranks_more() -> None:
    _, high_k = reciprocal_rank_fusion([ids("a", "b")], k=60)[0]
    _, low_k = reciprocal_rank_fusion([ids("a", "b")], k=1)[0]

    assert low_k > high_k


def test_a_half_weighted_list_cannot_outvote_the_first_list() -> None:
    # The lexical list's best chunk scores lower than the vector list's best chunk, even alone.
    fused = dict(reciprocal_rank_fusion([ids("vector"), ids("lexical")], weights=(1.0, 0.5)))

    assert fused[ChunkId("vector")] > fused[ChunkId("lexical")]


def test_half_weight_still_promotes_a_chunk_that_both_lists_found() -> None:
    # Present at rank 3 in the vector list and rank 1 in the lexical list: 1/63 + 0.5/61 beats
    # 1/61, so agreement between retrievers is worth more than either alone.
    fused = reciprocal_rank_fusion([ids("a", "b", "shared"), ids("shared")], weights=(1.0, 0.5))

    assert [chunk for chunk, _ in fused][:2] == [ChunkId("shared"), ChunkId("a")]


def test_equal_weights_are_the_default() -> None:
    weighted = reciprocal_rank_fusion([ids("a"), ids("b")], weights=(1.0, 1.0))
    default = reciprocal_rank_fusion([ids("a"), ids("b")])

    assert weighted == default


def test_rejects_invalid_parameters() -> None:
    with pytest.raises(ValueError, match="k"):
        reciprocal_rank_fusion([], k=0)
    with pytest.raises(ValueError, match="limit"):
        reciprocal_rank_fusion([], limit=-1)
    with pytest.raises(ValueError, match="same length"):
        reciprocal_rank_fusion([ids("a")], weights=(1.0, 0.5))
    with pytest.raises(ValueError, match="positive"):
        reciprocal_rank_fusion([ids("a")], weights=(0.0,))


def test_dedupe_preserves_order() -> None:
    assert dedupe(ids("b", "a", "b")) == (ChunkId("b"), ChunkId("a"))

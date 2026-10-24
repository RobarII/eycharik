"""Properties of the pure rules, not a handful of examples.

Chunking, fusion, retention, and cursors are the places where a plausible example passes and a
real document does not: a long paragraph, a duplicate chunk id, a cursor with a nested value. The
examples in the other test modules pin the decisions; these pin the invariants.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from onboarding.api.cursor import CursorError, decode, encode
from onboarding.core.chunking import split_document
from onboarding.core.models import Document
from onboarding.core.ranking import reciprocal_rank_fusion
from onboarding.core.retention import PERSONAL_AUDIT_KEYS, cutoff, expired, redact_fields

SENTENCE = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\r\n"),
    min_size=1,
    max_size=80,
).filter(lambda value: value.strip() == value and value)

TEXT = st.lists(SENTENCE, min_size=0, max_size=8).map("\n\n".join)
DATED = date(2026, 10, 20)


@settings(max_examples=40, deadline=None)
@given(text=TEXT)
def test_chunk_ids_are_stable_and_indexed(text: str) -> None:
    document = Document(
        id="hr/policy", title="Политика", text=text, audience=("all",), valid_from=DATED
    )

    first = split_document(document, max_chars=120, overlap_chars=20)
    second = split_document(document, max_chars=120, overlap_chars=20)

    assert [chunk.id for chunk in first] == [chunk.id for chunk in second]
    assert [chunk.index for chunk in first] == list(range(len(first)))
    assert all(chunk.text.strip() for chunk in first)


@settings(max_examples=40, deadline=None)
@given(text=TEXT, max_chars=st.integers(min_value=40, max_value=200))
def test_chunking_keeps_every_unit_in_order(text: str, max_chars: int) -> None:
    document = Document(
        id="hr/policy", title="Политика", text=text, audience=("all",), valid_from=DATED
    )

    chunks = split_document(document, max_chars=max_chars, overlap_chars=max_chars // 4)

    # Overlap repeats text; it must never reorder or drop it.
    joined = _squashed("\n".join(chunk.text for chunk in chunks))
    assert _subsequence(_squashed(text), joined)


def _squashed(value: str) -> str:
    return "".join(value.split())


def _subsequence(needle: str, haystack: str) -> bool:
    position = 0
    for char in haystack:
        if position < len(needle) and char == needle[position]:
            position += 1
    return position == len(needle)


@given(
    left=st.lists(st.text(min_size=1, max_size=8), max_size=5),
    right=st.lists(st.text(min_size=1, max_size=8), max_size=5),
)
def test_fusion_ranks_only_what_it_was_given(left: list[str], right: list[str]) -> None:
    fused = reciprocal_rank_fusion([left, right])

    assert {chunk_id for chunk_id, _ in fused} <= set(left) | set(right)
    scores = [score for _, score in fused]
    assert scores == sorted(scores, reverse=True)
    assert len(fused) == len({chunk_id for chunk_id, _ in fused})


@given(
    rankings=st.lists(st.lists(st.text(min_size=1, max_size=6), max_size=4), max_size=4),
    limit=st.integers(min_value=0, max_value=6),
)
def test_fusion_never_exceeds_the_limit(rankings: list[list[str]], limit: int) -> None:
    assert len(reciprocal_rank_fusion(rankings, limit=limit)) == min(
        limit, len({chunk_id for ranking in rankings for chunk_id in ranking})
    )


@given(days=st.integers(min_value=1, max_value=3650))
def test_the_window_moves_with_the_clock(days: int) -> None:
    now = datetime(2026, 10, 23, 9, 0, tzinfo=UTC)

    assert cutoff(now, days) == now - timedelta(days=days)
    assert expired(cutoff(now, days) - timedelta(seconds=1), now, days)
    assert not expired(cutoff(now, days), now, days)


RESERVED = PERSONAL_AUDIT_KEYS | {"redacted"}


@given(
    fields=st.dictionaries(
        st.text(min_size=1, max_size=8).filter(lambda key: key not in RESERVED),
        st.integers(),
        max_size=6,
    )
)
def test_redaction_is_idempotent_and_keeps_the_skeleton(fields: dict[str, int]) -> None:
    once = redact_fields(fields)
    twice = redact_fields(once)

    assert twice == once
    assert set(once) - {"redacted"} == set(fields) - PERSONAL_AUDIT_KEYS


@given(
    payload=st.dictionaries(
        st.text(min_size=1, max_size=8),
        st.one_of(st.text(max_size=12), st.integers(), st.booleans(), st.none()),
        max_size=5,
    )
)
def test_a_cursor_round_trips(payload: dict[str, object]) -> None:
    assert decode(encode(payload)) == payload


@given(value=st.text(max_size=20))
def test_a_corrupt_cursor_is_a_value_error_not_a_crash(value: str) -> None:
    try:
        decoded = decode(value)
    except CursorError:
        return
    assert isinstance(decoded, dict)

"""The retrieval policy: one value, read by both backends.

These tests are about the pieces that used to be restated in two places. They do not compare two
rankers — a ranking function is a backend's own opinion — they compare the *admission* rules, which
are the ones that quietly decide which documents exist for a question.

The gate has two mirrors on purpose: ``test_one_shared_word_does_not_admit_a_chunk`` here runs the
in-memory backend, and ``test_the_lexical_branch_does_not_answer_with_one_shared_word`` in the
integration tier runs ``ts_rank_cd`` and the coverage subquery. Same policy, two engines.
"""

from __future__ import annotations

from datetime import date

import pytest

from onboarding.app.knowledge.embedding import HashingEmbedder
from onboarding.app.knowledge.memory import InMemoryKnowledgeBase
from onboarding.core.chunking import DEFAULT_MAX_CHARS, DEFAULT_OVERLAP_CHARS
from onboarding.core.models import Chunk, DocId, Document
from onboarding.core.ranking import LEXICAL_WEIGHT
from onboarding.core.retrieval import (
    DEFAULT_COVERAGE_FLOOR,
    DEFAULT_OVERFETCH,
    RetrievalPolicy,
)
from onboarding.ports import SearchQuery

ON_DATE = date(2026, 10, 24)


def chunk(index: int = 0, text: str = "текст", context: str = "") -> Chunk:
    return Chunk(
        id=f"hr/test#{index}",  # type: ignore[arg-type]
        doc_id=DocId("hr/test"),
        index=index,
        text=text,
        context=context,
    )


def test_the_default_policy_is_the_shipped_configuration() -> None:
    policy = RetrievalPolicy()

    assert policy.max_chars == DEFAULT_MAX_CHARS
    assert policy.overlap_chars == DEFAULT_OVERLAP_CHARS
    assert policy.lexical_weight == LEXICAL_WEIGHT
    assert policy.coverage_floor == DEFAULT_COVERAGE_FLOOR
    assert policy.overfetch == DEFAULT_OVERFETCH


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"max_chars": 0}, "max_chars"),
        ({"max_chars": 100, "overlap_chars": 100}, "overlap_chars"),
        ({"overlap_chars": -1}, "overlap_chars"),
        ({"lexical_weight": 0.0}, "lexical_weight"),
        ({"lexical_weight": 1.5}, "lexical_weight"),
        ({"coverage_floor": 0}, "coverage_floor"),
        ({"overfetch": 0}, "overfetch"),
    ],
)
def test_an_invalid_policy_is_refused_at_construction(
    kwargs: dict[str, float], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        RetrievalPolicy(**kwargs)  # type: ignore[arg-type]


def test_the_gate_is_a_floor_capped_by_the_question() -> None:
    policy = RetrievalPolicy(coverage_floor=3)

    assert policy.coverage_required(7) == 3
    assert policy.coverage_required(3) == 3
    assert policy.coverage_required(2) == 2
    assert policy.coverage_required(1) == 1
    # A question with no tokens must not admit anything, and a requirement of zero would admit all.
    assert policy.coverage_required(0) == 1
    assert not policy.lexical_admits(0, 0)


def test_admission_is_coverage_against_the_requirement() -> None:
    policy = RetrievalPolicy(coverage_floor=3)

    assert policy.lexical_admits(3, 6)
    assert not policy.lexical_admits(2, 6)
    # A two-word question gates on both words, not on the floor.
    assert policy.lexical_admits(2, 2)
    assert not policy.lexical_admits(1, 2)


def test_the_embedder_and_the_lexical_index_read_one_view() -> None:
    """If they read different views, the vector and the lexemes describe different documents."""
    policy = RetrievalPolicy()
    piece = chunk(text="квота сохраняется", context="Раздел про отпуск")

    assert policy.embedding_view(piece) == piece.embedding_text
    assert policy.lexical_view(piece) == piece.embedding_text
    assert "Раздел про отпуск" in policy.embedding_view(piece)
    assert "квота сохраняется" in policy.embedding_view(piece)


def test_a_contextual_chunk_is_embedded_with_its_context() -> None:
    policy = RetrievalPolicy()
    plain = chunk(text="Квота сохраняется на второй год.")
    contextual = chunk(text="Квота сохраняется на второй год.", context="Отпуска и отгулы")

    assert policy.embedding_view(plain) != policy.embedding_view(contextual)


def test_a_lexical_only_hit_cannot_outrank_the_vector_head() -> None:
    """Half weight is what stops one shared word from displacing a whole-question vector match."""
    policy = RetrievalPolicy(lexical_weight=0.5)

    fused = policy.fuse(["a#0", "b#0", "c#0"], ["c#0", "d#0"])  # type: ignore[arg-type]
    order = [str(chunk_id) for chunk_id, _ in fused]

    # ``d`` is second in the lexical list and exists in no vector list: it stays below the head.
    assert order.index("d#0") > order.index("a#0")
    # ``c`` is in both lists, and that agreement is what puts it first.
    assert order[0] == "c#0"


def test_a_chunk_found_by_both_retrievers_wins() -> None:
    policy = RetrievalPolicy()

    fused = policy.fuse(["a#0", "b#0"], ["b#0", "c#0"])  # type: ignore[arg-type]

    assert str(fused[0][0]) == "b#0"


def test_fusion_respects_the_limit() -> None:
    policy = RetrievalPolicy()

    fused = policy.fuse(["a#0", "b#0", "c#0"], ["d#0"], limit=2)  # type: ignore[arg-type]

    assert len(fused) == 2


def document(doc_id: str, text: str) -> Document:
    return Document(
        id=DocId(doc_id),
        title=doc_id,
        text=text,
        audience=("all",),
        valid_from=date(2020, 1, 1),
    )


async def test_one_shared_word_does_not_admit_a_chunk() -> None:
    """The in-memory mirror of the SQL gate test: a chunk matching one question word stays out."""
    kb = await InMemoryKnowledgeBase.build(
        [
            document("hr/leave-policy", "Отпуск положен в первый год. Двадцать восемь дней."),
            document("hr/days-off", "День отдыха за свой счёт оформляется заявлением."),
        ],
        HashingEmbedder(dim=512),
        policy=RetrievalPolicy(coverage_floor=3),
    )

    results = await kb.search(
        SearchQuery(
            text="Сколько дней отпуска положено в первый год?",
            audience=("all",),
            on_date=ON_DATE,
            limit=30,
        )
    )

    # The gate governs the lexical list, not the vector one: ``hr/days-off`` still reaches the
    # fusion through its vector score. What the gate buys is the order — the chunk that covers the
    # question comes first, and one shared word does not promote the other chunk above it.
    assert results
    assert results[0].chunk.doc_id == "hr/leave-policy"


async def test_a_two_word_question_gates_on_both_words() -> None:
    kb = await InMemoryKnowledgeBase.build(
        [
            document("hr/dms", "Условия ДМС описаны в полисе."),
            document("hr/dms-old", "Полис действует с первого дня."),
        ],
        HashingEmbedder(dim=512),
        policy=RetrievalPolicy(coverage_floor=3),
    )

    results = await kb.search(
        SearchQuery(
            text="условия ДМС",
            audience=("all",),
            on_date=ON_DATE,
            limit=30,
        )
    )

    assert results
    assert results[0].chunk.doc_id == "hr/dms"


async def test_an_empty_index_is_not_an_error() -> None:
    kb = await InMemoryKnowledgeBase.build([], HashingEmbedder(dim=64))

    assert await kb.search(SearchQuery(text="что-нибудь", audience=("all",), on_date=ON_DATE)) == ()

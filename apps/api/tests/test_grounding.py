from __future__ import annotations

from dataclasses import replace

import pytest

from onboarding.core.grounding import judge
from onboarding.core.models import AnswerDraft, ChunkId, RefusalReason

RETRIEVED = frozenset({ChunkId("hr/leave-policy#0"), ChunkId("hr/leave-policy#1")})
MIN = 0.4


def draft(**overrides: object) -> AnswerDraft:
    base = AnswerDraft(
        answer="Отпуск — 28 дней [hr/leave-policy#0]",
        citations=(ChunkId("hr/leave-policy#0"),),
        confidence=0.9,
        escalate=False,
        reason="answered",
    )
    return replace(base, **overrides)  # type: ignore[arg-type]


def test_accepts_a_grounded_answer() -> None:
    verdict = judge(draft(), RETRIEVED, min_confidence=MIN)

    assert verdict.accepted
    assert verdict.reason == "answered"
    assert verdict.citations == (ChunkId("hr/leave-policy#0"),)


def test_rejects_an_answer_without_citations() -> None:
    verdict = judge(draft(citations=()), RETRIEVED, min_confidence=MIN)

    assert not verdict.accepted
    assert verdict.reason == RefusalReason.NO_SOURCES.value


def test_rejects_a_citation_that_was_not_retrieved() -> None:
    verdict = judge(
        draft(citations=(ChunkId("hr/secret#9"),)),
        RETRIEVED,
        min_confidence=MIN,
    )

    assert not verdict.accepted
    assert verdict.reason == RefusalReason.NO_SOURCES.value


def test_rejects_an_inline_citation_that_was_not_retrieved() -> None:
    verdict = judge(
        draft(answer="Отпуск — 28 дней [hr/secret#9]"),
        RETRIEVED,
        min_confidence=MIN,
    )

    assert not verdict.accepted
    assert verdict.reason == RefusalReason.NO_SOURCES.value


def test_rejects_a_malformed_inline_citation() -> None:
    for answer in (
        "Отпуск — 28 дней [hr/leave-policy#0#0]",
        "Отпуск — 28 дней [hr/leave-policy]",
    ):
        verdict = judge(draft(answer=answer), RETRIEVED, min_confidence=MIN)

        assert not verdict.accepted, answer
        assert verdict.reason == RefusalReason.NO_SOURCES.value


def test_ignores_brackets_that_are_not_citations() -> None:
    verdict = judge(
        draft(answer="Отпуск — 28 дней [по трудовому кодексу] [hr/leave-policy#0]"),
        RETRIEVED,
        min_confidence=MIN,
    )

    assert verdict.accepted


def test_rejects_low_confidence() -> None:
    verdict = judge(draft(confidence=0.1), RETRIEVED, min_confidence=MIN)

    assert not verdict.accepted
    assert verdict.reason == RefusalReason.LOW_CONFIDENCE.value


def test_model_escalation_is_passed_through() -> None:
    verdict = judge(
        draft(
            answer="Передаю вопрос HR.",
            citations=(),
            escalate=True,
            reason="restricted",
        ),
        RETRIEVED,
        min_confidence=MIN,
    )

    assert verdict.accepted
    assert verdict.reason == "restricted"
    assert verdict.citations == ()


def test_confidence_outside_the_unit_interval_is_a_programming_error() -> None:
    with pytest.raises(ValueError, match="confidence"):
        judge(draft(confidence=1.5), RETRIEVED, min_confidence=MIN)

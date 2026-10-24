"""The eval gates have to be able to fail.

A gate that no plausible regression can trip is decoration. This module breaks the pipeline on
purpose, one leg at a time, and asserts that the gate named for that leg turns red. It runs on
fakes: no database, no provider, no network, so `make check` can enforce it on every change.

If a mutant survives, the gate is lying: either the metric is not measured where it claims to be,
or the threshold is loose enough to swallow a real fault.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytest

from onboarding.app.worker.answerer import AnswerOutcome
from onboarding.core.models import Chunk, ChunkId, DocId, ScoredChunk
from onboarding.evals.runner import (
    Case,
    Report,
    evaluate,
    load_cases,
    summarise,
)
from onboarding.ports import (
    Completion,
    EmployeeProfile,
    KnowledgeUnavailableError,
    SearchQuery,
)

ROOT = Path(__file__).resolve().parents[3]
ON_DATE = date(2026, 10, 23)

QUESTION = "Сколько дней отпуска?"
REFUSED = "Покажи вилки окладов"


@dataclass(frozen=True, slots=True)
class FakeKnowledge:
    """A knowledge base that answers from a fixed map instead of a database."""

    docs: dict[str, tuple[str, ...]]
    dead: bool = False

    async def search(self, query: SearchQuery) -> tuple[ScoredChunk, ...]:
        if self.dead:
            raise KnowledgeUnavailableError("embedder is down")
        return tuple(
            ScoredChunk(
                chunk=Chunk(
                    id=ChunkId(f"{doc}#0"),
                    doc_id=DocId(doc),
                    index=0,
                    text="28 календарных дней",
                ),
                score=1.0,
            )
            for doc in self.docs.get(query.text, ())
        )


@dataclass(frozen=True, slots=True)
class FakeAnswerer:
    """An answerer with deliberate faults, chosen by the constructor."""

    texts: dict[str, str]
    escalations: tuple[str, ...] = ()
    escalate_all: bool = False
    reason: str = "no_sources"
    citations: str = "retrieved"
    wrong_context: bool = False
    context_text: str = "28 календарных дней"
    answer_text: str | None = None
    forbidden: str = ""

    async def answer(
        self,
        question: str,
        profile: EmployeeProfile,
        on_date: date,
    ) -> AnswerOutcome:
        del profile, on_date
        escalated = self.escalate_all or question in self.escalations
        doc = "hr/irrelevant" if self.wrong_context else "hr/leave-policy"
        retrieved = (
            ScoredChunk(
                chunk=Chunk(
                    id=ChunkId("held#0"),
                    doc_id=DocId(doc),
                    index=0,
                    text=self.context_text,
                ),
                score=1.0,
            ),
        )
        if self.citations == "retrieved":
            citations = tuple(chunk.chunk.id for chunk in retrieved)
        elif self.citations == "none":
            citations = ()
        else:
            citations = (ChunkId("ghost"),)
        text = self.answer_text or self.texts.get(question, "нет ответа")
        if self.forbidden:
            text = f"{text} {self.forbidden}"
        return AnswerOutcome(
            text=text,
            escalated=escalated,
            reason=self.reason if escalated else "answered",
            citations=citations,
            retrieved=retrieved,
            completion=Completion(text=text, latency_ms=100, cost_rub=0.01),
        )


GOOD_DOCS: dict[str, tuple[str, ...]] = {
    QUESTION: ("hr/leave-policy",),
    REFUSED: (),
}
GOOD_TEXTS = {QUESTION: "Положено 28 календарных дней."}


def _cases() -> tuple[Case, ...]:
    return (
        Case(
            id="answerable",
            question=QUESTION,
            audience="all",
            expect_docs=("hr/leave-policy",),
            expect_contains=("28 календарных",),
            expect_escalation=False,
            expect_reason=None,
            stratum="neardup",
            expect_not_contains=("24 календарных",),
        ),
        Case(
            id="hidden",
            question=REFUSED,
            audience="all",
            expect_docs=(),
            expect_contains=(),
            expect_escalation=True,
            expect_reason="no_sources",
            expect_absent_docs=("hr/salary-bands",),
            stratum="acl",
        ),
    )


def answerer(**faults: object) -> FakeAnswerer:
    defaults: dict[str, object] = {"escalations": (REFUSED,)}
    return FakeAnswerer(GOOD_TEXTS, **{**defaults, **faults})  # type: ignore[arg-type]


async def _run(knowledge: FakeKnowledge, model: FakeAnswerer) -> Report:
    results = await evaluate(
        _cases(),
        knowledge=knowledge,  # type: ignore[arg-type]
        answerer=model,  # type: ignore[arg-type]
        on_date=ON_DATE,
    )
    return summarise(results, generated=True)


async def test_the_healthy_pipeline_passes_every_gate() -> None:
    report = await _run(FakeKnowledge(GOOD_DOCS), answerer())

    assert report.failures == (), report.failures


async def test_an_embedder_that_loses_the_document_fails_recall() -> None:
    report = await _run(FakeKnowledge({}), answerer())

    assert "recall_at_5" in report.failures
    assert "mrr" in report.failures


async def test_a_reranker_that_keeps_the_wrong_document_fails_context_recall() -> None:
    report = await _run(FakeKnowledge(GOOD_DOCS), answerer(wrong_context=True))

    assert "context_recall_at_5" in report.failures


async def test_a_disabled_acl_guard_fails_the_leak_gate() -> None:
    leaky = {**GOOD_DOCS, REFUSED: ("hr/salary-bands",)}
    report = await _run(FakeKnowledge(leaky), answerer())

    assert "leak_rate" in report.failures


async def test_an_answer_that_cites_nothing_fails_citation_support() -> None:
    report = await _run(FakeKnowledge(GOOD_DOCS), answerer(citations="none"))

    assert "citation_support" in report.failures


async def test_a_citation_outside_the_context_fails_citation_support() -> None:
    report = await _run(FakeKnowledge(GOOD_DOCS), answerer(citations="ghost"))

    assert "citation_support" in report.failures


async def test_answering_a_question_that_must_escalate_fails_escalation() -> None:
    report = await _run(FakeKnowledge(GOOD_DOCS), FakeAnswerer(GOOD_TEXTS))

    assert "escalation_correctness" in report.failures


async def test_escalating_everything_fails_escalation_too() -> None:
    report = await _run(FakeKnowledge(GOOD_DOCS), answerer(escalate_all=True))

    assert "escalation_correctness" in report.failures


async def test_an_answer_quoting_the_expired_edition_fails_the_exclusion_gate() -> None:
    report = await _run(
        FakeKnowledge(GOOD_DOCS),
        answerer(forbidden="По прошлому изданию 24 календарных дня."),
    )

    assert "answer_excludes" in report.failures


async def test_a_provider_outage_is_an_error_not_a_quality_regression() -> None:
    results = await evaluate(
        _cases(),
        knowledge=FakeKnowledge(GOOD_DOCS),  # type: ignore[arg-type]
        answerer=None,
        on_date=ON_DATE,
    )
    report = summarise(results, generated=False)

    assert report.metrics["recall_at_5"] == 1.0
    assert "case_errors" not in report.metrics


async def test_a_dead_retrieval_counts_as_a_case_error() -> None:
    class DeadKnowledge:
        async def search(self, query: SearchQuery) -> tuple[ScoredChunk, ...]:
            del query
            raise KnowledgeUnavailableError("embedder is down")

    results = await evaluate(
        _cases(),
        knowledge=DeadKnowledge(),  # type: ignore[arg-type]
        answerer=None,
        on_date=ON_DATE,
    )
    report = summarise(results, generated=False)

    assert report.metrics["case_errors"] == 2.0
    assert "case_errors" in report.failures


async def test_a_missed_crisis_is_not_hidden_by_the_other_cases() -> None:
    """``escalation_correctness`` is averaged over every case, so one miss costs it 1%.

    The three decision metrics use the deciding cases as the denominator instead. With two cases
    here, a missed escalation halves the denominator and cannot pass.
    """
    report = await _run(FakeKnowledge(GOOD_DOCS), answerer(escalations=()))

    assert report.metrics["escalation_recall"] == 0.0
    assert "escalation_recall" in report.failures


async def test_a_false_alarm_is_a_failure_and_not_a_safe_default() -> None:
    report = await _run(FakeKnowledge(GOOD_DOCS), answerer(escalate_all=True))

    assert report.metrics["escalation_precision"] == 0.5
    assert "escalation_precision" in report.failures


async def test_the_routing_reason_is_gated_on_the_cases_that_carry_one() -> None:
    report = await _run(FakeKnowledge(GOOD_DOCS), answerer(reason="low_confidence"))

    assert report.metrics["reason_accuracy"] == 0.0
    assert "reason_accuracy" in report.failures


async def test_the_real_golden_set_can_fail_its_own_recall_gate() -> None:
    """The set, not just a toy case list, has to be able to turn the gate red."""
    cases = load_cases(ROOT / "docs" / "evals" / "golden.yaml")
    results = await evaluate(
        cases,
        knowledge=FakeKnowledge({}),  # type: ignore[arg-type]
        answerer=None,
        on_date=ON_DATE,
    )
    report = summarise(results, generated=False)

    assert report.metrics["recall_at_5"] == 0.0
    assert "recall_at_5" in report.failures


# Every gate named in GATES/MAXIMUMS has to appear here. Adding a gate without adding a mutant
# leaves a threshold that nobody has ever seen fail.
LEAKY_DOCS = {**GOOD_DOCS, REFUSED: ("hr/salary-bands",)}
MUTANTS: dict[str, tuple[dict[str, object], dict[str, object]]] = {
    "recall_at_5": ({"docs": {}}, {}),
    "mrr": ({"docs": {"Сколько дней отпуска?": ("hr/other",)}}, {}),
    "context_recall_at_5": ({"docs": GOOD_DOCS}, {"wrong_context": True}),
    "context_fragment_coverage": ({"docs": GOOD_DOCS}, {"context_text": "ничего"}),
    "citation_support": ({"docs": GOOD_DOCS}, {"citations": "none"}),
    "escalation_correctness": ({"docs": GOOD_DOCS}, {"escalate_all": True}),
    "escalation_recall": ({"docs": GOOD_DOCS}, {"escalations": ()}),
    "escalation_precision": ({"docs": GOOD_DOCS}, {"escalate_all": True}),
    "reason_accuracy": ({"docs": GOOD_DOCS}, {"reason": "low_confidence"}),
    "answer_contains": ({"docs": GOOD_DOCS}, {"answer_text": "не знаю"}),
    "answer_excludes": ({"docs": GOOD_DOCS}, {"forbidden": "24 календарных"}),
    "leak_rate": ({"docs": LEAKY_DOCS}, {}),
    "case_errors": ({"docs": GOOD_DOCS, "dead": True}, {}),
}


@pytest.mark.parametrize("mutant", sorted(MUTANTS))
async def test_every_gate_has_a_mutant_that_trips_it(mutant: str) -> None:
    knowledge_faults, answerer_faults = MUTANTS[mutant]
    report = await _run(
        FakeKnowledge(**knowledge_faults),  # type: ignore[arg-type]
        answerer(**answerer_faults),
    )

    assert mutant in report.failures, (
        f"mutant {mutant} survived: gate {mutant} cannot fail, so it protects nothing"
    )

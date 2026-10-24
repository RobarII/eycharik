"""The evaluation harness is a library, not a script that happens to have functions.

Every eval used to reach for ``build_container`` and a database connection before it could score
anything, so a change to the harness could only be tested against a running Postgres and a provider
key. That is the opposite of what a gate needs: the thing that judges the product must be the
cheapest thing in the repository to run.

These tests take the same entry points the CLI calls and hand them fakes. No database, no key, no
network: three cases, a scripted retriever, and numbers a human would check by hand.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from onboarding.app.knowledge.ingest import load_corpus
from onboarding.evals.acl import CorpusDocument, matrix, run
from onboarding.evals.artifact import commit_hash, stem
from onboarding.evals.runner import Case, evaluate, summarise
from onboarding.ports import KnowledgeUnavailableError, SearchQuery

from .fakes import FakeKnowledgeBase, profile, scored_chunk

ROOT = Path(__file__).resolve().parents[3]
ON_DATE = date(2026, 10, 23)


def case(case_id: str, *, expect: tuple[str, ...], absent: tuple[str, ...] = ()) -> Case:
    return Case(
        id=case_id,
        question=f"вопрос {case_id}",
        audience="dept:it",
        expect_docs=expect,
        expect_contains=(),
        expect_escalation=False,
        expect_reason=None,
        expect_absent_docs=absent,
    )


async def test_a_hit_is_recalled_and_a_miss_is_not() -> None:
    cases = (case("hit", expect=("hr/a",)), case("miss", expect=("hr/b",)))
    knowledge = FakeKnowledgeBase(chunks=(scored_chunk("hr/a#0"),))

    results = await evaluate(cases, knowledge=knowledge, answerer=None, on_date=ON_DATE)

    assert [result.recall for result in results] == [1.0, 0.0]
    assert knowledge.queries[0].text == "вопрос hit"
    assert knowledge.queries[0].audience == profile().audience


async def test_a_forbidden_document_is_a_leak_even_when_the_expected_one_is_found() -> None:
    cases = (case("acl", expect=("hr/a",), absent=("hr/secret",)),)
    knowledge = FakeKnowledgeBase(chunks=(scored_chunk("hr/a#0"), scored_chunk("hr/secret#0")))

    results = await evaluate(cases, knowledge=knowledge, answerer=None, on_date=ON_DATE)
    report = summarise(results, generated=False)

    assert results[0].leaked_docs == ("hr/secret",)
    assert report.metrics["leak_rate"] == pytest.approx(1.0)
    assert report.failures


async def test_a_retrieval_outage_is_neither_a_miss_nor_a_wrong_answer() -> None:
    class Unavailable:
        async def search(self, query: SearchQuery) -> tuple[()]:
            del query
            raise KnowledgeUnavailableError("db is down")

    results = await evaluate(
        (case("down", expect=("hr/a",)),),
        knowledge=Unavailable(),  # type: ignore[arg-type]
        answerer=None,
        on_date=ON_DATE,
    )

    assert results[0].error.startswith("retrieval:")
    assert results[0].recall == 0.0
    assert not results[0].leaked_docs


def corpus_documents() -> tuple[CorpusDocument, ...]:
    """Two documents with different audiences, built without touching a database."""
    return (
        CorpusDocument(
            doc_id="hr/a", title="Отпуск", audience=("all",), question="сколько дней отпуска"
        ),
        CorpusDocument(
            doc_id="hr/secret", title="Оклады", audience=("hr_only",), question="какие оклады"
        ),
    )


def test_the_acl_matrix_needs_no_connection() -> None:
    cases = matrix(corpus_documents(), on_date=ON_DATE)

    assert {item.audience for item in cases} == {
        "all",
        "hr_only",
        "dept:it",
        "dept:sales",
        "dept:production",
    }
    # Every viewer x every document, with the audience it must not see named in the case.
    assert len(cases) == 2 * 5
    hr_reader = [item for item in cases if item.audience == "hr_only" and "hr-secret" in item.id]
    assert hr_reader
    assert hr_reader[0].expect_docs == ("hr/secret",)
    shared_reader = [item for item in cases if item.audience == "all" and "hr-secret" in item.id]
    assert shared_reader
    assert shared_reader[0].expect_docs == ()


async def test_the_acl_matrix_scores_against_any_knowledge_base() -> None:
    cases = matrix(corpus_documents(), on_date=ON_DATE)
    knowledge = FakeKnowledgeBase(chunks=(scored_chunk("hr/a#0"),))

    report = await run(cases, knowledge, on_date=ON_DATE)

    # Only the shared document is retrievable: every viewer sees it, nobody sees the other.
    assert report.metrics["leak_rate"] == pytest.approx(0.0)
    assert report.metrics["recall_at_5"] < 1.0


def test_the_corpus_loads_without_a_database() -> None:
    loaded = load_corpus(ROOT / "knowledge", ROOT / "docs" / "contracts" / "doc.schema.json")

    assert loaded


def test_an_artifact_name_sorts_by_date_and_reads_as_a_command() -> None:
    assert stem(ON_DATE, kind="retrieval", label="acl-matrix") == (
        "2026-10-23-eval-retrieval-acl-matrix"
    )
    assert stem(ON_DATE, kind="full") == "2026-10-23-eval-full"


def test_the_commit_is_resolved_in_one_place() -> None:
    """Four copies used to disagree inside one run; one function cannot disagree with itself."""
    assert commit_hash()

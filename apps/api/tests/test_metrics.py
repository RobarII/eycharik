from __future__ import annotations

from pathlib import Path

import pytest

from onboarding.core.metrics import mean, percentile, recall_at_k, reciprocal_rank
from onboarding.evals.runner import (
    MAXIMUMS,
    Case,
    CaseResult,
    RegradeError,
    Report,
    _render_metrics,
    _render_strata,
    merge_records,
    regrade,
    summarise,
)


def test_recall_counts_expected_documents_in_the_top_k() -> None:
    assert recall_at_k(["a", "b"], ["x", "a", "b", "c", "d"], k=5) == 1.0
    assert recall_at_k(["a", "b"], ["x", "a", "y", "z", "w"], k=5) == 0.5
    assert recall_at_k(["a"], ["a", "b"], k=1) == 1.0
    assert recall_at_k(["a"], ["b", "a"], k=1) == 0.0


def test_recall_of_nothing_expected_is_one() -> None:
    assert recall_at_k([], ["a"]) == 1.0


def test_reciprocal_rank_uses_the_first_hit() -> None:
    assert reciprocal_rank(["b"], ["a", "b", "c"]) == pytest.approx(0.5)
    assert reciprocal_rank(["a"], ["a"]) == 1.0
    assert reciprocal_rank(["z"], ["a", "b"]) == 0.0


def test_percentile_uses_nearest_rank() -> None:
    values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    assert percentile(values, p=50) == 5
    assert percentile(values, p=95) == 10
    assert percentile([], p=95) == 0.0


def test_percentile_rejects_a_bad_p() -> None:
    with pytest.raises(ValueError, match="within"):
        percentile([1], p=101)


def test_mean_handles_empty_input() -> None:
    assert mean([]) == 0.0
    assert mean([1, 2, 3]) == 2.0


def test_escalation_cases_do_not_drag_retrieval_metrics() -> None:

    def result(case_id: str, expected: tuple[str, ...], rr: float) -> CaseResult:
        case = Case(
            id=case_id,
            question="q",
            audience="all",
            expect_docs=expected,
            expect_contains=(),
            expect_escalation=not expected,
            expect_reason=None,
        )
        return CaseResult(case=case, retrieved_docs=("a",), recall=1.0, rr=rr)

    report = summarise(
        (result("answerable", ("a",), 1.0), result("refusal", (), 0.0)),
        generated=False,
    )

    assert report.metrics["mrr"] == 1.0
    assert "citation_support" not in report.metrics


def test_expected_fragments_are_a_gate() -> None:
    case = Case(
        id="content",
        question="q",
        audience="all",
        expect_docs=("a",),
        expect_contains=("28",),
        expect_escalation=False,
        expect_reason=None,
    )
    good = CaseResult(
        case=case,
        retrieved_docs=("a",),
        recall=1.0,
        rr=1.0,
        answer="28 дней",
        escalated=False,
        reason="answered",
        retrieved_citations=1,
        accepted_citations=1,
    )
    bad = CaseResult(
        case=case,
        retrieved_docs=("a",),
        recall=1.0,
        rr=1.0,
        answer="нет данных",
        escalated=False,
        reason="answered",
        retrieved_citations=1,
        accepted_citations=1,
    )

    assert summarise((good,), generated=True).metrics["answer_contains"] == 1.0
    assert summarise((bad,), generated=True).failures == ("answer_contains",)


def test_escalation_must_match_the_expected_reason() -> None:
    case = Case(
        id="restricted",
        question="q",
        audience="all",
        expect_docs=(),
        expect_contains=(),
        expect_escalation=True,
        expect_reason="restricted",
    )

    wrong = CaseResult(
        case=case, retrieved_docs=(), recall=0.0, rr=0.0, escalated=True, reason="no_sources"
    )
    right = CaseResult(
        case=case, retrieved_docs=(), recall=0.0, rr=0.0, escalated=True, reason="restricted"
    )

    assert wrong.escalation_correct is False
    assert right.escalation_correct is True


def test_latency_gate_is_an_upper_bound() -> None:
    fast = Report(metrics={"p95_completion_ms": 1200.0}, results=(), generated=True)
    slow = Report(metrics={"p95_completion_ms": 9000.0}, results=(), generated=True)
    crawling = Report(metrics={"p95_answer_ms": 20000.0}, results=(), generated=True)
    weak = Report(metrics={"recall_at_5": 0.5}, results=(), generated=True)

    assert fast.failures == ()
    assert slow.failures == ("p95_completion_ms",)
    assert crawling.failures == ("p95_answer_ms",)
    assert weak.failures == ("recall_at_5",)


def test_a_demo_gateway_reports_latency_without_gating_on_it() -> None:
    """A cross-border endpoint cannot answer for personal data (ADR 0030), so its p95 is a vendor.

    The number stays in the report — hiding it would be the lie the gate exists to prevent — but a
    red mark against it would read as a defect of the system the pilot would not run on.
    """
    demo = Report(
        metrics={"p95_completion_ms": 11355.0, "p95_answer_ms": 20771.0, "recall_at_5": 0.99},
        results=(),
        generated=True,
        personal_data=False,
    )

    assert demo.failures == ()
    assert demo.diagnostics == ("p95_completion_ms", "p95_answer_ms")
    assert "диагностика" in "".join(_render_metrics(demo))


def test_the_pilot_contour_still_gates_on_latency() -> None:
    pilot = Report(
        metrics={"p95_completion_ms": 11355.0},
        results=(),
        generated=True,
        personal_data=True,
    )

    assert pilot.failures == ("p95_completion_ms",)
    assert pilot.diagnostics == ()


def test_a_leak_is_a_gate_on_every_contour() -> None:
    """The contour relaxes a vendor budget, never confidentiality."""
    demo = Report(
        metrics={"leak_rate": 0.1, "p95_answer_ms": 90000.0},
        results=(),
        generated=True,
        personal_data=False,
    )

    assert demo.failures == ("leak_rate",)


def test_the_completion_budget_matches_the_documented_one() -> None:
    assert MAXIMUMS["p95_completion_ms"] == 8000.0


def test_the_answer_budget_is_wider_than_the_completion_budget() -> None:
    """The whole answer adds retrieval, rerank, and generation to the provider call."""
    assert MAXIMUMS["p95_answer_ms"] > MAXIMUMS["p95_completion_ms"]


def test_an_answer_without_a_citation_does_not_pass_citation_support() -> None:
    case = Case(
        id="uncited",
        question="q",
        audience="all",
        expect_docs=("a",),
        expect_contains=(),
        expect_escalation=False,
        expect_reason=None,
    )
    uncited = CaseResult(
        case=case,
        retrieved_docs=("a",),
        recall=1.0,
        rr=1.0,
        answer="28 дней",
        escalated=False,
        reason="answered",
    )
    cited = CaseResult(
        case=case,
        retrieved_docs=("a",),
        recall=1.0,
        rr=1.0,
        answer="28 дней",
        escalated=False,
        reason="answered",
        retrieved_citations=1,
        accepted_citations=1,
    )

    assert summarise((uncited,), generated=True).metrics["citation_support"] == 0.0
    assert summarise((cited,), generated=True).metrics["citation_support"] == 1.0


def test_a_stratum_without_documents_reports_no_recall_instead_of_zero() -> None:
    """``mean([]) == 0.0`` used to make "no such case" read as "total retrieval failure".

    The injection and unanswerable strata expect no document at all, so their recall is not zero —
    it does not exist. The table renders an absent metric as "-".
    """
    case = Case(
        id="refuse",
        question="q",
        audience="all",
        expect_docs=(),
        expect_contains=(),
        expect_escalation=True,
        expect_reason="no_sources",
        stratum="unanswerable",
    )
    result = CaseResult(
        case=case, retrieved_docs=(), recall=1.0, rr=0.0, escalated=True, reason="no_sources"
    )

    report = summarise((result,), generated=True)

    assert "recall_at_5" not in report.strata["unanswerable"]
    assert "mrr" not in report.strata["unanswerable"]
    assert _render_strata(report)[-1].endswith("| - | 1.00 | - |")


def test_a_stratum_metric_that_exists_is_still_reported() -> None:
    case = Case(
        id="fact",
        question="q",
        audience="all",
        expect_docs=("a",),
        expect_contains=(),
        expect_escalation=False,
        expect_reason=None,
    )
    result = CaseResult(case=case, retrieved_docs=("a",), recall=1.0, rr=1.0)

    report = summarise((result,), generated=False)

    assert report.strata["fact"]["recall_at_5"] == 1.0


def test_regrade_recomputes_the_verdicts_from_the_recorded_answer() -> None:
    """A golden set that changes must move the numbers without a provider call."""
    case = Case(
        id="leave",
        question="q",
        audience="all",
        expect_docs=("a",),
        expect_contains=("14 календарных дней",),
        expect_escalation=False,
        expect_reason=None,
    )
    records = {
        "leave": {
            "case": "leave",
            "retrieved": ["a"],
            "context": ["a"],
            "answer": "До 14 календарных дней в год.",
            "escalated": False,
            "reason": "answered",
            "citations": 1,
            "accepted_citations": 1,
        }
    }

    graded = regrade((case,), records)

    assert graded[0].contains_expected is True
    assert graded[0].recall == 1.0
    assert graded[0].case.expect_contains == ("14 календарных дней",)


def test_regrade_follows_a_changed_golden_expectation() -> None:
    case = Case(
        id="leave",
        question="q",
        audience="all",
        expect_docs=("b",),
        expect_contains=("21 день",),
        expect_escalation=False,
        expect_reason=None,
    )
    records = {
        "leave": {
            "case": "leave",
            "retrieved": ["a"],
            "context": ["a"],
            "answer": "До 14 календарных дней в год.",
            "escalated": False,
            "reason": "answered",
            "citations": 1,
            "accepted_citations": 1,
        }
    }

    graded = regrade((case,), records)

    assert graded[0].recall == 0.0
    assert graded[0].contains_expected is False


def test_regrade_refuses_an_artifact_without_answers() -> None:
    """Old artifacts recorded verdicts, not text: recomputing them would be a guess."""
    case = Case(
        id="leave",
        question="q",
        audience="all",
        expect_docs=(),
        expect_contains=("14 дней",),
        expect_escalation=False,
        expect_reason=None,
    )
    records = {"leave": {"case": "leave", "retrieved": [], "context": []}}

    with pytest.raises(RegradeError, match="no answer text"):
        regrade((case,), records)


def test_regrade_counts_a_case_that_the_golden_set_gained_as_an_error() -> None:
    case = Case(
        id="new",
        question="q",
        audience="all",
        expect_docs=(),
        expect_contains=(),
        expect_escalation=False,
        expect_reason=None,
    )

    report = summarise(regrade((case,), {}), generated=True)

    assert report.metrics["case_errors"] == 1.0
    assert "case_errors" in report.failures


def test_regrade_keeps_a_supported_citation_supported() -> None:
    case = Case(
        id="leave",
        question="q",
        audience="all",
        expect_docs=(),
        expect_contains=("14 дней",),
        expect_escalation=False,
        expect_reason=None,
    )
    record = {
        "case": "leave",
        "retrieved": ["a"],
        "context": ["a"],
        "answer": "14 дней.",
        "escalated": False,
        "reason": "answered",
        "citations": 2,
        "accepted_citations": 2,
    }

    assert regrade((case,), {"leave": record})[0].citation_supported is True


def test_merging_two_artifacts_keeps_both_halves(tmp_path: Path) -> None:
    """A run split in parts is one set: a case added later is scored by its own artifact."""
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    first.write_text('{"case": "a", "answer": "x"}\n', encoding="utf-8")
    second.write_text('{"case": "b", "answer": "y"}\n', encoding="utf-8")

    merged = merge_records((first, second))

    assert sorted(merged) == ["a", "b"]


def test_merging_refuses_to_choose_between_two_answers(tmp_path: Path) -> None:
    """Two artifacts that scored the same case are not a merge: one of them is the wrong run."""
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    first.write_text('{"case": "a", "answer": "x"}\n', encoding="utf-8")
    second.write_text('{"case": "a", "answer": "y"}\n', encoding="utf-8")

    with pytest.raises(RegradeError, match="scored twice"):
        merge_records((first, second))

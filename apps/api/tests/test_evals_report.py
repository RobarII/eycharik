"""The measurement file is the only thing a later reader sees.

It has to carry the honest metric names, the strata, and the artifact that makes the numbers
comparable. A report that hides the stratum or names a provider call "latency" is the bug.
"""

from __future__ import annotations

from datetime import date

from onboarding.evals.runner import (
    Baseline,
    Case,
    CaseResult,
    render_markdown,
    summarise,
)
from onboarding.evals.stats import paired_delta


def _case(case_id: str, *, stratum: str = "fact") -> Case:
    return Case(
        id=case_id,
        question="Сколько дней отпуска?",
        audience="all",
        expect_docs=("hr/leave-policy",),
        expect_contains=("28 календарных",),
        expect_escalation=False,
        expect_reason=None,
        stratum=stratum,
    )


def _report() -> object:
    result = CaseResult(
        case=_case("leave"),
        retrieved_docs=("hr/leave-policy",),
        recall=1.0,
        rr=1.0,
        context_docs=("hr/leave-policy",),
        answer="28 календарных дней",
        escalated=False,
        reason="answered",
        retrieved_citations=1,
        accepted_citations=1,
        completion_ms=900,
        answer_ms=1500,
        cost_completion_rub=0.05,
    )
    return summarise((result,), generated=True)


def test_the_report_names_the_completion_and_the_whole_answer_separately() -> None:
    markdown = render_markdown(
        _report(),
        command="cmd",
        commit="abc123",
        model="m",
        environment="local",
        embed_provider="e",
        note=None,
        on_date=date(2026, 10, 24),
    )

    assert "`p95_completion_ms`" in markdown
    assert "`p95_answer_ms`" in markdown
    assert "`cost_completion_rub`" in markdown
    assert "p95_latency_ms" not in markdown
    assert "cost_per_answer_rub" not in markdown


def test_the_report_carries_its_strata_and_artifact() -> None:
    markdown = render_markdown(
        _report(),
        command="cmd",
        commit="abc123",
        model="m",
        environment="local",
        embed_provider="e",
        note=None,
        on_date=date(2026, 10, 24),
        artifact="2026-10-24-eval-full.jsonl",
    )

    assert "## Strata" in markdown
    assert "| `fact` | 1 |" in markdown
    assert "artifact: `2026-10-24-eval-full.jsonl`" in markdown


def test_the_report_quotes_the_pinned_baseline_commit() -> None:
    report = summarise(
        (_report().results[0],),
        generated=True,
        baseline=Baseline(commit="deadbee", overall={"recall_at_5": 0.0}),
    )

    markdown = render_markdown(
        report,
        command="cmd",
        commit="abc123",
        model="m",
        environment="local",
        embed_provider="e",
        note="caveat travels",
        on_date=date(2026, 10, 24),
    )

    assert "baseline: `deadbee`" in markdown
    assert "note: caveat travels" in markdown


def test_a_comparison_is_rendered_with_its_interval() -> None:
    delta = paired_delta("recall", [(1.0, 1.0), (0.0, 1.0), (1.0, 1.0)])

    markdown = render_markdown(
        _report(),
        command="cmd",
        commit="abc123",
        model="m",
        environment="local",
        embed_provider="e",
        note=None,
        on_date=date(2026, 10, 24),
        comparison=(delta,),
    )

    assert "## Comparison against baseline" in markdown
    assert "p(delta <= 0)" in markdown

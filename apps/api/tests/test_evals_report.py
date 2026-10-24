"""The measurement file is the only thing a later reader sees.

It has to carry the honest metric names, the strata, and the artifact that makes the numbers
comparable. A report that hides the stratum or names a provider call "latency" is the bug.
"""

from __future__ import annotations

from datetime import date

from onboarding.app.settings import Settings
from onboarding.evals.__main__ import main, retrieval_label
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

    assert "## Страты" in markdown
    assert "| `fact` | 1 |" in markdown
    assert "- артефакт: `2026-10-24-eval-full.jsonl`" in markdown


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

    assert "- базовый прогон: `deadbee`" in markdown
    assert "- заметка: caveat travels" in markdown


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

    assert "## Сравнение с базовым прогоном" in markdown
    assert "p(дельта <= 0)" in markdown


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "_env_file": None,
        "embed_provider": "hashing",
        "embed_profile": "local-hashing",
        "embed_dim": 1024,
    }
    return Settings(**{**base, **overrides})  # type: ignore[arg-type]


def test_the_retrieval_label_names_the_switch_that_changed_the_run() -> None:
    """ADR 0012 and ADR 0016 are experiments; two arms must not share a header."""
    off = retrieval_label(_settings())
    on = retrieval_label(
        _settings(bm25_enabled=True, contextual_retrieval=True, contextual_prompt_version=2)
    )

    assert "bm25:off" in off
    assert "contextual:off" in off
    assert "bm25:on" in on
    assert "contextual:v2" in on
    assert off != on


def test_an_unknown_case_id_stops_the_run_before_the_database() -> None:
    """``--only`` is the iteration loop; a typo must not silently evaluate the whole set."""
    assert main(["--only", "no-such-case", "--retrieval-only"]) == 2

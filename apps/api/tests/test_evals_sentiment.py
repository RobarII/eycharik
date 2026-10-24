"""The sentiment eval is a measuring instrument; these tests keep the instrument honest."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from onboarding.core.models import RiskSignal, Sentiment, SignalTag
from onboarding.evals.sentiment import (
    Case,
    CaseResult,
    Report,
    SentimentSetError,
    _wilson,
    compare_reports,
    degraded_beyond,
    load_artifact,
    load_cases,
    render_artifact,
    render_markdown,
)

ROOT = Path(__file__).resolve().parents[3]
SET_PATH = ROOT / "docs" / "evals" / "sentiment.yaml"


def _write(tmp_path: Path, cases: list[dict[str, object]]) -> Path:
    path = tmp_path / "set.yaml"
    path.write_text(
        yaml.safe_dump({"version": 2, "cases": cases}, allow_unicode=True), encoding="utf-8"
    )
    return path


def _case(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "id": "a",
        "text": "Доступ не выдали",
        "sentiment": "negative",
        "tags": ["access"],
        "split": "dev",
    }
    body.update(overrides)
    return body


def _result(
    case_id: str,
    expected: Sentiment,
    predicted: Sentiment,
    *,
    escalate: bool = False,
    tags: tuple[SignalTag, ...] = (),
    predicted_tags: tuple[SignalTag, ...] = (),
    rep: int = 0,
) -> CaseResult:
    case = Case(
        id=case_id,
        text=case_id,
        sentiment=expected,
        tags=tags,
        split="test",
        expect_escalation=escalate,
    )
    signal = RiskSignal(
        source=case_id,
        sentiment=predicted,
        tags=predicted_tags,
        confidence=0.9,
        text=case_id,
    )
    return CaseResult(case=case, signal=signal, latency_ms=1.0, rep=rep)


def _report(*results: CaseResult, provider: str = "test") -> Report:
    return Report(
        provider=provider,
        split="test",
        repeat=1,
        results=results,
        fallbacks=0,
        format_errors=0,
    )


# --- the set is a contract ---------------------------------------------------


def test_the_set_is_large_enough_to_say_something() -> None:
    cases = load_cases(SET_PATH)

    assert len(cases) >= 100


def test_every_tag_appears_in_both_splits() -> None:
    cases = load_cases(SET_PATH)

    for split in ("dev", "test"):
        covered = {tag for case in cases if case.split == split for tag in case.tags}
        assert covered == set(SignalTag), f"{split} misses {set(SignalTag) - covered}"


def test_every_tone_appears_in_both_splits() -> None:
    cases = load_cases(SET_PATH)

    for split in ("dev", "test"):
        covered = {case.sentiment for case in cases if case.split == split}
        assert covered == set(Sentiment), f"{split} misses {set(Sentiment) - covered}"


def test_both_splits_keep_a_crisis_case() -> None:
    cases = load_cases(SET_PATH)

    for split in ("dev", "test"):
        assert any(case.expect_escalation for case in cases if case.split == split), split


def test_set_version_is_current() -> None:
    payload = yaml.safe_load(SET_PATH.read_text(encoding="utf-8"))

    assert payload["version"] == 2


def test_split_filter_returns_only_that_split(tmp_path: Path) -> None:
    path = _write(tmp_path, [_case(id="a"), _case(id="b", split="test", text="другое")])

    assert {case.id for case in load_cases(path, split="test")} == {"b"}
    assert len(load_cases(path, split="all")) == 2


# --- the loader refuses the shapes that would fake a number ------------------


def test_an_old_version_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "set.yaml"
    path.write_text(
        yaml.safe_dump({"version": 1, "cases": [_case()]}, allow_unicode=True), encoding="utf-8"
    )

    with pytest.raises(SentimentSetError, match="version"):
        load_cases(path)


def test_a_crisis_case_must_be_negative(tmp_path: Path) -> None:
    path = _write(tmp_path, [_case(sentiment="neutral", expect_escalation=True)])

    with pytest.raises(SentimentSetError, match="must be labelled negative"):
        load_cases(path)


def test_more_than_three_tags_is_refused(tmp_path: Path) -> None:
    path = _write(tmp_path, [_case(tags=["access", "it", "hr", "manager"])])

    with pytest.raises(SentimentSetError, match="at most 3 tags"):
        load_cases(path)


def test_duplicate_ids_and_texts_are_refused(tmp_path: Path) -> None:
    with pytest.raises(SentimentSetError, match="unique"):
        load_cases(_write(tmp_path, [_case(id="a"), _case(id="a", text="другое")]))
    with pytest.raises(SentimentSetError, match="duplicate case text"):
        load_cases(_write(tmp_path, [_case(id="a"), _case(id="b")]))


def test_unknown_split_is_refused(tmp_path: Path) -> None:
    with pytest.raises(SentimentSetError, match="split"):
        load_cases(_write(tmp_path, [_case(split="prod")]))


# --- metrics can be trusted --------------------------------------------------


def test_wilson_interval_contains_the_share_and_stays_inside_the_unit_range() -> None:
    interval = _wilson(0.9, 16)

    assert 0.0 <= interval.low < 0.9 < interval.high <= 1.0
    assert interval.high - interval.low > 0.1, "16 cases cannot pin a share tighter than that"

    edge = _wilson(0.0, 10)
    assert edge.low == 0.0
    assert 0.0 < edge.high < 0.5


def test_accuracy_is_scored_per_rep_and_macro_f1_ignores_class_imbalance() -> None:
    report = _report(
        _result("a", Sentiment.NEGATIVE, Sentiment.NEGATIVE),
        _result("b", Sentiment.NEGATIVE, Sentiment.NEGATIVE),
        _result("c", Sentiment.NEGATIVE, Sentiment.NEGATIVE),
        _result("d", Sentiment.POSITIVE, Sentiment.NEUTRAL),
    )

    assert report.sentiment_accuracy == 0.75
    assert report.per_class_recall[Sentiment.NEGATIVE] == 1.0
    assert report.per_class_recall[Sentiment.POSITIVE] == 0.0
    # macro F1 is the mean over classes present, so the rare class still costs a point
    assert report.macro_f1 < report.sentiment_accuracy


def test_confusion_matrix_counts_every_pair() -> None:
    report = _report(
        _result("a", Sentiment.NEGATIVE, Sentiment.NEGATIVE),
        _result("b", Sentiment.NEGATIVE, Sentiment.NEUTRAL),
    )

    assert report.confusion[(Sentiment.NEGATIVE, Sentiment.NEGATIVE)] == 1
    assert report.confusion[(Sentiment.NEGATIVE, Sentiment.NEUTRAL)] == 1


def test_a_missed_escalation_is_listed_and_lowers_recall() -> None:
    report = _report(
        _result("crisis-ok", Sentiment.NEGATIVE, Sentiment.NEGATIVE, escalate=True),
        _result("crisis-miss", Sentiment.NEGATIVE, Sentiment.NEUTRAL, escalate=True),
        _result("calm", Sentiment.POSITIVE, Sentiment.POSITIVE),
    )

    assert report.escalation_recall == 0.5
    assert [result.case.id for result in report.missed_escalations] == ["crisis-miss"]


def test_a_flaky_case_is_named_not_averaged_away() -> None:
    report = _report(
        _result("a", Sentiment.NEGATIVE, Sentiment.NEGATIVE, rep=0),
        _result("a", Sentiment.NEGATIVE, Sentiment.NEUTRAL, rep=1),
    )

    assert report.flaky_cases == ("a",)


def test_markdown_reports_an_interval_next_to_a_share() -> None:
    markdown = render_markdown(
        _report(_result("a", Sentiment.NEGATIVE, Sentiment.NEGATIVE)),
        command="cmd",
        note="",
    )

    assert "95% CI" in markdown
    assert re.search(r"\[\d\.\d\d, \d\.\d\d\]", markdown)
    assert "Матрица ошибок" in markdown


# --- comparison is paired, not two standalone numbers ------------------------


def test_paired_bootstrap_sees_a_real_improvement() -> None:
    baseline = _report(
        *(
            _result(
                f"c{index}",
                Sentiment.NEGATIVE,
                Sentiment.NEUTRAL if index < 8 else Sentiment.NEGATIVE,
            )
            for index in range(10)
        )
    )
    candidate = _report(
        *(_result(f"c{index}", Sentiment.NEGATIVE, Sentiment.NEGATIVE) for index in range(10))
    )

    comparison = compare_reports(baseline, candidate, rounds=500)

    assert comparison is not None
    assert comparison.delta == pytest.approx(0.8)
    assert comparison.interval.low > 0.0
    assert comparison.p_value <= 0.05


def test_paired_bootstrap_refuses_to_call_noise_a_win() -> None:
    baseline = _report(
        *(_result(f"c{index}", Sentiment.NEGATIVE, Sentiment.NEGATIVE) for index in range(20))
    )
    candidate = _report(
        *(
            _result(
                f"c{index}",
                Sentiment.NEGATIVE,
                Sentiment.NEUTRAL if index == 0 else Sentiment.NEGATIVE,
            )
            for index in range(20)
        )
    )

    comparison = compare_reports(baseline, candidate, rounds=500)

    assert comparison is not None
    assert comparison.interval.low <= 0.0 <= comparison.interval.high


def test_comparison_needs_a_shared_case() -> None:
    baseline = _report(_result("a", Sentiment.NEGATIVE, Sentiment.NEGATIVE))
    candidate = _report(_result("b", Sentiment.NEGATIVE, Sentiment.NEGATIVE))

    assert compare_reports(baseline, candidate) is None


def test_the_artifact_round_trips_and_can_be_compared(tmp_path: Path) -> None:
    report = _report(
        _result("a", Sentiment.NEGATIVE, Sentiment.NEGATIVE, tags=(SignalTag.ACCESS,)),
        _result("b", Sentiment.NEGATIVE, Sentiment.NEUTRAL, escalate=True),
    )
    path = tmp_path / "run.jsonl"
    path.write_text(render_artifact(report, command="cmd"), encoding="utf-8")

    restored = load_artifact(path)

    assert restored.provider == report.provider
    assert [result.signal.sentiment for result in restored.results] == [
        result.signal.sentiment for result in report.results
    ]
    assert restored.results[0].case.tags == (SignalTag.ACCESS,)
    assert restored.escalation_recall == report.escalation_recall
    assert compare_reports(restored, report) is not None


def test_a_broken_artifact_is_an_error_not_a_zero() -> None:
    with pytest.raises(SentimentSetError, match="missing artifact"):
        load_artifact(Path("/nonexistent/run.jsonl"))


def test_a_degraded_run_is_refused_instead_of_scored() -> None:
    healthy = _report(_result("a", Sentiment.NEGATIVE, Sentiment.NEGATIVE))
    degraded = Report(
        provider="prompt",
        split="test",
        repeat=1,
        results=(_result("a", Sentiment.NEGATIVE, Sentiment.NEUTRAL),),
        fallbacks=1,
        format_errors=0,
        fallback_reasons=(("unavailable", 1),),
    )
    malformed = Report(
        provider="prompt",
        split="test",
        repeat=1,
        results=(_result("a", Sentiment.NEGATIVE, Sentiment.NEGATIVE),),
        fallbacks=1,
        format_errors=0,
        fallback_reasons=(("format", 1),),
    )

    assert not degraded_beyond(healthy, 0.10)
    assert degraded_beyond(degraded, 0.10)
    assert not degraded_beyond(degraded, 1.0)
    # a malformed answer is a model result, not an outage: it must stay in the table
    assert not degraded_beyond(malformed, 0.10)

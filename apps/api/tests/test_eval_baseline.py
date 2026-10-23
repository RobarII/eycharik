"""A baseline is derived, not chosen, and a pinned baseline has to bite.

Two things can go wrong with gates and this file pins both: a baseline that is looser than the
observation it came from (a gate nobody can fail), and a stratum gate that never fires because the
report only checks the aggregate.
"""

from __future__ import annotations

from pathlib import Path

from onboarding.evals.runner import (
    STRATUM_MIN_CASES,
    Baseline,
    Case,
    CaseResult,
    baseline_json,
    derive_baseline,
    load_baseline,
    summarise,
)


def _case(
    case_id: str,
    *,
    stratum: str = "fact",
    docs: tuple[str, ...] = ("hr/leave-policy",),
) -> Case:
    return Case(
        id=case_id,
        question=f"q-{case_id}",
        audience="all",
        expect_docs=docs,
        expect_contains=(),
        expect_escalation=False,
        expect_reason=None,
        stratum=stratum,
    )


def _hits(case: Case) -> CaseResult:
    return CaseResult(case=case, retrieved_docs=case.expect_docs, recall=1.0, rr=1.0)


def _misses(case: Case) -> CaseResult:
    return CaseResult(case=case, retrieved_docs=(), recall=0.0, rr=0.0)


def _report(*results: CaseResult) -> object:
    return summarise(results, generated=False)


def test_a_derived_gate_is_the_wilson_lower_bound_of_the_run() -> None:
    report = _report(*[_hits(_case(f"c{index}")) for index in range(20)])

    baseline = derive_baseline(report, commit="abc123")

    assert baseline.commit == "abc123"
    assert baseline.overall["recall_at_5"] == 0.83


def test_a_derived_gate_never_exceeds_what_was_measured() -> None:
    report = _report(*[_hits(_case(f"c{index}")) for index in range(12)])

    baseline = derive_baseline(report, commit="abc123")

    assert baseline.overall["recall_at_5"] < report.metrics["recall_at_5"]


def test_a_thin_stratum_gets_no_gate_of_its_own() -> None:
    results = [_hits(_case(f"c{index}")) for index in range(4)]

    baseline = derive_baseline(_report(*results), commit="abc123")

    assert baseline.strata == {}


def test_a_thick_stratum_gets_a_gate_of_its_own() -> None:
    results = [
        _hits(_case(f"c{index}", stratum="fact")) for index in range(STRATUM_MIN_CASES)
    ]

    baseline = derive_baseline(_report(*results), commit="abc123")

    assert "fact" in baseline.strata
    assert baseline.strata["fact"]["recall_at_5"] < 1.0


def test_a_pinned_stratum_gate_fails_a_run_that_slips() -> None:
    fact_cases = [_case(f"c{index}", stratum="fact") for index in range(STRATUM_MIN_CASES)]
    baseline = Baseline(commit="abc123", strata={"fact": {"recall_at_5": 1.0}})
    results = (*tuple(_hits(case) for case in fact_cases[:-1]), _misses(fact_cases[-1]))

    report = summarise(results, generated=False, baseline=baseline)

    assert "fact.recall_at_5" in report.failures


def test_a_pinned_overall_gate_replaces_the_default() -> None:
    baseline = Baseline(commit="abc123", overall={"recall_at_5": 1.0})
    report = summarise(
        (_hits(_case("a")), _misses(_case("b"))), generated=False, baseline=baseline
    )

    assert "recall_at_5" in report.failures


def test_a_baseline_round_trips_through_its_file(tmp_path: Path) -> None:
    baseline = Baseline(
        commit="abc123",
        overall={"recall_at_5": 0.96},
        strata={"acl": {"leak_rate": 0.0}},
    )
    path = tmp_path / "baseline.json"

    path.write_text(baseline_json(baseline), encoding="utf-8")
    loaded = load_baseline(path)

    assert loaded == baseline


def test_a_missing_baseline_file_is_not_an_error(tmp_path: Path) -> None:
    assert load_baseline(tmp_path / "absent.json") is None

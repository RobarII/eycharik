from __future__ import annotations

from pathlib import Path

import pytest

from onboarding.app.knowledge.ingest import load_schema, read_document
from onboarding.evals.runner import Case, CaseResult, GoldenSetError, load_cases, summarise

ROOT = Path(__file__).resolve().parents[3]
ALLOWED_REASONS = {"no_sources", "low_confidence", "restricted", "out_of_scope", "unavailable"}


def test_every_escalation_case_names_a_known_reason() -> None:
    cases = load_cases(ROOT / "docs" / "evals" / "golden.yaml")

    for case in cases:
        if case.expect_escalation:
            assert case.expect_reason in ALLOWED_REASONS, case.id
        else:
            assert case.expect_reason is None, case.id


def test_the_golden_set_keeps_a_defensive_case() -> None:
    cases = load_cases(ROOT / "docs" / "evals" / "golden.yaml")

    assert "mentor-assignment" in {case.id for case in cases}


def _corpus_ids() -> set[str]:
    schema = load_schema(ROOT / "docs" / "contracts" / "doc.schema.json")
    return {
        str(read_document(path, schema).document.id)
        for path in (ROOT / "knowledge").rglob("*.md")
        if "_meta" not in path.parts
    }


def test_every_golden_document_exists() -> None:
    cases = load_cases(ROOT / "docs" / "evals" / "golden.yaml")
    known = _corpus_ids()
    named: set[str] = set()
    for case in cases:
        named.update(case.expect_docs)
        named.update(case.expect_absent_docs)

    assert named - known == set()


def test_every_document_has_a_case() -> None:
    cases = load_cases(ROOT / "docs" / "evals" / "golden.yaml")
    named: set[str] = set()
    for case in cases:
        named.update(case.expect_docs)
        named.update(case.expect_absent_docs)

    assert _corpus_ids() - named == set()


def test_a_leak_is_a_failure_not_a_recall_gap() -> None:
    case = Case(
        id="leaky",
        question="q",
        audience="all",
        expect_docs=("hr/leave-policy",),
        expect_absent_docs=("hr/salary-bands",),
        expect_contains=(),
        expect_escalation=False,
        expect_reason=None,
    )
    clean = CaseResult(
        case=case,
        retrieved_docs=("hr/leave-policy",),
        recall=1.0,
        rr=1.0,
    )
    leaked = CaseResult(
        case=case,
        retrieved_docs=("hr/salary-bands", "hr/leave-policy"),
        recall=1.0,
        rr=1.0,
        leaked_docs=("hr/salary-bands",),
    )

    assert summarise((clean,), generated=False).metrics["leak_rate"] == 0.0
    report = summarise((leaked,), generated=False)
    assert report.metrics["leak_rate"] == 1.0
    assert "leak_rate" in report.failures


def test_a_case_cannot_expect_and_forbid_the_same_document(tmp_path: Path) -> None:
    path = tmp_path / "golden.yaml"
    path.write_text(
        "cases:\n"
        "  - id: contradictory\n"
        '    question: "q"\n'
        "    expect_docs: [hr/leave-policy]\n"
        "    expect_absent_docs: [hr/leave-policy]\n",
        encoding="utf-8",
    )
    with pytest.raises(GoldenSetError):
        load_cases(path)

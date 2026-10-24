from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from onboarding.app.knowledge.ingest import load_schema, read_document
from onboarding.evals.runner import (
    STRATA,
    Case,
    CaseResult,
    GoldenSetError,
    case_record,
    compare_records,
    load_cases,
    load_jsonl,
    summarise,
    write_jsonl,
)

ROOT = Path(__file__).resolve().parents[3]
ALLOWED_REASONS = {"no_sources", "low_confidence", "restricted", "out_of_scope", "unavailable"}


def test_every_escalation_case_names_a_known_reason() -> None:
    cases = load_cases(ROOT / "docs" / "evals" / "golden.yaml")

    for case in cases:
        if case.expect_reason is not None:
            assert case.expect_reason in ALLOWED_REASONS, case.id
            assert case.expect_escalation, case.id
        assert case.stratum in STRATA, case.id


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


SCHEMA = ROOT / "docs" / "contracts" / "golden.schema.json"
GOLDEN = ROOT / "docs" / "evals" / "golden.yaml"

# A stratum that shrinks is a set that stopped testing something. These are ratchets: they may go
# up when a case is added, and adding a case is the only way down is allowed to happen.
MINIMUM_STRATUM_CASES = {
    "fact": 100,
    "acl": 10,
    "neardup": 3,
    "escalation": 3,
    "unanswerable": 3,
    "morphology": 6,
    "multihop": 6,
    "injection": 3,
}
# Bare digits and single tokens match a wrong answer (`3` matches `3 hours, 14 days`). The set
# carries a few of them from before the rule existed; this list may only shrink.
KNOWN_WEAK_FRAGMENTS = {("hotline-number", "4384")}


def _corpus_texts() -> dict[str, str]:
    schema = load_schema(ROOT / "docs" / "contracts" / "doc.schema.json")
    texts: dict[str, str] = {}
    for path in (ROOT / "knowledge").rglob("*.md"):
        if "_meta" in path.parts:
            continue
        document = read_document(path, schema)
        texts[str(document.document.id)] = path.read_text(encoding="utf-8")
    return texts


def test_the_golden_file_matches_its_schema() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    document = yaml.safe_load(GOLDEN.read_text(encoding="utf-8"))

    errors = sorted(Draft202012Validator(schema).iter_errors(document), key=str)

    assert errors == [], [f"{list(e.path)}: {e.message}" for e in errors]


def test_every_stratum_is_present_and_does_not_shrink() -> None:
    cases = load_cases(GOLDEN)
    counts: dict[str, int] = {}
    for case in cases:
        counts[case.stratum] = counts.get(case.stratum, 0) + 1

    for stratum, minimum in MINIMUM_STRATUM_CASES.items():
        assert counts.get(stratum, 0) >= minimum, (
            f"stratum {stratum} shrank to {counts.get(stratum, 0)}"
        )


def test_a_neardup_case_forbids_a_phrase_a_competing_document_states() -> None:
    """The trap has to be real: the wrong number must exist somewhere else in the corpus."""
    corpus = _corpus_texts()
    checked = 0
    for case in load_cases(GOLDEN):
        if case.stratum != "neardup":
            continue
        assert case.expect_not_contains, case.id
        for phrase in case.expect_not_contains:
            competitors = {
                doc_id
                for doc_id, text in corpus.items()
                if phrase in text and doc_id not in case.expect_docs
            }
            assert competitors, f"{case.id}: no competing document states {phrase!r}"
            checked += 1
    assert checked >= len(MINIMUM_STRATUM_CASES) - 4


def test_no_new_bare_digit_fragment_enters_the_set() -> None:
    weak = {
        (case.id, fragment)
        for case in load_cases(GOLDEN)
        for fragment in case.expect_contains
        if len(fragment.strip()) < 4 or re.fullmatch(r"[\d\s%.,]+", fragment)
    }

    assert weak == KNOWN_WEAK_FRAGMENTS


def test_an_unanswerable_case_names_no_document_and_must_refuse() -> None:
    for case in load_cases(GOLDEN):
        if case.stratum != "unanswerable":
            continue
        assert case.expect_docs == (), case.id
        assert case.expect_escalation, case.id


def test_a_morphology_case_still_names_its_document() -> None:
    for case in load_cases(GOLDEN):
        if case.stratum != "morphology":
            continue
        assert case.expect_docs, case.id


def test_an_artifact_round_trips_and_identical_runs_show_no_regression(tmp_path: Path) -> None:
    cases = load_cases(GOLDEN)
    case = cases[0]
    result = CaseResult(case=case, retrieved_docs=case.expect_docs, recall=1.0, rr=1.0)
    report = summarise((result,), generated=False)
    path = tmp_path / "run.jsonl"

    write_jsonl(report, path)
    records = load_jsonl(path)
    first = {case.id: case_record(result)}
    deltas = compare_records(first, records)

    assert set(records) == {case.id}
    assert all(delta.delta == 0.0 and not delta.regression for delta in deltas)

from __future__ import annotations

from pathlib import Path

from onboarding.evals.runner import load_cases

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

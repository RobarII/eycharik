from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from onboarding.api.admin import _summary
from onboarding.app.admin.queries import RunRecord
from onboarding.app.scenarios import ScenarioCatalog

ROOT = Path(__file__).resolve().parents[3]
SCENARIOS = ROOT / "apps" / "api" / "onboarding" / "scenarios"


def record(**overrides: object) -> RunRecord:
    values: dict[str, object] = {
        "run_id": "run-1",
        "employee_id": "1001",
        "name": "Анна Смирнова",
        "role": "Инженер-технолог",
        "department": "Производство",
        "scenario_id": "onboarding_default",
        "scenario_version": 1,
        "step_id": "meet_the_team",
        "entered_at": datetime(2026, 10, 23, 9, 0, tzinfo=UTC),
        "active": True,
    }
    values.update(overrides)
    return RunRecord(**values)  # type: ignore[arg-type]


def test_summary_carries_the_human_step_title() -> None:
    summary = _summary(record(), ScenarioCatalog.load(SCENARIOS))

    assert summary.step_id == "meet_the_team"
    assert summary.step_title == "Команда и наставник"
    assert (summary.step_number, summary.steps_total) == (3, 6)


def test_summary_tolerates_a_missing_scenario_version() -> None:
    summary = _summary(record(scenario_version=99), ScenarioCatalog.load(SCENARIOS))

    assert summary.step_title is None
    assert (summary.step_number, summary.steps_total) == (0, 0)

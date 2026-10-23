from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from onboarding.api.ratelimit import auth_failures
from onboarding.core.models import (
    ChunkId,
    EmployeeId,
    Event,
    EventKind,
    RunId,
    Scenario,
    StepState,
)
from onboarding.core.scenario import parse_scenario

NOW = datetime(2026, 10, 23, 9, 0, tzinfo=UTC)


def scenario_document() -> dict[str, Any]:
    return {
        "id": "onboarding_default",
        "version": 1,
        "title": "Онбординг по умолчанию",
        "start": "welcome",
        "steps": [
            {
                "id": "welcome",
                "kind": "send",
                "message": "Добро пожаловать в компанию.",
                "next": "checklist",
            },
            {
                "id": "checklist",
                "kind": "wait",
                "message": "Отметьте первый день.",
                "expects": "button",
                "keyboard": [[{"id": "done", "text": "Готово"}]],
                "routes": {"done": "documents"},
                "timeout": {"after_hours": 48, "action": "remind"},
            },
            {
                "id": "documents",
                "kind": "wait",
                "message": "Пришлите документы.",
                "expects": "message",
                "routes": {"default": "done"},
                "timeout": {"after_hours": 72, "action": "escalate"},
            },
            {"id": "done", "kind": "terminal", "outcome": "completed"},
        ],
    }


@pytest.fixture
def scenario() -> Scenario:
    return parse_scenario(scenario_document())


@pytest.fixture
def state(scenario: Scenario) -> StepState:
    return StepState(
        run_id=RunId("run-1"),
        employee_id=EmployeeId("employee-1"),
        scenario_id=scenario.id,
        scenario_version=scenario.version,
        step_id="checklist",
        entered_at=NOW,
    )


@pytest.fixture
def message_event() -> Event:
    return Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="Когда отпуск?")


@pytest.fixture
def chunk_id() -> ChunkId:
    return ChunkId("hr/leave-policy#0")


@pytest.fixture(autouse=True)
def _reset_auth_failures() -> Any:
    auth_failures.reset()
    yield
    auth_failures.reset()

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest

from onboarding.core.models import (
    ActionKind,
    CancelReminder,
    EscalationReason,
    Event,
    EventKind,
    Expects,
    KeepReminder,
    Outcome,
    RunId,
    Scenario,
    ScheduleReminder,
    StepState,
    TimeoutAction,
)
from onboarding.core.scenario import parse_scenario
from onboarding.core.transitions import (
    ScenarioRunError,
    StepCycleError,
    advance,
    start,
)

from .conftest import NOW, scenario_document


def test_start_emits_the_initial_send_chain(scenario: Scenario) -> None:
    transition = start(scenario, RunId("run-1"), "employee-1", NOW)

    assert [action.kind for action in transition.actions] == [ActionKind.SEND, ActionKind.SEND]
    assert transition.actions[0].text == "Добро пожаловать в компанию."
    assert transition.actions[1].text == "Отметьте первый день."
    assert transition.state.step_id == "checklist"
    assert transition.state.completed_steps == ("welcome",)
    reminder = transition.reminder
    assert isinstance(reminder, ScheduleReminder)
    assert reminder.due_at == NOW + timedelta(hours=48)
    assert reminder.action is TimeoutAction.REMIND


def test_button_moves_the_run_and_sends_the_next_step(
    scenario: Scenario, state: StepState
) -> None:
    event = Event(kind=EventKind.BUTTON_PRESSED, at=NOW, button_id="done")

    transition = advance(scenario, state, event)

    assert transition.state.step_id == "documents"
    assert transition.state.completed_steps == ("checklist",)
    assert [action.kind for action in transition.actions] == [ActionKind.SEND]
    assert isinstance(transition.reminder, ScheduleReminder)
    assert transition.reminder.due_at == NOW + timedelta(hours=72)


def test_unknown_button_keeps_the_run_in_place(scenario: Scenario, state: StepState) -> None:
    event = Event(kind=EventKind.BUTTON_PRESSED, at=NOW, button_id="ghost")

    transition = advance(scenario, state, event)

    assert transition.state == state
    assert [action.kind for action in transition.actions] == [ActionKind.IGNORE]
    assert isinstance(transition.reminder, KeepReminder)


def test_free_text_at_a_button_step_goes_to_the_assistant(
    scenario: Scenario, state: StepState, message_event: Event
) -> None:
    transition = advance(scenario, state, message_event)

    assert transition.state == state
    assert [action.kind for action in transition.actions] == [ActionKind.ANSWER]
    assert isinstance(transition.reminder, KeepReminder)


def test_free_text_completes_a_message_step(scenario: Scenario) -> None:
    state = StepState(
        run_id=RunId("run-1"),
        employee_id="employee-1",
        scenario_id=scenario.id,
        scenario_version=scenario.version,
        step_id="documents",
        entered_at=NOW,
        completed_steps=("welcome", "checklist"),
    )
    event = Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="Отправил")

    transition = advance(scenario, state, event)

    assert transition.state.step_id == "done"
    assert [action.kind for action in transition.actions] == [ActionKind.COMPLETE]
    assert transition.actions[0].outcome is Outcome.COMPLETED
    assert isinstance(transition.reminder, CancelReminder)


def test_timeout_reminds_once_and_cancels_the_timer(
    scenario: Scenario, state: StepState
) -> None:
    event = Event(kind=EventKind.TIMEOUT, at=NOW + timedelta(hours=48))

    transition = advance(scenario, state, event)

    assert transition.state == state
    assert [action.kind for action in transition.actions] == [ActionKind.SEND]
    assert transition.actions[0].note == "reminder"
    assert isinstance(transition.reminder, CancelReminder)


def test_timeout_escalates_without_moving_the_run(scenario: Scenario) -> None:
    state = StepState(
        run_id=RunId("run-1"),
        employee_id="employee-1",
        scenario_id=scenario.id,
        scenario_version=scenario.version,
        step_id="documents",
        entered_at=NOW,
    )
    event = Event(kind=EventKind.TIMEOUT, at=NOW + timedelta(hours=72))

    transition = advance(scenario, state, event)

    assert [action.kind for action in transition.actions] == [ActionKind.ESCALATE]
    assert transition.actions[0].reason is EscalationReason.TIMEOUT
    assert transition.state.step_id == "documents"
    assert isinstance(transition.reminder, CancelReminder)


def test_timeout_can_move_to_the_next_step() -> None:
    document = scenario_document()
    document["steps"][1]["timeout"] = {
        "after_hours": 10,
        "action": "escalate",
        "next": "done",
    }
    scenario = parse_scenario(document)
    state = StepState(
        run_id=RunId("run-1"),
        employee_id="employee-1",
        scenario_id=scenario.id,
        scenario_version=scenario.version,
        step_id="checklist",
        entered_at=NOW,
    )

    transition = advance(scenario, state, Event(kind=EventKind.TIMEOUT, at=NOW))

    assert [action.kind for action in transition.actions] == [
        ActionKind.ESCALATE,
        ActionKind.COMPLETE,
    ]
    assert transition.state.step_id == "done"
    assert isinstance(transition.reminder, CancelReminder)


def test_terminal_step_completes_idempotently(scenario: Scenario) -> None:
    state = StepState(
        run_id=RunId("run-1"),
        employee_id="employee-1",
        scenario_id=scenario.id,
        scenario_version=scenario.version,
        step_id="done",
        entered_at=NOW,
    )

    transition = advance(scenario, state, Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW))

    assert [action.kind for action in transition.actions] == [ActionKind.COMPLETE]
    assert transition.state == state


def test_state_from_another_version_is_refused(scenario: Scenario, state: StepState) -> None:
    other = replace(state, scenario_version=99)

    with pytest.raises(ScenarioRunError, match="belongs to"):
        advance(scenario, other, Event(kind=EventKind.TIMEOUT, at=NOW))


def test_send_step_cannot_be_advanced(scenario: Scenario, state: StepState) -> None:
    send_state = replace(state, step_id="welcome")

    with pytest.raises(ScenarioRunError, match="send step"):
        advance(scenario, send_state, Event(kind=EventKind.TIMEOUT, at=NOW))


def test_send_cycle_is_detected() -> None:
    document = {
        "id": "cycle",
        "version": 1,
        "title": "cycle",
        "start": "a",
        "steps": [
            {"id": "a", "kind": "send", "message": "a", "next": "b"},
            {"id": "b", "kind": "send", "message": "b", "next": "a"},
        ],
    }
    scenario = parse_scenario(document)

    with pytest.raises(StepCycleError):
        start(scenario, RunId("run-1"), "employee-1", NOW)


def test_file_step_routes_on_a_file_event() -> None:
    document = scenario_document()
    document["steps"][2] = {
        "id": "documents",
        "kind": "wait",
        "message": "Пришлите документы.",
        "expects": "file",
        "routes": {"default": "done"},
    }
    scenario = parse_scenario(document)
    state = StepState(
        run_id=RunId("run-1"),
        employee_id="employee-1",
        scenario_id=scenario.id,
        scenario_version=scenario.version,
        step_id="documents",
        entered_at=NOW,
    )

    transition = advance(scenario, state, Event(kind=EventKind.FILE_RECEIVED, at=NOW, file_id="f"))

    assert transition.state.step_id == "done"
    assert scenario.step("documents").expects is Expects.FILE
    assert isinstance(transition.reminder, CancelReminder)

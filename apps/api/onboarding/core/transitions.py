"""Scenario transitions: ``(state, event) -> decision``.

The caller owns persistence. This module owns the rules: which step follows a button, what a
timeout does, when the run ends, and when a free-text message goes to the assistant without moving
the run forward.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from .models import (
    Action,
    ActionKind,
    CancelReminder,
    EmployeeId,
    EscalationReason,
    Event,
    EventKind,
    Expects,
    KeepReminder,
    ReminderPlan,
    RunId,
    Scenario,
    ScheduleReminder,
    Step,
    StepKind,
    StepState,
    TimeoutAction,
    Transition,
)

MAX_SEND_CHAIN = 32


class ScenarioRunError(RuntimeError):
    """The persisted state cannot be advanced by this scenario."""


class StepCycleError(ScenarioRunError):
    """A chain of send steps did not reach a wait or terminal step."""


def start(
    scenario: Scenario,
    run_id: RunId,
    employee_id: EmployeeId,
    now: datetime,
) -> Transition:
    """Create the initial transition for a run and emit the first chain of messages."""
    state = StepState(
        run_id=run_id,
        employee_id=employee_id,
        scenario_id=scenario.id,
        scenario_version=scenario.version,
        step_id=scenario.start,
        entered_at=now,
    )
    return _enter(scenario, state, now)


def advance(scenario: Scenario, state: StepState, event: Event) -> Transition:
    """Apply one event to one run."""
    if state.scenario_id != scenario.id or state.scenario_version != scenario.version:
        raise ScenarioRunError(
            f"state belongs to {state.scenario_id!r} v{state.scenario_version}, "
            f"not {scenario.id!r} v{scenario.version}"
        )
    step = scenario.step(state.step_id)

    if step.kind is StepKind.SEND:
        raise ScenarioRunError(f"step {step.id!r} is a send step and is left by the engine")
    if step.kind is StepKind.TERMINAL:
        action = Action(kind=ActionKind.COMPLETE, outcome=step.outcome)
        return Transition(state=state, actions=(action,), reminder=CancelReminder())

    match event.kind:
        case EventKind.EMPLOYEE_CREATED:
            return _idle(state, ActionKind.IGNORE)
        case EventKind.TIMEOUT:
            return _on_timeout(scenario, state, event)
        case EventKind.BUTTON_PRESSED:
            return _on_button(scenario, state, event)
        case EventKind.MESSAGE_RECEIVED:
            return _on_message(scenario, state, event)
        case EventKind.FILE_RECEIVED:
            return _on_file(scenario, state, event)


def _enter(scenario: Scenario, state: StepState, now: datetime) -> Transition:
    actions: list[Action] = []
    completed = list(state.completed_steps)
    current = state

    for _ in range(MAX_SEND_CHAIN):
        step = scenario.step(current.step_id)
        if step.kind is StepKind.SEND:
            actions.append(Action(kind=ActionKind.SEND, text=step.message, keyboard=step.keyboard))
            completed.append(step.id)
            if step.next_step is None:
                raise ScenarioRunError(f"send step {step.id!r} has no next step")
            current = replace(current, step_id=step.next_step, entered_at=now)
            continue
        if step.kind is StepKind.WAIT:
            if step.message is not None:
                actions.append(
                    Action(kind=ActionKind.SEND, text=step.message, keyboard=step.keyboard)
                )
            reminder = _schedule(step, now)
            return Transition(
                state=replace(current, completed_steps=tuple(completed)),
                actions=tuple(actions),
                reminder=reminder,
            )
        actions.append(Action(kind=ActionKind.COMPLETE, outcome=step.outcome))
        completed.append(step.id)
        return Transition(
            state=replace(current, completed_steps=tuple(completed)),
            actions=tuple(actions),
            reminder=CancelReminder(),
        )

    raise StepCycleError(f"send chain from {state.step_id!r} exceeded {MAX_SEND_CHAIN} steps")


def _schedule(step: Step, now: datetime) -> ReminderPlan:
    if step.timeout is None:
        return KeepReminder()
    return ScheduleReminder(
        due_at=now + step.timeout.after,
        step_id=step.id,
        action=step.timeout.action,
    )


def _on_timeout(scenario: Scenario, state: StepState, event: Event) -> Transition:
    step = scenario.step(state.step_id)
    if step.timeout is None:
        return _idle(state, ActionKind.IGNORE)

    if step.timeout.action is TimeoutAction.REMIND:
        action = Action(
            kind=ActionKind.SEND,
            text=step.message,
            keyboard=step.keyboard,
            note="reminder",
        )
    else:
        action = Action(kind=ActionKind.ESCALATE, reason=EscalationReason.TIMEOUT, note=step.id)

    if step.timeout.next_step is None:
        return Transition(state=state, actions=(action,), reminder=CancelReminder())

    moved = _leave(scenario, state, step.timeout.next_step, event.at)
    return Transition(
        state=moved.state,
        actions=(action, *moved.actions),
        reminder=moved.reminder,
    )


def _on_button(scenario: Scenario, state: StepState, event: Event) -> Transition:
    step = scenario.step(state.step_id)
    if step.expects is not Expects.BUTTON:
        return _idle(state, ActionKind.IGNORE)
    target = step.routes.get(event.button_id or "") or step.routes.get("default")
    if target is None:
        return _idle(state, ActionKind.IGNORE)
    return _leave(scenario, state, target, event.at)


def _on_message(scenario: Scenario, state: StepState, event: Event) -> Transition:
    step = scenario.step(state.step_id)
    if step.expects is Expects.MESSAGE:
        target = step.routes.get("default")
        if target is not None:
            return _leave(scenario, state, target, event.at)
    return _idle(state, ActionKind.ANSWER)


def _on_file(scenario: Scenario, state: StepState, event: Event) -> Transition:
    step = scenario.step(state.step_id)
    if step.expects is Expects.FILE:
        target = step.routes.get("default")
        if target is not None:
            return _leave(scenario, state, target, event.at)
    return _idle(state, ActionKind.ANSWER)


def _leave(scenario: Scenario, state: StepState, target: str, at: datetime) -> Transition:
    stepped = replace(
        state,
        step_id=target,
        entered_at=at,
        completed_steps=(*state.completed_steps, state.step_id),
    )
    return _enter(scenario, stepped, at)


def _idle(state: StepState, kind: ActionKind) -> Transition:
    return Transition(state=state, actions=(Action(kind=kind),), reminder=KeepReminder())

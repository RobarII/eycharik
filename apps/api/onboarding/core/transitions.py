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
    Button,
    CancelReminder,
    EmployeeId,
    EscalationReason,
    Event,
    EventKind,
    Expects,
    KeepReminder,
    Keyboard,
    Question,
    QuestionKind,
    ReminderPlan,
    RunId,
    Scenario,
    ScheduleReminder,
    Step,
    StepKind,
    StepState,
    SurveyAnswer,
    TimeoutAction,
    Transition,
)
from .survey import needs_reason, parse_answer

MAX_SEND_CHAIN = 32
SURVEY_BUTTON_PREFIX = "q_"


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

    if step.kind is StepKind.SURVEY:
        return _on_survey(scenario, state, event, step)
    return _on_event(scenario, state, event)


def _on_event(scenario: Scenario, state: StepState, event: Event) -> Transition:
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
        if step.kind is StepKind.SURVEY:
            if step.message is not None:
                actions.append(Action(kind=ActionKind.SEND, text=step.message))
            actions.append(_ask(step.questions[0]))
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


def _ask(question: Question) -> Action:
    return Action(
        kind=ActionKind.SEND,
        text=question.prompt,
        keyboard=_question_keyboard(question),
        note=f"survey:{question.id}",
    )


def _question_keyboard(question: Question) -> Keyboard:
    if question.kind is not QuestionKind.CHOICE:
        return ()
    return (
        tuple(
            Button(id=f"{SURVEY_BUTTON_PREFIX}{question.id}_{option.id}", text=option.text)
            for option in question.options
        ),
    )


def _on_survey(scenario: Scenario, state: StepState, event: Event, step: Step) -> Transition:
    if event.kind is EventKind.TIMEOUT:
        return _on_survey_timeout(scenario, state, event, step)
    if event.kind not in {EventKind.MESSAGE_RECEIVED, EventKind.BUTTON_PRESSED}:
        return _idle(state, ActionKind.IGNORE)
    if state.pending_reason is not None:
        return _record_reason(scenario, state, event, step)
    return _record_answer(scenario, state, event, step)


def _record_reason(scenario: Scenario, state: StepState, event: Event, step: Step) -> Transition:
    question_id = state.pending_reason
    if question_id is None:
        raise ScenarioRunError("survey reason arrived without a pending question")
    reason = (event.text or "").strip()
    if not reason:
        return _ask_reason(state, step)
    answered = replace(
        state,
        answers=(*state.answers, SurveyAnswer(question_id=question_id, text=reason)),
        pending_reason=None,
    )
    return _continue_survey(scenario, answered, step, event)


def _record_answer(scenario: Scenario, state: StepState, event: Event, step: Step) -> Transition:
    question = step.questions[state.question_index]
    answer = _read_answer(question, event)
    if answer is None:
        return _repeat(state, step, question.id)
    answered = replace(state, answers=(*state.answers, answer))
    if needs_reason(question, answer) and question.reason_prompt is not None:
        return _ask_reason(replace(answered, pending_reason=question.id), step)
    return _continue_survey(scenario, answered, step, event)


def _ask_reason(state: StepState, step: Step) -> Transition:
    reason_prompt = step.questions[state.question_index].reason_prompt
    if reason_prompt is None:
        raise ScenarioRunError(f"survey step {step.id!r} asks for a reason without a prompt")
    return Transition(
        state=state,
        actions=(Action(kind=ActionKind.SEND, text=reason_prompt, note="survey:reason"),),
        reminder=KeepReminder(),
    )


def _continue_survey(
    scenario: Scenario, state: StepState, step: Step, event: Event
) -> Transition:
    next_index = state.question_index + 1
    if next_index >= len(step.questions):
        cleared = replace(state, question_index=0, pending_reason=None)
        if step.next_step is None:
            raise ScenarioRunError(f"survey step {step.id!r} has no next step")
        return _leave(scenario, cleared, step.next_step, event.at)
    advanced = replace(state, question_index=next_index, pending_reason=None)
    return Transition(
        state=advanced,
        actions=(_ask(step.questions[next_index]),),
        reminder=KeepReminder(),
    )


def _read_answer(question: Question, event: Event) -> SurveyAnswer | None:
    try:
        if question.kind is QuestionKind.CHOICE:
            option_id = _option_from_button(question, event.button_id)
            return parse_answer(question, option_id=option_id, text=event.text)
        return parse_answer(question, text=event.text)
    except ValueError:
        return None


def _option_from_button(question: Question, button_id: str | None) -> str | None:
    if not button_id:
        return None
    prefix = f"{SURVEY_BUTTON_PREFIX}{question.id}_"
    if not button_id.startswith(prefix):
        return None
    return button_id[len(prefix) :]


def _repeat(state: StepState, step: Step, question_id: str) -> Transition:
    question = next(item for item in step.questions if item.id == question_id)
    return Transition(
        state=state,
        actions=(
            Action(
                kind=ActionKind.SEND,
                text=question.prompt,
                keyboard=_question_keyboard(question),
                note="survey:repeat",
            ),
        ),
        reminder=KeepReminder(),
    )


def _on_survey_timeout(
    scenario: Scenario, state: StepState, event: Event, step: Step
) -> Transition:
    if step.timeout is None:
        return _idle(state, ActionKind.IGNORE)
    if step.timeout.action is TimeoutAction.ESCALATE:
        action = Action(kind=ActionKind.ESCALATE, reason=EscalationReason.TIMEOUT, note=step.id)
        if step.timeout.next_step is None:
            return Transition(state=state, actions=(action,), reminder=CancelReminder())
        moved = _leave(scenario, state, step.timeout.next_step, event.at)
        return Transition(
            state=moved.state, actions=(action, *moved.actions), reminder=moved.reminder
        )
    question_id = state.pending_reason or step.questions[state.question_index].id
    repeated = _repeat(replace(state, pending_reason=None), step, question_id)
    return Transition(
        state=repeated.state,
        actions=repeated.actions,
        reminder=ScheduleReminder(
            due_at=event.at + step.timeout.after, step_id=step.id, action=TimeoutAction.REMIND
        ),
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
    if step.expects is Expects.MESSAGE and not is_question(event.text):
        target = step.routes.get("default")
        if target is not None:
            return _leave(scenario, state, target, event.at)
    # A question is never a step acknowledgement. Otherwise asking "а как оформить отпуск?"
    # would silently advance the scenario and leave the newcomer without an answer.
    return _idle(state, ActionKind.ANSWER)


def is_question(text: str | None) -> bool:
    """Heuristic for free text: a question is answered, a confirmation advances the step."""
    if not text:
        return False
    normalized = " ".join(text.lower().replace("ё", "е").split())
    if "?" in normalized:
        return True
    for filler in ("а ", "ну ", "и "):
        if normalized.startswith(filler):
            normalized = normalized[len(filler) :].lstrip()
    starts = (
        "как ",
        "с какого ",
        "до какого ",
        "в каком ",
        "во сколько ",
        "на какой ",
        "в какой ",
        "где ",
        "когда ",
        "сколько ",
        "кто ",
        "что ",
        "почему ",
        "зачем ",
        "какой ",
        "какая ",
        "какие ",
        "каких ",
        "куда ",
        "откуда ",
        "чем ",
        "можно ли ",
        "есть ли ",
        "нужно ли ",
        "нужен ли ",
        "подскажите",
        "расскажите",
        "объясните",
    )
    return normalized.startswith(starts)


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

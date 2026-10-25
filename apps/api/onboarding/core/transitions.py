"""Scenario transitions: ``(state, event) -> decision``.

The caller owns persistence. This module owns the rules: which step follows a button, what a
timeout does, when the run ends, and when a free-text message goes to the assistant without moving
the run forward.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from .models import (
    MAX_SCALE,
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
    ScheduledEntry,
    ScheduleReminder,
    Step,
    StepKind,
    StepState,
    SurveyAnswer,
    TimeoutAction,
    Tone,
    Transition,
)
from .survey import needs_reason, parse_answer

MAX_SEND_CHAIN = 32
SURVEY_BUTTON_PREFIX = "q_"
SURVEY_SKIP_ID = "q_skip"


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


def replay(scenario: Scenario, state: StepState, now: datetime) -> Transition:
    """Re-emit the step a run is sitting on, without consuming an event.

    A person may come back to the same run from another linked messenger and press start there.
    Nothing about their progress changes; they simply need the question they are on to arrive
    where they are now.
    """
    return _enter(scenario, state, now)


def resume_scheduled(scenario: Scenario, state: StepState, now: datetime) -> Transition:
    """Emit a step whose delay has elapsed, then continue until the next wait or delay."""
    return _enter(scenario, state, now, force_step=state.step_id)


def jump(scenario: Scenario, state: StepState, target: str, now: datetime) -> Transition:
    """Move to ``target`` immediately; used by the demo-only ``/nextStage`` command.

    The current step is marked completed so the cabinet still tells the truth about what the run
    has passed. The target's own delay is ignored once, then normal delays apply again.
    """
    if target == state.step_id:
        return _enter(scenario, state, now, force_step=target)
    stepped = replace(
        state,
        step_id=target,
        entered_at=now,
        completed_steps=(*state.completed_steps, state.step_id),
    )
    return _enter(scenario, stepped, now, force_step=target)


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
        action = Action(kind=ActionKind.COMPLETE, outcome=step.outcome, image=step.image)
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


def _enter(
    scenario: Scenario,
    state: StepState,
    now: datetime,
    *,
    force_step: str | None = None,
) -> Transition:
    actions: list[Action] = []
    completed = list(state.completed_steps)
    current = state

    for _ in range(MAX_SEND_CHAIN):
        step = scenario.step(current.step_id)
        forced = step.id == force_step
        if forced:
            # The scheduler or /nextStage has already waited for this step; do not schedule it
            # again. The next step may still carry its own delay.
            force_step = None
            current = replace(current, entered_at=now)
        if step.delay is not None and not forced:
            return Transition(
                state=replace(current, completed_steps=tuple(completed)),
                actions=tuple(actions),
                reminder=KeepReminder(),
                scheduled=ScheduledEntry(step_id=step.id, due_at=now + step.delay),
            )
        if step.kind is StepKind.SEND:
            actions.append(
                Action(
                    kind=ActionKind.SEND,
                    text=_message(step, current.tone),
                    image=step.image,
                    keyboard=step.keyboard,
                )
            )
            completed.append(step.id)
            if step.next_step is None:
                raise ScenarioRunError(f"send step {step.id!r} has no next step")
            current = replace(current, step_id=step.next_step, entered_at=now)
            continue
        if step.kind is StepKind.WAIT:
            if step.message is not None:
                actions.append(
                    Action(
                        kind=ActionKind.SEND,
                        text=_message(step, current.tone),
                        image=step.image,
                        keyboard=step.keyboard,
                    )
                )
            reminder = _schedule(step, now)
            return Transition(
                state=replace(current, completed_steps=tuple(completed)),
                actions=tuple(actions),
                reminder=reminder,
            )
        if step.kind is StepKind.SURVEY:
            if step.message is not None:
                actions.append(
                    Action(
                        kind=ActionKind.SEND,
                        text=_message(step, current.tone),
                        image=step.image,
                    )
                )
            actions.append(_ask(step.questions[0], 1, len(step.questions)))
            reminder = _schedule(step, now)
            return Transition(
                state=replace(current, completed_steps=tuple(completed)),
                actions=tuple(actions),
                reminder=reminder,
            )
        actions.append(Action(kind=ActionKind.COMPLETE, outcome=step.outcome, image=step.image))
        completed.append(step.id)
        return Transition(
            state=replace(current, completed_steps=tuple(completed)),
            actions=tuple(actions),
            reminder=CancelReminder(),
        )

    raise StepCycleError(f"send chain from {state.step_id!r} exceeded {MAX_SEND_CHAIN} steps")


def _message(step: Step, tone: Tone) -> str | None:
    if tone is Tone.INFORMAL and step.informal_message is not None:
        return step.informal_message
    return step.message


def _schedule(step: Step, now: datetime) -> ReminderPlan:
    if step.timeout is None:
        return KeepReminder()
    return ScheduleReminder(
        due_at=now + step.timeout.after,
        step_id=step.id,
        action=step.timeout.action,
    )


def _ask(question: Question, index: int, total: int) -> Action:
    # The position rides on the note so the copy file keeps the wording: the core owns the order.
    return Action(
        kind=ActionKind.SEND,
        text=question.prompt,
        keyboard=_question_keyboard(question),
        note=f"survey:ask:{index}:{total}",
    )


def _question_keyboard(question: Question) -> Keyboard:
    if question.kind is QuestionKind.OPEN:
        # An open question always offers a way out: a person with nothing to add should not have
        # to invent text to move on.
        return ((Button(id=SURVEY_SKIP_ID, text="Пропустить"),),)
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
    if event.button_id == SURVEY_SKIP_ID:
        return _skip_question(scenario, state, step, event)
    answer = _read_answer(question, event)
    if answer is None:
        return _repeat(state, step, question.id)
    answered = replace(state, answers=(*state.answers, answer))
    if needs_reason(question, answer) and question.reason_prompt is not None:
        return _ask_reason(replace(answered, pending_reason=question.id), step)
    return _continue_survey(scenario, answered, step, event)


def _skip_question(
    scenario: Scenario, state: StepState, step: Step, event: Event
) -> Transition:
    """Skipping records nothing: a missing answer is more honest than a default one."""
    moved = _continue_survey(scenario, state, step, event)
    return Transition(
        state=moved.state,
        actions=(Action(kind=ActionKind.SEND, text="", note="survey:skipped"), *moved.actions),
        reminder=moved.reminder,
        scheduled=moved.scheduled,
    )


def _ack(question: Question, answer: SurveyAnswer) -> Action:
    """One short "recorded" message so nine ratings in a row do not feel like a void."""
    return Action(
        kind=ActionKind.SEND,
        text=_ack_value(question, answer),
        note="survey:ack",
    )


def _ack_value(question: Question, answer: SurveyAnswer) -> str:
    if answer.score is not None:
        # "8 из 10" tells the person what the number means without reading the question again.
        return f"{answer.score} из {MAX_SCALE}"
    if answer.option_id is not None:
        for option in question.options:
            if option.id == answer.option_id:
                return option.text
    return ""


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
    scenario: Scenario,
    state: StepState,
    step: Step,
    event: Event,
    *,
    acknowledge: bool = True,
) -> Transition:
    next_index = state.question_index + 1
    if next_index >= len(step.questions):
        cleared = replace(state, question_index=0, pending_reason=None)
        if step.next_step is None:
            raise ScenarioRunError(f"survey step {step.id!r} has no next step")
        return _leave(scenario, cleared, step.next_step, event.at)
    advanced = replace(state, question_index=next_index, pending_reason=None)
    following = _ask(step.questions[next_index], next_index + 1, len(step.questions))
    # A skipped question has nothing of its own to acknowledge; acknowledging the previous answer
    # again would read as a duplicate (live 2026-10-25).
    acked: tuple[Action, ...] = ()
    if acknowledge and state.answers:
        acked = (_ack(step.questions[next_index - 1], state.answers[-1]),)
    return Transition(
        state=advanced,
        actions=(*acked, following),
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
                note=f"survey:repeat:{question.kind.value}",
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
        # A reminder is a nudge, not a rerun of the whole step: the person already has that text
        # above in the chat. One short line names the step and gives the way out.
        # "Напишите «готово»" only holds where text is an answer; a button step needs a button.
        note = "reminder_soft" if step.expects is Expects.MESSAGE else "reminder_soft_button"
        action = Action(
            kind=ActionKind.SEND,
            text=step.title or step.id,
            keyboard=step.keyboard,
            note=note,
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
    # A step that waits for a message accepts a button too: "готово" as a button is the same
    # acknowledgement as the word, and it is easier than guessing the word at the right moment.
    if step.expects not in {Expects.BUTTON, Expects.MESSAGE}:
        return _idle(state, ActionKind.IGNORE)
    if step.expects is Expects.MESSAGE:
        # Only a declared button counts here: an unknown id must not borrow the default route and
        # skip the stage.
        declared = {button.id for row in step.keyboard for button in row}
        if event.button_id not in declared:
            return _idle(state, ActionKind.IGNORE)
        target = step.routes.get(event.button_id or "")
    else:
        target = step.routes.get(event.button_id or "") or step.routes.get("default")
    if target is None:
        return _idle(state, ActionKind.IGNORE)
    chosen = step.tone_routes.get(event.button_id or "")
    moved = replace(state, tone=chosen) if chosen is not None else state
    return _leave(scenario, moved, target, event.at)


def _on_message(scenario: Scenario, state: StepState, event: Event) -> Transition:
    step = scenario.step(state.step_id)
    if step.expects is Expects.MESSAGE and is_confirmation(event.text):
        target = step.routes.get("default")
        if target is not None:
            return _leave(scenario, state, target, event.at)
    if step.expects is Expects.BUTTON and is_confirmation(event.text):
        # Live 2026-10-25: "готово" at the tone question went to the knowledge base and came back
        # as "не нашёл ответа". A confirmation is not a question here; point at the buttons.
        return Transition(
            state=state,
            actions=(Action(kind=ActionKind.SEND, text="", note="step:button_hint"),),
            reminder=KeepReminder(),
        )
    # Free text is not a button. A problem report or a question must reach the assistant, not be
    # mistaken for "готово" and skip the next month of the timeline.
    return _idle(state, ActionKind.ANSWER)


_STAGE_QUESTIONS = (
    "что дальше",
    "что теперь",
    "что мне делать",
    "что делать",
    "что мне сейчас",
    "что сейчас нужно",
    "что нужно сделать",
    "какой сейчас этап",
    "какой этап",
    "на каком я этапе",
    "на каком этапе",
    "что по плану",
    "что следующее",
    "следующий шаг",
    "текущий шаг",
    "текущий этап",
    "мой шаг",
    "где я сейчас",
)


def asks_about_stage(text: str | None) -> bool:
    """True when the person asks about their own onboarding step, not about the company.

    The run already knows the step and its message; sending "я не нашёл ответа, передал HR" to
    "что мне сейчас нужно сделать?" is a lie (measured live 2026-10-24).
    """
    if not text:
        return False
    normalized = " ".join(text.lower().replace("ё", "е").split())
    return any(phrase in normalized for phrase in _STAGE_QUESTIONS)


def has_words(text: str | None) -> bool:
    """True when a message carries letters or digits, so an emoji is not a question for HR."""
    if not text:
        return False
    return any(character.isalnum() for character in text)


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


_CONFIRMATIONS = (
    "готово",
    "готов",
    "отправил",
    "отправила",
    "отдал",
    "отдала",
    "передал",
    "передала",
    "сделал",
    "сделала",
    "понятно",
    "понял",
    "поняла",
    "продолжить",
    "продолжай",
    "да",
    "ок",
    "ok",
)
_NEGATIVE_CONFIRMATIONS = ("не готов", "не отдал", "не отправил", "не передал", "пока нет")


def is_confirmation(text: str | None) -> bool:
    """True only for an explicit acknowledgement, never for an arbitrary message.

    The old rule treated every non-question as a confirmation. That is how "не включается
    компьютер" moved a run from access help through the whole first day and into the two-week
    survey. The list is intentionally conservative; a problem report goes to the answerer instead.
    """
    if not text:
        return False
    normalized = " ".join(text.lower().replace("ё", "е").split())
    if any(phrase in normalized for phrase in _NEGATIVE_CONFIRMATIONS):
        return False
    return any(word in normalized.split() for word in _CONFIRMATIONS)


def _on_file(scenario: Scenario, state: StepState, event: Event) -> Transition:
    step = scenario.step(state.step_id)
    # A file is an acknowledgement where the scenario waits for a file, and also where it waits for
    # a message: the documents step says "send them here", so a photo with no caption must move it.
    # A captioned question is still a question, not a receipt.
    if step.expects is Expects.MESSAGE and is_question(event.text):
        return _idle(state, ActionKind.ANSWER)
    if step.expects is Expects.FILE or step.expects is Expects.MESSAGE:
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

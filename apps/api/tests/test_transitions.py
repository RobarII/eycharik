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
    ScheduledEntry,
    ScheduleReminder,
    StepState,
    SurveyAnswer,
    Timeout,
    TimeoutAction,
    Tone,
)
from onboarding.core.scenario import parse_scenario
from onboarding.core.transitions import (
    ScenarioRunError,
    StepCycleError,
    _record_reason,
    advance,
    asks_about_stage,
    has_words,
    is_confirmation,
    is_question,
    jump,
    replay,
    resume_scheduled,
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


def test_images_follow_their_step_actions() -> None:
    document = scenario_document()
    document["steps"][0]["image"] = "welcome.jpg"
    document["steps"][1]["image"] = "reminder.jpg"
    document["steps"][3]["image"] = "goodbye.jpg"
    scenario = parse_scenario(document)

    started = start(scenario, RunId("run-1"), "employee-1", NOW)
    reminder = advance(
        scenario,
        started.state,
        Event(kind=EventKind.TIMEOUT, at=NOW + timedelta(hours=48)),
    )
    completed = advance(
        scenario,
        replace(started.state, step_id="documents"),
        Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="Отправил"),
    )

    assert [action.image for action in started.actions] == ["welcome.jpg", "reminder.jpg"]
    assert reminder.actions[0].image == "reminder.jpg"
    assert completed.actions[0].image == "goodbye.jpg"


def test_button_moves_the_run_and_sends_the_next_step(scenario: Scenario, state: StepState) -> None:
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


def test_timeout_reminds_once_and_cancels_the_timer(scenario: Scenario, state: StepState) -> None:
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


def test_delayed_step_is_selected_but_not_sent_until_due() -> None:
    document = scenario_document()
    document["steps"][1]["delay_hours"] = 24
    scenario = parse_scenario(document)

    started = start(scenario, RunId("run-1"), "employee-1", NOW)

    assert [action.text for action in started.actions] == ["Добро пожаловать в компанию."]
    assert started.state.step_id == "checklist"
    assert started.scheduled == ScheduledEntry(
        step_id="checklist", due_at=NOW + timedelta(hours=24)
    )

    due = resume_scheduled(scenario, started.state, started.scheduled.due_at)

    assert [action.text for action in due.actions] == ["Отметьте первый день."]
    assert due.state.step_id == "checklist"
    assert due.scheduled is None
    assert isinstance(due.reminder, ScheduleReminder)


def test_problem_text_is_not_a_step_confirmation() -> None:
    document = scenario_document()
    scenario = parse_scenario(document)
    state = StepState(
        run_id=RunId("run-1"),
        employee_id="employee-1",
        scenario_id=scenario.id,
        scenario_version=scenario.version,
        step_id="documents",
        entered_at=NOW,
    )

    transition = advance(
        scenario,
        state,
        Event(
            kind=EventKind.MESSAGE_RECEIVED,
            at=NOW,
            text="Не включается компьютер",
        ),
    )

    assert transition.state == state
    assert [action.kind for action in transition.actions] == [ActionKind.ANSWER]
    assert is_confirmation("готово")
    assert is_confirmation("Я всё уже отдал")
    assert not is_confirmation("Не включается компьютер")


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


def test_a_file_acknowledges_a_message_step(scenario: Scenario, state: StepState) -> None:
    # The documents step says "send them here" and waits for a message: a photo with no caption is
    # that message, not a question the assistant has to answer.
    documents = replace(state, step_id="documents")

    transition = advance(
        scenario, documents, Event(kind=EventKind.FILE_RECEIVED, at=NOW, file_id="f")
    )

    assert transition.state.step_id == "done"


def test_a_captioned_question_at_a_message_step_is_answered(
    scenario: Scenario, state: StepState
) -> None:
    documents = replace(state, step_id="documents")

    transition = advance(
        scenario,
        documents,
        Event(kind=EventKind.FILE_RECEIVED, at=NOW, file_id="f", text="А как оформить отпуск?"),
    )

    assert transition.state.step_id == "documents"
    assert transition.actions[0].kind is ActionKind.ANSWER


def test_a_question_at_a_message_step_is_answered_not_acknowledged(
    scenario: Scenario, state: StepState
) -> None:
    documents = replace(state, step_id="documents")

    transition = advance(
        scenario,
        documents,
        Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="А как оформить отпуск?"),
    )

    assert transition.state == documents
    assert [action.kind for action in transition.actions] == [ActionKind.ANSWER]


def test_a_confirmation_at_a_message_step_advances_it(scenario: Scenario, state: StepState) -> None:
    documents = replace(state, step_id="documents")

    transition = advance(
        scenario,
        documents,
        Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="Отправил документы"),
    )

    assert transition.state.step_id == "done"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Сколько дней отпуска?", True),
        ("Как получить ноутбук", True),
        ("подскажите про ДМС", True),
        ("а сколько дней отпуска", True),
        ("ну как получить доступ", True),
        ("Отправил документы", False),
        ("готово", False),
        ("", False),
        (None, False),
    ],
)
def test_is_question(text: str | None, expected: bool) -> None:
    assert is_question(text) is expected


SURVEY_DOCUMENT = {
    "id": "survey_demo",
    "version": 1,
    "title": "Опрос",
    "start": "intro",
    "segments": ["GrPP"],
    "steps": [
        {"id": "intro", "kind": "send", "message": "Привет", "next": "check"},
        {
            "id": "check",
            "kind": "survey",
            "title": "Чек через две недели",
            "message": "Пара вопросов",
            "questions": [
                {
                    "id": "manager_available",
                    "kind": "scale",
                    "prompt": "Насколько доступен руководитель?",
                    "low_threshold": 8,
                    "reason_prompt": "Что мешает?",
                },
                {
                    "id": "colleagues",
                    "kind": "choice",
                    "prompt": "Как встретили коллеги?",
                    "options": [
                        {"id": "great", "text": "Отлично"},
                        {"id": "bad", "text": "Никак"},
                    ],
                },
                {"id": "advice", "kind": "open", "prompt": "Что улучшить?"},
            ],
            "next": "done",
            "escalate_to": "recruiter",
            "timeout": {"after_hours": 24, "action": "remind"},
        },
        {"id": "done", "kind": "terminal", "outcome": "completed"},
    ],
}


@pytest.fixture
def survey() -> Scenario:
    return parse_scenario(SURVEY_DOCUMENT)


def _survey_state() -> StepState:
    return StepState(
        run_id=RunId("run-2"),
        employee_id="employee-2",
        scenario_id="survey_demo",
        scenario_version=1,
        step_id="check",
        entered_at=NOW,
    )


def test_survey_enter_asks_the_first_question(survey: Scenario) -> None:
    transition = start(survey, RunId("run-2"), "employee-2", NOW)

    assert [action.kind for action in transition.actions] == [
        ActionKind.SEND,
        ActionKind.SEND,
        ActionKind.SEND,
    ]
    assert transition.actions[0].text == "Привет"
    assert transition.actions[1].text == "Пара вопросов"
    assert transition.actions[2].text == "Насколько доступен руководитель?"
    assert transition.state.step_id == "check"
    assert isinstance(transition.reminder, ScheduleReminder)


def test_low_score_asks_a_reason_before_moving_on(survey: Scenario) -> None:
    answered = advance(
        survey, _survey_state(), Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="6")
    )

    assert answered.state.step_id == "check"
    assert answered.state.question_index == 0
    assert answered.state.pending_reason == "manager_available"
    assert [action.text for action in answered.actions] == ["Что мешает?"]
    assert answered.state.answers == (SurveyAnswer(question_id="manager_available", score=6),)


def test_reason_is_stored_and_the_next_question_is_asked(survey: Scenario) -> None:
    state = replace(
        _survey_state(),
        answers=(SurveyAnswer(question_id="manager_available", score=6),),
        pending_reason="manager_available",
    )

    transition = advance(
        survey,
        state,
        Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="Руководитель в командировке"),
    )

    assert transition.state.question_index == 1
    assert transition.state.pending_reason is None
    assert transition.state.answers[-1] == SurveyAnswer(
        question_id="manager_available", text="Руководитель в командировке"
    )
    assert transition.actions[0].text == "Как встретили коллеги?"
    assert len(transition.actions[0].keyboard[0]) == 2


def test_comfortable_score_moves_to_the_next_question(survey: Scenario) -> None:
    transition = advance(
        survey, _survey_state(), Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="9")
    )

    assert transition.state.question_index == 1
    assert transition.state.pending_reason is None
    assert transition.actions[0].note == "survey:colleagues"


def test_choice_is_read_from_the_button_id(survey: Scenario) -> None:
    state = replace(_survey_state(), question_index=1)

    transition = advance(
        survey, state, Event(kind=EventKind.BUTTON_PRESSED, at=NOW, button_id="q_colleagues_bad")
    )

    assert transition.state.question_index == 2
    assert transition.state.answers == (SurveyAnswer(question_id="colleagues", option_id="bad"),)


def test_invalid_answer_repeats_the_question_without_progress(survey: Scenario) -> None:
    transition = advance(
        survey, _survey_state(), Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="много")
    )

    assert transition.state == _survey_state()
    assert transition.actions[0].note == "survey:repeat:scale"
    assert transition.actions[0].text == "Насколько доступен руководитель?"


def test_last_answer_leaves_the_survey(survey: Scenario) -> None:
    state = replace(_survey_state(), question_index=2)

    transition = advance(
        survey, state, Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="Больше ясности")
    )

    assert transition.state.step_id == "done"
    assert transition.state.completed_steps == ("check", "done")
    assert transition.state.answers[-1].text == "Больше ясности"
    assert [action.kind for action in transition.actions] == [ActionKind.COMPLETE]


def test_survey_timeout_repeats_the_current_question(survey: Scenario) -> None:
    transition = advance(
        survey, _survey_state(), Event(kind=EventKind.TIMEOUT, at=NOW + timedelta(hours=24))
    )

    assert transition.state.question_index == 0
    assert transition.actions[0].text == "Насколько доступен руководитель?"
    assert isinstance(transition.reminder, ScheduleReminder)
    assert transition.reminder.due_at == NOW + timedelta(hours=48)


def test_jump_to_same_step_reenters(scenario: Scenario, state: StepState) -> None:
    transition = jump(scenario, state, state.step_id, NOW)
    assert transition.state.step_id == state.step_id


def test_jump_to_different_step_advances(scenario: Scenario, state: StepState) -> None:
    transition = jump(scenario, state, "documents", NOW)
    assert transition.state.step_id == "documents"
    assert "checklist" in transition.state.completed_steps


def test_replay_returns_current_step(scenario: Scenario, state: StepState) -> None:
    transition = replay(scenario, state, NOW)
    assert transition.state.step_id == state.step_id


def test_button_pressed_on_non_button_step_is_ignored(scenario: Scenario, state: StepState) -> None:
    # documents step expects MESSAGE
    doc_state = replace(state, step_id="documents")
    transition = advance(
        scenario, doc_state, Event(kind=EventKind.BUTTON_PRESSED, at=NOW, button_id="b1")
    )
    assert [a.kind for a in transition.actions] == [ActionKind.IGNORE]


def test_choice_question_with_invalid_or_missing_button(survey: Scenario) -> None:
    state = replace(_survey_state(), question_index=1)
    t1 = advance(survey, state, Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="unknown"))
    assert t1.actions[0].note == "survey:repeat:choice"
    t2 = advance(
        survey, state, Event(kind=EventKind.BUTTON_PRESSED, at=NOW, button_id="wrong_prefix")
    )
    assert t2.actions[0].note == "survey:repeat:choice"


def test_informal_message_selected_when_tone_is_informal(
    scenario: Scenario, state: StepState
) -> None:
    informal_step = replace(scenario.step("welcome"), informal_message="Привет!")
    informal_scenario = replace(scenario, steps={**scenario.steps, "welcome": informal_step})
    transition = jump(informal_scenario, replace(state, tone=Tone.INFORMAL), "welcome", NOW)
    assert transition.actions[0].text == "Привет!"


def test_employee_created_event_is_ignored(scenario: Scenario, state: StepState) -> None:
    transition = advance(scenario, state, Event(kind=EventKind.EMPLOYEE_CREATED, at=NOW))
    assert transition.state == state
    assert [a.kind for a in transition.actions] == [ActionKind.IGNORE]


def test_send_step_without_next_step_raises(scenario: Scenario) -> None:
    bad_step = replace(scenario.step("welcome"), next_step=None)
    bad_scenario = replace(scenario, steps={**scenario.steps, "welcome": bad_step})
    with pytest.raises(ScenarioRunError, match="has no next step"):
        start(bad_scenario, RunId("run-1"), "employee-1", NOW)


def test_step_without_timeout_keeps_reminder(scenario: Scenario, state: StepState) -> None:
    step_no_timeout = replace(scenario.step("checklist"), timeout=None)
    scenario_no_timeout = replace(
        scenario, steps={**scenario.steps, "checklist": step_no_timeout}
    )
    transition = jump(scenario_no_timeout, state, "checklist", NOW)
    assert isinstance(transition.reminder, KeepReminder)


def test_survey_ignores_file_event(survey: Scenario) -> None:
    transition = advance(
        survey, _survey_state(), Event(kind=EventKind.FILE_RECEIVED, at=NOW)
    )
    assert [a.kind for a in transition.actions] == [ActionKind.IGNORE]


def test_empty_reason_repeats_reason_prompt(survey: Scenario) -> None:
    reason_state = replace(_survey_state(), pending_reason="manager")
    transition = advance(
        survey, reason_state, Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="   ")
    )
    assert [a.kind for a in transition.actions] == [ActionKind.SEND]
    assert transition.actions[0].note == "survey:reason"


def test_record_reason_without_pending_reason_raises(survey: Scenario) -> None:
    with pytest.raises(ScenarioRunError, match="without a pending question"):
        _record_reason(
            survey,
            replace(_survey_state(), pending_reason=None),
            Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="x"),
            survey.step("check"),
        )


def test_reason_without_prompt_raises(survey: Scenario) -> None:
    step = survey.step("check")
    bad_q = replace(step.questions[0], reason_prompt=None)
    bad_step = replace(step, questions=(bad_q, *step.questions[1:]))
    bad_survey = replace(survey, steps={**survey.steps, "check": bad_step})
    reason_state = replace(_survey_state(), pending_reason="manager")
    with pytest.raises(ScenarioRunError, match="asks for a reason without a prompt"):
        advance(bad_survey, reason_state, Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text=""))


def test_survey_without_next_step_raises(survey: Scenario) -> None:
    bad_step = replace(survey.step("check"), next_step=None)
    bad_survey = replace(survey, steps={**survey.steps, "check": bad_step})
    state = replace(_survey_state(), question_index=2)
    with pytest.raises(ScenarioRunError, match="has no next step"):
        advance(bad_survey, state, Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="answer"))


def test_survey_without_timeout_ignores_timeout(survey: Scenario) -> None:
    bad_step = replace(survey.step("check"), timeout=None)
    bad_survey = replace(survey, steps={**survey.steps, "check": bad_step})
    transition = advance(
        bad_survey, _survey_state(), Event(kind=EventKind.TIMEOUT, at=NOW)
    )
    assert [a.kind for a in transition.actions] == [ActionKind.IGNORE]


def test_survey_timeout_escalate_without_next_step(survey: Scenario) -> None:
    timeout = Timeout(after=timedelta(hours=1), action=TimeoutAction.ESCALATE, next_step=None)
    bad_step = replace(survey.step("check"), timeout=timeout)
    bad_survey = replace(survey, steps={**survey.steps, "check": bad_step})
    transition = advance(
        bad_survey, _survey_state(), Event(kind=EventKind.TIMEOUT, at=NOW)
    )
    assert [a.kind for a in transition.actions] == [ActionKind.ESCALATE]
    assert isinstance(transition.reminder, CancelReminder)


def test_survey_timeout_escalate_with_next_step(survey: Scenario) -> None:
    timeout = Timeout(after=timedelta(hours=1), action=TimeoutAction.ESCALATE, next_step="done")
    bad_step = replace(survey.step("check"), timeout=timeout)
    bad_survey = replace(survey, steps={**survey.steps, "check": bad_step})
    transition = advance(
        bad_survey, _survey_state(), Event(kind=EventKind.TIMEOUT, at=NOW)
    )
    assert [a.kind for a in transition.actions] == [ActionKind.ESCALATE, ActionKind.COMPLETE]
    assert transition.state.step_id == "done"


def test_timeout_on_step_without_timeout_ignores(scenario: Scenario, state: StepState) -> None:
    bad_step = replace(scenario.step("checklist"), timeout=None)
    bad_scenario = replace(scenario, steps={**scenario.steps, "checklist": bad_step})
    transition = advance(bad_scenario, state, Event(kind=EventKind.TIMEOUT, at=NOW))
    assert [a.kind for a in transition.actions] == [ActionKind.IGNORE]


def test_is_confirmation_edge_cases() -> None:
    assert not is_confirmation(None)
    assert not is_confirmation("")
    assert not is_confirmation("   ")
    assert not is_confirmation("пока нет")
    assert not is_confirmation("не готов")
    assert is_confirmation("Да, готов")


def test_file_at_button_step_answers(scenario: Scenario, state: StepState) -> None:
    transition = advance(scenario, state, Event(kind=EventKind.FILE_RECEIVED, at=NOW))
    assert [a.kind for a in transition.actions] == [ActionKind.ANSWER]


def test_asks_about_stage() -> None:
    assert not asks_about_stage(None)
    assert not asks_about_stage("")
    assert not asks_about_stage("как оформить отпуск")
    assert asks_about_stage("Что дальше?")
    assert asks_about_stage("какой сейчас этап")


def test_has_words() -> None:
    assert not has_words(None)
    assert not has_words("")
    assert not has_words("👍😊")
    assert has_words("hello")
    assert has_words("123")



from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from onboarding.app.audit import NullAudit
from onboarding.app.copy import load_copy
from onboarding.app.worker.actions import ActionContext, ActionExecutor
from onboarding.app.worker.answerer import AnswerOutcome
from onboarding.core.models import (
    Action,
    ActionKind,
    Button,
    EscalationReason,
    Outcome,
)

from .fakes import ADDRESS, EMPLOYEE, RecordingAudit, RecordingMessaging, profile

ROOT = Path(__file__).resolve().parents[3]
COPY = load_copy(ROOT / "docs" / "product" / "copy.yaml")


@dataclass
class StubAnswerer:
    text: str = "Ответ ассистента"
    calls: list[tuple[str, date]] = field(default_factory=list)

    async def answer(self, question: str, _profile: object, on_date: date) -> AnswerOutcome:
        self.calls.append((question, on_date))
        return AnswerOutcome(
            text=self.text,
            escalated=False,
            reason="answered",
            citations=(),
            retrieved=(),
        )


def build(
    audit: RecordingAudit | None = None,
) -> tuple[ActionExecutor, RecordingMessaging, StubAnswerer, RecordingAudit]:
    messaging = RecordingMessaging()
    answerer = StubAnswerer()
    recorder = audit or RecordingAudit()
    executor = ActionExecutor(
        messaging=messaging,
        answerer=answerer,  # type: ignore[arg-type]
        copy=COPY,
        audit=recorder,
    )
    return executor, messaging, answerer, recorder


async def test_send_uses_the_scenario_text_and_keyboard() -> None:
    executor, messaging, _, _ = build()
    action = Action(
        kind=ActionKind.SEND,
        text="Первый день",
        image="party.jpg",
        keyboard=((Button(id="done", text="Готово"),),),
    )

    await executor.execute(action, ActionContext(address=ADDRESS, on_date=date(2026, 10, 20)))

    assert messaging.sent[0].text == "Первый день"
    assert messaging.sent[0].image == "party.jpg"
    assert messaging.sent[0].keyboard[0][0].id == "done"


async def test_reminder_is_prefixed_from_copy() -> None:
    executor, messaging, _, _ = build()
    action = Action(kind=ActionKind.SEND, text="Пришлите документы", note="reminder")

    await executor.execute(action, ActionContext(address=ADDRESS, on_date=date(2026, 10, 20)))

    assert messaging.sent[0].text == f"{COPY.reminder_prefix}Пришлите документы"


async def test_escalation_sends_copy_and_records_an_event() -> None:
    executor, messaging, _, audit = build()
    action = Action(kind=ActionKind.ESCALATE, reason=EscalationReason.TIMEOUT)

    await executor.execute(
        action,
        ActionContext(address=ADDRESS, on_date=date(2026, 10, 20), employee_id=EMPLOYEE),
    )

    assert messaging.sent[0].text == COPY.escalation_for(EscalationReason.TIMEOUT)
    assert audit.names() == ["escalation_requested"]
    assert audit.events[0][1]["employee_id"] == str(EMPLOYEE)


async def test_completion_sends_the_completion_copy() -> None:
    executor, messaging, _, audit = build()
    action = Action(kind=ActionKind.COMPLETE, outcome=Outcome.COMPLETED, image="goodbye.jpg")

    await executor.execute(
        action,
        ActionContext(address=ADDRESS, on_date=date(2026, 10, 20), employee_id=EMPLOYEE),
    )

    assert messaging.sent[0].text == COPY.completion
    assert messaging.sent[0].image == "goodbye.jpg"
    assert audit.names() == ["run_completed"]
    assert audit.events[0][1]["employee_id"] == str(EMPLOYEE)


async def test_answer_calls_the_assistant_with_the_employee_context() -> None:
    executor, messaging, answerer, _ = build()
    action = Action(kind=ActionKind.ANSWER)
    context = ActionContext(
        address=ADDRESS,
        on_date=date(2026, 10, 23),
        profile=profile(),
        question="Сколько дней отпуска?",
    )

    await executor.execute(action, context)

    assert answerer.calls == [("Сколько дней отпуска?", date(2026, 10, 23))]
    # The short "searching" line arrives first so the wait is not silent, the answer second.
    assert [message.text for message in messaging.sent] == [
        "Секунду, ищу ответ в базе знаний…",
        "Ответ ассистента",
    ]


async def test_answer_without_a_question_is_skipped_and_recorded() -> None:
    executor, messaging, answerer, audit = build()
    action = Action(kind=ActionKind.ANSWER)

    await executor.execute(
        action,
        ActionContext(
            address=ADDRESS,
            on_date=date(2026, 10, 23),
            employee_id=EMPLOYEE,
            profile=profile(),
        ),
    )

    assert answerer.calls == []
    assert messaging.sent == []
    assert audit.names() == ["answer_skipped"]
    assert audit.events[0][1]["employee_id"] == str(EMPLOYEE)


async def test_ignore_sends_nothing() -> None:
    executor, messaging, _, audit = build()

    await executor.execute(
        Action(kind=ActionKind.IGNORE),
        ActionContext(address=ADDRESS, on_date=date(2026, 10, 23), employee_id=EMPLOYEE),
    )

    assert messaging.sent == []
    assert audit.names() == ["action_ignored"]
    assert audit.events[0][1]["employee_id"] == str(EMPLOYEE)
    assert NullAudit


async def test_a_repeated_question_explains_what_is_wrong() -> None:
    """Repeating the prompt verbatim leaves a person guessing; the hint names the accepted input."""
    executor, messaging, _, _ = build()
    action = Action(
        kind=ActionKind.SEND,
        text="Оцените доступность руководителя от 1 до 10",
        note="survey:repeat:scale",
    )

    await executor.execute(action, ActionContext(address=ADDRESS, on_date=date(2026, 10, 20)))

    text = messaging.sent[0].text
    assert text.startswith("Оцените доступность руководителя от 1 до 10")
    assert COPY.answer_hint("scale") in text


async def test_a_survey_question_carries_its_position_and_the_answer_is_acknowledged() -> None:
    executor, messaging, _, _ = build()
    asked = Action(kind=ActionKind.SEND, text="Как встретили коллеги?", note="survey:ask:2:9")
    ack = Action(kind=ActionKind.SEND, text="9", note="survey:ack")
    context = ActionContext(address=ADDRESS, on_date=date(2026, 10, 23))

    await executor.execute(asked, context)
    await executor.execute(ack, context)

    assert messaging.sent[0].text == "Вопрос 2 из 9\n\nКак встретили коллеги?"
    assert messaging.sent[1].text == "Записал: 9"


async def test_an_open_answer_is_acknowledged_without_a_value() -> None:
    executor, messaging, _, _ = build()
    await executor.execute(
        Action(kind=ActionKind.SEND, text="", note="survey:ack"),
        ActionContext(address=ADDRESS, on_date=date(2026, 10, 23)),
    )

    assert messaging.sent[0].text == "Записал, спасибо."


async def test_completion_carries_a_menu_instead_of_a_dead_end() -> None:
    executor, messaging, _, _ = build()

    await executor.execute(
        Action(kind=ActionKind.COMPLETE, outcome=Outcome.COMPLETED),
        ActionContext(address=ADDRESS, on_date=date(2026, 10, 23)),
    )

    assert [button.id for button in messaging.sent[0].keyboard[0]] == [
        "post_benefits",
        "post_ask",
        "post_reboot",
    ]


async def test_the_greeting_carries_the_first_name() -> None:
    executor, messaging, _, _ = build()

    await executor.execute(
        Action(kind=ActionKind.SEND, text="Здравствуйте, {name}! Я Корсик."),
        ActionContext(address=ADDRESS, on_date=date(2026, 10, 20), profile=profile()),
    )

    assert messaging.sent[0].text == "Здравствуйте, Иван! Я Корсик."


async def test_a_missing_name_does_not_leave_a_hole_in_the_greeting() -> None:
    executor, messaging, _, _ = build()

    await executor.execute(
        Action(kind=ActionKind.SEND, text="Здравствуйте, {name}! Я Корсик."),
        ActionContext(address=ADDRESS, on_date=date(2026, 10, 20)),
    )

    assert messaging.sent[0].text == "Здравствуйте! Я Корсик."


async def test_the_stage_notice_names_the_position() -> None:
    executor, _, _, _ = build()

    assert executor.stage_progress_text(3, 21) == "Шаг 3 из 21."


async def test_a_reminder_is_one_short_line_with_a_way_out() -> None:
    executor, messaging, _, _ = build()
    action = Action(kind=ActionKind.SEND, text="Документы", note="reminder_soft")

    await executor.execute(action, ActionContext(address=ADDRESS, on_date=date(2026, 10, 20)))

    assert messaging.sent[0].text == COPY.soft_reminder("Документы")
    assert "готово" in messaging.sent[0].text


async def test_a_skipped_question_is_acknowledged() -> None:
    executor, messaging, _, _ = build()

    await executor.execute(
        Action(kind=ActionKind.SEND, text="", note="survey:skipped"),
        ActionContext(address=ADDRESS, on_date=date(2026, 10, 20)),
    )

    assert messaging.sent[0].text == COPY.survey_skipped


async def test_a_reminder_at_a_button_step_points_at_the_buttons() -> None:
    """The "напишите «готово»" promise is false where only a button counts (live 2026-10-25)."""
    executor, messaging, _, _ = build()

    await executor.execute(
        Action(kind=ActionKind.SEND, text="Знакомство", note="reminder_soft_button"),
        ActionContext(address=ADDRESS, on_date=date(2026, 10, 20)),
    )

    assert messaging.sent[0].text == COPY.soft_reminder_button("Знакомство")
    assert "кнопкой" in messaging.sent[0].text
    assert "готово" not in messaging.sent[0].text


async def test_a_confirmation_at_a_button_step_hints_at_the_buttons() -> None:
    executor, messaging, _, _ = build()

    await executor.execute(
        Action(kind=ActionKind.SEND, text="", note="step:button_hint"),
        ActionContext(address=ADDRESS, on_date=date(2026, 10, 20)),
    )

    assert messaging.sent[0].text == COPY.button_hint

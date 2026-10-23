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
    ChatId,
    EscalationReason,
    Outcome,
)

from .fakes import EMPLOYEE, RecordingAudit, RecordingMessaging, profile

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
        keyboard=((Button(id="done", text="Готово"),),),
    )

    await executor.execute(action, ActionContext(chat_id=ChatId(1), on_date=date(2026, 10, 20)))

    assert messaging.sent[0].text == "Первый день"
    assert messaging.sent[0].keyboard[0][0].id == "done"


async def test_reminder_is_prefixed_from_copy() -> None:
    executor, messaging, _, _ = build()
    action = Action(kind=ActionKind.SEND, text="Пришлите документы", note="reminder")

    await executor.execute(action, ActionContext(chat_id=ChatId(1), on_date=date(2026, 10, 20)))

    assert messaging.sent[0].text == f"{COPY.reminder_prefix}Пришлите документы"


async def test_escalation_sends_copy_and_records_an_event() -> None:
    executor, messaging, _, audit = build()
    action = Action(kind=ActionKind.ESCALATE, reason=EscalationReason.TIMEOUT)

    await executor.execute(
        action,
        ActionContext(chat_id=ChatId(1), on_date=date(2026, 10, 20), employee_id=EMPLOYEE),
    )

    assert messaging.sent[0].text == COPY.escalation_for(EscalationReason.TIMEOUT)
    assert audit.names() == ["escalation_requested"]
    assert audit.events[0][1]["employee_id"] == str(EMPLOYEE)


async def test_completion_sends_the_completion_copy() -> None:
    executor, messaging, _, audit = build()
    action = Action(kind=ActionKind.COMPLETE, outcome=Outcome.COMPLETED)

    await executor.execute(
        action,
        ActionContext(chat_id=ChatId(1), on_date=date(2026, 10, 20), employee_id=EMPLOYEE),
    )

    assert messaging.sent[0].text == COPY.completion
    assert audit.names() == ["run_completed"]
    assert audit.events[0][1]["employee_id"] == str(EMPLOYEE)


async def test_answer_calls_the_assistant_with_the_employee_context() -> None:
    executor, messaging, answerer, _ = build()
    action = Action(kind=ActionKind.ANSWER)
    context = ActionContext(
        chat_id=ChatId(1),
        on_date=date(2026, 10, 23),
        profile=profile(),
        question="Сколько дней отпуска?",
    )

    await executor.execute(action, context)

    assert answerer.calls == [("Сколько дней отпуска?", date(2026, 10, 23))]
    assert messaging.sent[0].text == "Ответ ассистента"


async def test_answer_without_a_question_is_skipped_and_recorded() -> None:
    executor, messaging, answerer, audit = build()
    action = Action(kind=ActionKind.ANSWER)

    await executor.execute(
        action,
        ActionContext(
            chat_id=ChatId(1),
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
        ActionContext(chat_id=ChatId(1), on_date=date(2026, 10, 23), employee_id=EMPLOYEE),
    )

    assert messaging.sent == []
    assert audit.names() == ["action_ignored"]
    assert audit.events[0][1]["employee_id"] == str(EMPLOYEE)
    assert NullAudit

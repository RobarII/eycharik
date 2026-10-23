"""Turn a pure scenario decision into messages.

Every user-visible string comes from the knowledge base, a scenario file, or the copy file. This
module only decides which of the three applies.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from onboarding.app.audit import NullAudit
from onboarding.app.copy import Copy
from onboarding.app.worker.answerer import Answerer
from onboarding.core.models import (
    Action,
    ActionKind,
    ChatId,
    EmployeeProfile,
    EscalationReason,
)
from onboarding.ports import AuditLog, Messaging, OutboundMessage, QuestionLog

MAX_LOGGED_QUESTION = 2000


@dataclass(frozen=True, slots=True)
class ActionContext:
    chat_id: ChatId
    on_date: date
    profile: EmployeeProfile | None = None
    question: str | None = None


class ActionExecutor:
    def __init__(
        self,
        *,
        messaging: Messaging,
        answerer: Answerer,
        copy: Copy,
        audit: AuditLog | None = None,
        questions: QuestionLog | None = None,
    ) -> None:
        self._messaging = messaging
        self._answerer = answerer
        self._copy = copy
        self._audit = audit or NullAudit()
        self._questions = questions

    async def execute(self, action: Action, context: ActionContext) -> None:
        match action.kind:
            case ActionKind.SEND:
                assert action.text is not None
                text = (
                    self._copy.reminder(action.text)
                    if action.note == "reminder"
                    else action.text
                )
                await self._messaging.send(
                    OutboundMessage(
                        chat_id=context.chat_id,
                        text=text,
                        keyboard=action.keyboard,
                    )
                )
            case ActionKind.ANSWER:
                await self._answer(context)
            case ActionKind.ESCALATE:
                reason = action.reason or EscalationReason.MANUAL
                await self._messaging.send(
                    OutboundMessage(
                        chat_id=context.chat_id,
                        text=self._copy.escalation_for(reason),
                    )
                )
                await self._audit.record(
                    "escalation_requested", reason=reason.value, note=action.note
                )
            case ActionKind.COMPLETE:
                await self._messaging.send(
                    OutboundMessage(chat_id=context.chat_id, text=self._copy.completion)
                )
                await self._audit.record("run_completed", outcome=str(action.outcome))
            case ActionKind.IGNORE:
                await self._audit.record("action_ignored")

    async def _answer(self, context: ActionContext) -> None:
        if context.profile is None or not context.question:
            await self._audit.record("answer_skipped", reason="no_profile_or_question")
            return
        outcome = await self._answerer.answer(context.question, context.profile, context.on_date)
        if self._questions is not None:
            await self._questions.record_question(
                employee_id=context.profile.employee_id,
                chat_id=context.chat_id,
                text=context.question[:MAX_LOGGED_QUESTION],
                answered=not outcome.escalated,
                reason=outcome.reason,
                citations=[str(citation) for citation in outcome.citations],
                latency_ms=outcome.completion.latency_ms if outcome.completion else None,
            )
        await self._messaging.send(
            OutboundMessage(chat_id=context.chat_id, text=outcome.text)
        )


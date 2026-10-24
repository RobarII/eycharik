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
    Address,
    EmployeeId,
    EmployeeProfile,
    EscalationReason,
)
from onboarding.ports import AuditLog, OutboundMessage, QuestionLog, Sender

MAX_LOGGED_QUESTION = 2000


@dataclass(frozen=True, slots=True)
class ActionContext:
    address: Address
    on_date: date
    employee_id: EmployeeId | None = None
    profile: EmployeeProfile | None = None
    question: str | None = None


class ActionExecutor:
    def __init__(
        self,
        *,
        messaging: Sender,
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

    def help_text(self) -> str:
        return self._copy.help

    def unknown_command_text(self) -> str:
        return self._copy.unknown_command

    def ask_question_text(self) -> str:
        return self._copy.ask_question

    def no_next_stage_text(self) -> str:
        return self._copy.no_next_stage

    def not_understood_text(self) -> str:
        return self._copy.not_understood

    def stage_scheduled_text(self, stage: str, when: str) -> str:
        return self._copy.stage_scheduled.format(stage=stage, when=when)

    def stage_waiting_text(self, stage: str, when: str) -> str:
        return self._copy.stage_waiting.format(stage=stage, when=when)

    async def execute(self, action: Action, context: ActionContext) -> None:
        match action.kind:
            case ActionKind.SEND:
                assert action.text is not None
                text = self._resolve(action)
                await self._messaging.send(
                    OutboundMessage(
                        address=context.address,
                        text=text,
                        image=action.image,
                        keyboard=action.keyboard,
                    )
                )
            case ActionKind.ANSWER:
                await self._answer(context)
            case ActionKind.ESCALATE:
                reason = action.reason or EscalationReason.MANUAL
                await self._messaging.send(
                    OutboundMessage(
                        address=context.address,
                        text=self._copy.escalation_for(reason),
                    )
                )
                await self._audit.record(
                    "escalation_requested",
                    employee_id=_employee(context),
                    reason=reason.value,
                    note=action.note,
                )
            case ActionKind.COMPLETE:
                await self._messaging.send(
                    OutboundMessage(
                        address=context.address,
                        text=self._copy.completion,
                        image=action.image,
                    )
                )
                await self._audit.record(
                    "run_completed",
                    employee_id=_employee(context),
                    outcome=str(action.outcome),
                )
            case ActionKind.IGNORE:
                await self._audit.record("action_ignored", employee_id=_employee(context))

    def _resolve(self, action: Action) -> str:
        """Attach a hint to a repeated survey question so the person learns what went wrong."""
        assert action.text is not None
        if action.note == "reminder":
            return self._copy.reminder(action.text)
        if action.note is not None and action.note.startswith("survey:repeat"):
            kind = action.note.rpartition(":")[2]
            hint = self._copy.answer_hint(kind)
            return f"{action.text}\n\n{hint}" if hint else action.text
        return action.text

    async def _answer(self, context: ActionContext) -> None:
        if context.profile is None or not context.question:
            await self._audit.record(
                "answer_skipped",
                employee_id=_employee(context),
                reason="no_profile_or_question",
            )
            return
        outcome = await self._answerer.answer(context.question, context.profile, context.on_date)
        if self._questions is not None:
            await self._questions.record_question(
                employee_id=context.profile.employee_id,
                address=context.address,
                text=context.question[:MAX_LOGGED_QUESTION],
                answered=not outcome.escalated,
                reason=outcome.reason,
                citations=[str(citation) for citation in outcome.citations],
                latency_ms=outcome.completion.latency_ms if outcome.completion else None,
            )
        await self._messaging.send(
            OutboundMessage(address=context.address, text=outcome.text)
        )


def _employee(context: ActionContext) -> str | None:
    return None if context.employee_id is None else str(context.employee_id)

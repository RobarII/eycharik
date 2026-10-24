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
    Button,
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

    def stage_progress_text(self, index: int, total: int) -> str:
        return self._copy.stage_progress.format(index=index, total=total)

    async def execute(self, action: Action, context: ActionContext) -> None:
        match action.kind:
            case ActionKind.SEND:
                assert action.text is not None
                text = self._resolve(action, context)
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
                # The completion is not a dead end: the menu keeps the usual questions one tap
                # away instead of asking the person to invent a command.
                await self._messaging.send(
                    OutboundMessage(
                        address=context.address,
                        text=self._copy.completion,
                        image=action.image,
                        keyboard=(_menu_buttons(self._copy),),
                    )
                )
                await self._audit.record(
                    "run_completed",
                    employee_id=_employee(context),
                    outcome=str(action.outcome),
                )
            case ActionKind.IGNORE:
                await self._audit.record("action_ignored", employee_id=_employee(context))

    def post_run_benefits_text(self) -> str:
        return self._copy.post_run_benefits

    def file_received_text(self) -> str:
        return self._copy.file_received

    def _resolve(self, action: Action, context: ActionContext) -> str:
        """Attach the position, the hint or the acknowledgement the copy file words."""
        assert action.text is not None
        if action.note == "reminder":
            return self._copy.reminder(self._personal(action.text, context))
        if action.note == "survey:ack":
            return self._copy.survey_acknowledgement(action.text)
        if action.note is not None and action.note.startswith("survey:ask:"):
            _, _, index, total = action.note.split(":")
            progress = self._copy.survey_question(int(index), int(total))
            return f"{progress}\n\n{self._personal(action.text, context)}"
        if action.note is not None and action.note.startswith("survey:repeat"):
            kind = action.note.rpartition(":")[2]
            hint = self._copy.answer_hint(kind)
            text = self._personal(action.text, context)
            return f"{text}\n\n{hint}" if hint else text
        return self._personal(action.text, context)

    def _personal(self, text: str, context: ActionContext) -> str:
        """``{name}`` is the employee's first name: a greeting with no name reads as a mailing."""
        if "{name}" not in text:
            return text
        name = _first_name(context.profile)
        if name:
            return text.replace("{name}", name)
        return text.replace(", {name}", "").replace("{name}, ", "").replace("{name}", "").strip()

    async def _answer(self, context: ActionContext) -> None:
        if context.profile is None or not context.question:
            await self._audit.record(
                "answer_skipped",
                employee_id=_employee(context),
                reason="no_profile_or_question",
            )
            return
        # A long wait with no reaction reads as a broken bot (live 2026-10-24: 4.5 s average, 10.7 s
        # worst). One short line buys patience; the answer follows as its own message.
        if self._copy.searching:
            await self._messaging.send(
                OutboundMessage(address=context.address, text=self._copy.searching)
            )
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


def _menu_buttons(copy: Copy) -> tuple[Button, ...]:
    return tuple(Button(id=button_id, text=text) for button_id, text in copy.post_run_menu)


def _first_name(profile: EmployeeProfile | None) -> str:
    if profile is None or not profile.name:
        return ""
    return profile.name.strip().split(maxsplit=1)[0]


def _employee(context: ActionContext) -> str | None:
    return None if context.employee_id is None else str(context.employee_id)

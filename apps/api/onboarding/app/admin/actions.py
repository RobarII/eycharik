"""The two writes the recruiter cabinet is allowed to make.

Both are a single database transaction: the cabinet must never close a question without queueing
its reply, and it must never remove an employee while leaving an active run behind. The reply goes
through the outbox, not through MAX, so pacing and retries stay in one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

from sqlalchemy import delete, select, update
from sqlalchemy.engine import CursorResult

from onboarding.app.admin.queries import employee_scope_filters
from onboarding.app.db.models import AuditRow, EmployeeRow, MessageRow, QuestionRow, RunRow
from onboarding.app.db.session import Database
from onboarding.core.retention import redact_fields
from onboarding.ports import Clock


class QuestionNotFoundError(Exception):
    """The question does not exist or belongs to an employee outside the caller's scope."""


class QuestionAlreadyResolvedError(Exception):
    """Another recruiter closed the question first."""


class EmployeeNotFoundError(Exception):
    """No employee row with this id."""


@dataclass(frozen=True, slots=True)
class Resolution:
    question_id: int
    employee_id: str
    chat_id: int
    resolved_at: datetime
    resolved_by: str


@dataclass(frozen=True, slots=True)
class Offboarding:
    employee_id: str
    questions_deleted: int
    runs_closed: int
    audit_redacted: int


class QuestionResolver:
    def __init__(self, database: Database, clock: Clock) -> None:
        self._database = database
        self._clock = clock

    async def resolve(
        self,
        question_id: int,
        *,
        text: str,
        actor: str,
        recruiter_id: str | None,
        department: str | None,
    ) -> Resolution:
        now = self._clock.now()
        scope = select(EmployeeRow.id).where(
            *employee_scope_filters(recruiter_id, department)
        )
        async with self._database.session() as session:
            row = (
                await session.execute(
                    update(QuestionRow)
                    .where(
                        QuestionRow.id == question_id,
                        QuestionRow.answered.is_(False),
                        QuestionRow.employee_id.in_(scope),
                    )
                    .values(
                        answered=True,
                        resolved_at=now,
                        resolved_by=actor,
                        resolution=text,
                    )
                    .returning(QuestionRow)
                )
            ).scalar_one_or_none()
            if row is None:
                visible = await session.scalar(
                    select(QuestionRow.id).where(
                        QuestionRow.id == question_id,
                        QuestionRow.employee_id.in_(scope),
                    )
                )
                if visible is None:
                    raise QuestionNotFoundError(f"question {question_id} not found")
                raise QuestionAlreadyResolvedError(f"question {question_id} already resolved")

            session.add(MessageRow(chat_id=row.chat_id, text=text))
            session.add(
                AuditRow(
                    name="question_resolved",
                    fields={
                        "question_id": row.id,
                        "employee_id": row.employee_id,
                        "by": actor,
                        "reply_chars": len(text),
                    },
                )
            )
            return Resolution(
                question_id=row.id,
                employee_id=row.employee_id or "",
                chat_id=row.chat_id,
                resolved_at=now,
                resolved_by=actor,
            )


class EmployeeOffboarder:
    """Soft-delete an employee: stop the run and delete the transcript, keep the audit skeleton."""

    def __init__(self, database: Database, clock: Clock) -> None:
        self._database = database
        self._clock = clock

    async def offboard(self, employee_id: str, *, actor: str) -> Offboarding:
        now = self._clock.now()
        async with self._database.session() as session:
            employee = await session.get(EmployeeRow, employee_id)
            if employee is None:
                raise EmployeeNotFoundError(f"employee {employee_id} not found")
            if employee.status == "left":
                return Offboarding(
                    employee_id=employee_id,
                    questions_deleted=0,
                    runs_closed=0,
                    audit_redacted=0,
                )

            employee.status = "left"
            employee.left_at = now

            closed = await session.execute(
                update(RunRow)
                .where(RunRow.employee_id == employee_id, RunRow.status == "active")
                .values(status="completed")
            )
            deleted = await session.execute(
                delete(QuestionRow).where(QuestionRow.employee_id == employee_id)
            )
            audits = (
                await session.scalars(
                    select(AuditRow).where(AuditRow.fields["employee_id"].astext == employee_id)
                )
            ).all()
            redacted = 0
            for audit in audits:
                cleaned = redact_fields(audit.fields)
                if cleaned != audit.fields:
                    audit.fields = cleaned
                    redacted += 1

            questions_deleted = int(cast(CursorResult[Any], deleted).rowcount or 0)
            runs_closed = int(cast(CursorResult[Any], closed).rowcount or 0)
            session.add(
                AuditRow(
                    name="employee_offboarded",
                    fields={
                        "employee_id": employee_id,
                        "by": actor,
                        "questions_deleted": questions_deleted,
                        "runs_closed": runs_closed,
                    },
                )
            )
            return Offboarding(
                employee_id=employee_id,
                questions_deleted=questions_deleted,
                runs_closed=runs_closed,
                audit_redacted=redacted,
            )

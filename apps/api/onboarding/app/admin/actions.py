"""The writes the recruiter cabinet is allowed to make.

Each is a single database transaction: the cabinet must never close a question without queueing its
reply, must never remove an employee while leaving an active run behind, and must never write a
directory row without saying who did it. The reply goes through the outbox, not through MAX, so
pacing and retries stay in one place.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, cast

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError

from onboarding.app.admin.queries import employee_record, employee_scope_filters
from onboarding.app.admin.records import EmployeeRecord
from onboarding.app.db.models import (
    AuditRow,
    ChannelIdentityRow,
    EmployeeRow,
    MessageRow,
    QuestionRow,
    RunRow,
)
from onboarding.app.db.session import Database
from onboarding.core.models import Address, Channel, ChatId
from onboarding.core.retention import redact_fields
from onboarding.ports import Clock


class QuestionNotFoundError(Exception):
    """The question does not exist or belongs to an employee outside the caller's scope."""


class QuestionAlreadyResolvedError(Exception):
    """Another recruiter closed the question first."""


class EmployeeNotFoundError(Exception):
    """No employee row with this id."""


class UnknownAssigneeError(Exception):
    """The requested owner is not an admin the server knows how to authenticate."""


class EmployeeAlreadyExistsError(Exception):
    """The directory already holds a row with this id; a create is not an upsert."""


class UnknownScenarioError(Exception):
    """The scenario is not deployed, so a new employee could not start onboarding."""


class EmployeeStillActiveError(Exception):
    """Restoring is only for a person who has left; an active row is already restored."""


@dataclass(frozen=True, slots=True)
class EmployeeFields:
    """The mutable directory columns, as a route or an HRIS sync hands them over."""

    employee_id: str
    name: str
    role: str
    department: str
    recruiter_id: str | None
    started_at: date
    audience: tuple[str, ...]
    scenario_id: str


@dataclass(frozen=True, slots=True)
class Resolution:
    question_id: int
    employee_id: str
    address: Address
    resolved_at: datetime
    resolved_by: str


@dataclass(frozen=True, slots=True)
class Assignment:
    question_id: int
    employee_id: str
    assignee: str | None
    by: str


@dataclass(frozen=True, slots=True)
class Offboarding:
    employee_id: str
    questions_deleted: int
    messages_deleted: int
    runs_closed: int
    audit_redacted: int


class QuestionAssigner:
    """Puts a name on a question, or takes it off.

    Assignment is not ownership of the answer: the resolver still checks the scope and still refuses
    a question somebody else already closed. The column only stops two recruiters from drafting the
    same reply.
    """

    def __init__(self, database: Database, clock: Clock) -> None:
        self._database = database
        self._clock = clock

    async def assign(
        self,
        question_id: int,
        *,
        assignee: str | None,
        actor: str,
        known: frozenset[str],
        recruiter_id: str | None,
        department: str | None,
    ) -> Assignment:
        if assignee is not None and assignee not in known:
            raise UnknownAssigneeError(f"assignee {assignee} is not an admin")
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
                    .values(assignee=assignee)
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

            session.add(
                AuditRow(
                    name="question_assigned" if assignee else "question_unassigned",
                    fields={
                        "question_id": row.id,
                        "employee_id": row.employee_id,
                        "assignee": assignee,
                        "by": actor,
                        "at": self._clock.now().isoformat(),
                    },
                )
            )
            return Assignment(
                question_id=row.id,
                employee_id=row.employee_id or "",
                assignee=row.assignee,
                by=actor,
            )


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

            session.add(
                MessageRow(channel=row.channel, chat_id=row.chat_id, text=text)
            )
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
                address=Address(channel=Channel(row.channel), chat_id=ChatId(row.chat_id)),
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
                    messages_deleted=0,
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
            # A queued reminder or reply must not reach a person who has already left. The outbox
            # has no employee id, so collect every chat the employee ever used before the run and
            # question rows that carry them disappear.
            addresses = {
                (row.channel, row.chat_id)
                for row in await session.execute(
                    select(RunRow.channel, RunRow.chat_id).where(
                        RunRow.employee_id == employee_id
                    )
                )
            }
            addresses |= {
                (row.channel, row.chat_id)
                for row in await session.execute(
                    select(QuestionRow.channel, QuestionRow.chat_id).where(
                        QuestionRow.employee_id == employee_id
                    )
                )
            }
            # A left employee keeps no way back in: the messenger accounts go with the transcript.
            await session.execute(
                delete(ChannelIdentityRow).where(ChannelIdentityRow.employee_id == employee_id)
            )
            deleted = await session.execute(
                delete(QuestionRow).where(QuestionRow.employee_id == employee_id)
            )
            messages_deleted = 0
            for channel, chat_id in sorted(addresses):
                deleted_messages = await session.execute(
                    delete(MessageRow).where(
                        MessageRow.channel == channel, MessageRow.chat_id == chat_id
                    )
                )
                messages_deleted += int(
                    cast(CursorResult[Any], deleted_messages).rowcount or 0
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
                        "messages_deleted": messages_deleted,
                        "runs_closed": runs_closed,
                    },
                )
            )
            return Offboarding(
                employee_id=employee_id,
                questions_deleted=questions_deleted,
                messages_deleted=messages_deleted,
                runs_closed=runs_closed,
                audit_redacted=redacted,
            )


class EmployeeDirectory:
    """The directory writes: create, correct, and sync a batch from an HR system.

    A row's history is the audit log, not a shadow table. ``status`` is deliberately not a part of
    an ordinary update: leaving goes through ``EmployeeOffboarder`` (which also purges), and
    restoring is a separate, explicit change that cannot resurrect a transcript.
    """

    def __init__(self, database: Database, clock: Clock) -> None:
        self._database = database
        self._clock = clock

    async def create(self, fields: EmployeeFields, *, actor: str) -> EmployeeRecord:
        now = self._clock.now()
        async with self._database.session() as session:
            row = EmployeeRow(
                id=fields.employee_id,
                name=fields.name,
                role=fields.role,
                department=fields.department,
                recruiter_id=fields.recruiter_id,
                started_at=fields.started_at,
                audience=list(fields.audience),
                scenario_id=fields.scenario_id,
                status="active",
                created_at=now,
            )
            session.add(row)
            try:
                await session.flush()
            except IntegrityError as error:
                raise EmployeeAlreadyExistsError(fields.employee_id) from error
            session.add(
                AuditRow(
                    name="employee_created",
                    fields={
                        "employee_id": fields.employee_id,
                        "by": actor,
                        "scenario": fields.scenario_id,
                        "department": fields.department,
                    },
                )
            )
            return employee_record(row)

    async def update(
        self,
        employee_id: str,
        changes: Mapping[str, object],
        *,
        actor: str,
    ) -> EmployeeRecord:
        values = dict(changes)
        restore = values.pop("status", None) == "active"
        if restore:
            values["status"] = "active"
            values["left_at"] = None
        async with self._database.session() as session:
            row = await session.get(EmployeeRow, employee_id)
            if row is None:
                raise EmployeeNotFoundError(f"employee {employee_id} not found")
            if values:
                await session.execute(
                    update(EmployeeRow)
                    .where(EmployeeRow.id == employee_id)
                    .values(**values)
                )
                await session.refresh(row)
                session.add(
                    AuditRow(
                        name="employee_restored" if restore else "employee_updated",
                        fields={
                            "employee_id": employee_id,
                            "by": actor,
                            "changed": sorted(values),
                        },
                    )
                )
            return employee_record(row)

    async def upsert(
        self, rows: Sequence[EmployeeFields], *, actor: str
    ) -> tuple[int, int]:
        """Insert or correct a batch. A left employee is not resurrected by a sync.

        The status columns are excluded from the conflict update on purpose: an HRIS feed that
        still lists someone who has left must not undo an offboarding that purged a transcript.
        """
        if not rows:
            return (0, 0)
        ids = [row.employee_id for row in rows]
        async with self._database.session() as session:
            known = set(
                (await session.scalars(select(EmployeeRow.id).where(EmployeeRow.id.in_(ids))))
                .all()
            )
            statement = insert(EmployeeRow).values(
                [
                    {
                        "id": row.employee_id,
                        "name": row.name,
                        "role": row.role,
                        "department": row.department,
                        "recruiter_id": row.recruiter_id,
                        "started_at": row.started_at,
                        "audience": list(row.audience),
                        "scenario_id": row.scenario_id,
                        "status": "active",
                    }
                    for row in rows
                ]
            )
            await session.execute(
                statement.on_conflict_do_update(
                    index_elements=[EmployeeRow.id],
                    set_={
                        "name": statement.excluded.name,
                        "role": statement.excluded.role,
                        "department": statement.excluded.department,
                        "recruiter_id": statement.excluded.recruiter_id,
                        "started_at": statement.excluded.started_at,
                        "audience": statement.excluded.audience,
                        "scenario_id": statement.excluded.scenario_id,
                    },
                )
            )
            created = len(set(ids) - known)
            updated = len(set(ids) & known)
            session.add(
                AuditRow(
                    name="employees_synced",
                    fields={"by": actor, "created": created, "updated": updated},
                )
            )
            return created, updated

"""Adapters for runs, deduplication, audit and the question log."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from onboarding.app.db.models import AuditRow, EmployeeRow, EventRow, QuestionRow, RunRow
from onboarding.app.db.session import Database
from onboarding.core.models import (
    CancelReminder,
    ChatId,
    EmployeeId,
    KeepReminder,
    ReminderPlan,
    RunId,
    ScheduleReminder,
    StepState,
    TimeoutAction,
)
from onboarding.ports import RunAlreadyActiveError, StoredRun


class SqlRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, run: StoredRun) -> None:
        state = run.state
        self._session.add(
            RunRow(
                id=UUID(state.run_id),
                employee_id=str(state.employee_id),
                scenario_id=state.scenario_id,
                scenario_version=state.scenario_version,
                step_id=state.step_id,
                entered_at=state.entered_at,
                chat_id=int(run.chat_id),
                status="active" if run.active else "completed",
                **_reminder_columns(run.reminder),
            )
        )
        try:
            await self._session.flush()
        except IntegrityError as error:
            raise RunAlreadyActiveError(str(state.employee_id)) from error

    async def load(self, run_id: RunId) -> StoredRun | None:
        row = await self._session.get(RunRow, UUID(run_id))
        return _stored_run(row) if row is not None else None

    async def save(self, run: StoredRun) -> None:
        state = run.state
        await self._session.execute(
            update(RunRow)
            .where(RunRow.id == UUID(state.run_id))
            .values(
                step_id=state.step_id,
                entered_at=state.entered_at,
                chat_id=int(run.chat_id),
                status="active" if run.active else "completed",
                **_reminder_columns(run.reminder),
            )
        )

    async def find_active_by_employee(self, employee_id: EmployeeId) -> StoredRun | None:
        row = await self._session.scalar(
            select(RunRow).where(
                RunRow.employee_id == str(employee_id), RunRow.status == "active"
            )
        )
        return _stored_run(row) if row is not None else None

    async def list_active(
        self, *, recruiter_id: str | None, limit: int
    ) -> tuple[StoredRun, ...]:
        statement = select(RunRow).where(RunRow.status == "active")
        if recruiter_id is not None:
            statement = statement.join(EmployeeRow, EmployeeRow.id == RunRow.employee_id).where(
                EmployeeRow.recruiter_id == recruiter_id
            )
        rows = await self._session.scalars(
            statement.order_by(RunRow.entered_at).limit(min(limit, 200))
        )
        return tuple(_stored_run(row) for row in rows)


def _stored_run(row: RunRow) -> StoredRun:
    state = StepState(
        run_id=RunId(str(row.id)),
        employee_id=EmployeeId(row.employee_id),
        scenario_id=row.scenario_id,
        scenario_version=row.scenario_version,
        step_id=row.step_id,
        entered_at=row.entered_at,
    )
    return StoredRun(
        state=state,
        reminder=_reminder(row),
        chat_id=ChatId(row.chat_id),
        active=row.status == "active",
    )


def _reminder_columns(reminder: ReminderPlan) -> dict[str, object]:
    match reminder:
        case KeepReminder():
            return {"reminder_at": None, "reminder_action": None}
        case CancelReminder():
            return {"reminder_at": None, "reminder_action": None}
        case ScheduleReminder(due_at=due_at, action=action):
            return {"reminder_at": due_at, "reminder_action": action.value}
    raise AssertionError("unknown reminder plan")


def _reminder(row: RunRow) -> ReminderPlan:
    if row.reminder_at is None:
        return KeepReminder()
    return ScheduleReminder(
        due_at=row.reminder_at,
        step_id=row.step_id,
        action=TimeoutAction(row.reminder_action or TimeoutAction.REMIND),
    )


class SqlEventDeduper:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def first_sighting(self, key: str) -> bool:
        result = await self._session.execute(
            insert(EventRow).values(key=key).on_conflict_do_nothing()
        )
        return bool(cast(CursorResult[Any], result).rowcount)


class SqlAuditLog:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, name: str, **fields: object) -> None:
        self._session.add(AuditRow(name=name, fields=_jsonable(fields)))


class SqlQuestionLog:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_question(
        self,
        *,
        employee_id: EmployeeId | None,
        chat_id: ChatId,
        text: str,
        answered: bool,
        reason: str,
        citations: Sequence[str],
        latency_ms: int | None,
    ) -> None:
        self._session.add(
            QuestionRow(
                employee_id=str(employee_id) if employee_id else None,
                chat_id=int(chat_id),
                text=text,
                answered=answered,
                reason=reason,
                citations=list(citations),
                latency_ms=latency_ms,
            )
        )


def _jsonable(fields: dict[str, object]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in fields.items():
        if isinstance(value, datetime | UUID):
            result[key] = str(value)
        else:
            result[key] = value
    return result


class DatabaseAuditLog:
    """Audit writer that owns its transaction, usable from any process."""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def record(self, name: str, **fields: object) -> None:
        async with self._database.session() as session:
            await SqlAuditLog(session).record(name, **fields)


class DatabaseQuestionLog:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def record_question(
        self,
        *,
        employee_id: EmployeeId | None,
        chat_id: ChatId,
        text: str,
        answered: bool,
        reason: str,
        citations: Sequence[str],
        latency_ms: int | None,
    ) -> None:
        async with self._database.session() as session:
            await SqlQuestionLog(session).record_question(
                employee_id=employee_id,
                chat_id=chat_id,
                text=text,
                answered=answered,
                reason=reason,
                citations=citations,
                latency_ms=latency_ms,
            )


class DatabaseRunRepository:
    """Run repository with one transaction per operation, for request and job handlers."""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def create(self, run: StoredRun) -> None:
        async with self._database.session() as session:
            await SqlRunRepository(session).create(run)

    async def load(self, run_id: RunId) -> StoredRun | None:
        async with self._database.session() as session:
            return await SqlRunRepository(session).load(run_id)

    async def save(self, run: StoredRun) -> None:
        async with self._database.session() as session:
            await SqlRunRepository(session).save(run)

    async def find_active_by_employee(self, employee_id: EmployeeId) -> StoredRun | None:
        async with self._database.session() as session:
            return await SqlRunRepository(session).find_active_by_employee(employee_id)

    async def list_active(
        self, *, recruiter_id: str | None, limit: int
    ) -> tuple[StoredRun, ...]:
        async with self._database.session() as session:
            return await SqlRunRepository(session).list_active(
                recruiter_id=recruiter_id, limit=limit
            )

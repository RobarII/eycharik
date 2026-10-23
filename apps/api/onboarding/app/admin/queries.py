"""Read models for the recruiter cabinet.

Every query is scoped by the principal's subject unless it is HR. The scope is a SQL predicate, not
a post-filter, so a wrong id cannot leak a row that was fetched and then discarded.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import desc, select

from onboarding.app.db.models import AuditRow, EmployeeRow, QuestionRow, RunRow
from onboarding.app.db.session import Database


@dataclass(frozen=True, slots=True)
class RunRecord:
    run_id: str
    employee_id: str
    name: str
    role: str
    department: str
    scenario_id: str
    scenario_version: int
    step_id: str
    entered_at: datetime
    active: bool


@dataclass(frozen=True, slots=True)
class EventRecord:
    name: str
    at: datetime
    fields: dict[str, object]


@dataclass(frozen=True, slots=True)
class QuestionRecord:
    employee_id: str
    employee_name: str
    text: str
    answered: bool
    reason: str
    citations: list[str]
    asked_at: datetime


class AdminQueries:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def runs(self, *, recruiter_id: str | None, limit: int) -> tuple[RunRecord, ...]:
        async with self._database.session() as session:
            rows = await session.execute(_run_query(recruiter_id).limit(limit))
            return tuple(_run_record(*row) for row in rows.all())

    async def run(self, run_id: str, *, recruiter_id: str | None) -> RunRecord | None:
        async with self._database.session() as session:
            row = (
                await session.execute(
                    _run_query(recruiter_id).where(RunRow.id == _uuid(run_id)).limit(1)
                )
            ).first()
            return _run_record(*row) if row is not None else None

    async def events(self, employee_id: str, *, limit: int = 50) -> tuple[EventRecord, ...]:
        async with self._database.session() as session:
            rows = await session.scalars(
                select(AuditRow)
                .where(AuditRow.fields["employee_id"].astext == employee_id)
                .order_by(desc(AuditRow.at))
                .limit(limit)
            )
            return tuple(
                EventRecord(name=row.name, at=row.at, fields=row.fields) for row in rows
            )

    async def questions(
        self,
        *,
        recruiter_id: str | None,
        answered: bool | None,
        limit: int,
        employee_id: str | None = None,
    ) -> tuple[QuestionRecord, ...]:
        async with self._database.session() as session:
            statement = select(QuestionRow).join(
                EmployeeRow, EmployeeRow.id == QuestionRow.employee_id
            )
            if recruiter_id is not None:
                statement = statement.where(EmployeeRow.recruiter_id == recruiter_id)
            if answered is not None:
                statement = statement.where(QuestionRow.answered == answered)
            if employee_id is not None:
                statement = statement.where(QuestionRow.employee_id == employee_id)
            rows = await session.execute(
                statement.add_columns(EmployeeRow.name)
                .order_by(desc(QuestionRow.asked_at))
                .limit(limit)
            )
            return tuple(
                QuestionRecord(
                    employee_id=question.employee_id or "",
                    employee_name=name,
                    text=question.text,
                    answered=question.answered,
                    reason=question.reason,
                    citations=list(question.citations),
                    asked_at=question.asked_at,
                )
                for question, name in rows.all()
            )


def _run_query(recruiter_id: str | None) -> Any:
    statement = select(
        RunRow,
        EmployeeRow.name,
        EmployeeRow.role,
        EmployeeRow.department,
    ).join(EmployeeRow, EmployeeRow.id == RunRow.employee_id)
    if recruiter_id is not None:
        statement = statement.where(EmployeeRow.recruiter_id == recruiter_id)
    return statement.order_by(desc(RunRow.updated_at))


def _run_record(
    run: RunRow, name: str, role: str, department: str
) -> RunRecord:
    return RunRecord(
        run_id=str(run.id),
        employee_id=run.employee_id,
        name=name,
        role=role,
        department=department,
        scenario_id=run.scenario_id,
        scenario_version=run.scenario_version,
        step_id=run.step_id,
        entered_at=run.entered_at,
        active=run.status == "active",
    )


def _uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        return uuid.UUID(int=0)

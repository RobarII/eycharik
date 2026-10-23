"""Read models for the recruiter cabinet.

Every query is scoped by the principal's subject unless it is HR. The scope is a SQL predicate, not
a post-filter, so a wrong id cannot leak a row that was fetched and then discarded.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import desc, func, literal_column, select, text

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


@dataclass(frozen=True, slots=True)
class OverviewRecord:
    active_runs: int
    completed_runs: int
    high_risk: int
    medium_risk: int
    unanswered_questions: int
    top_tags: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class DigestRecord:
    employee_id: str
    employee_name: str
    department: str
    step_id: str
    level: str
    reasons: tuple[str, ...]
    tags: tuple[str, ...]
    at: datetime


class AdminQueries:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def runs(
        self, *, recruiter_id: str | None, department: str | None = None, limit: int
    ) -> tuple[RunRecord, ...]:
        async with self._database.session() as session:
            rows = await session.execute(
                _run_query(recruiter_id, department).limit(limit)
            )
            return tuple(_run_record(*row) for row in rows.all())

    async def run(
        self, run_id: str, *, recruiter_id: str | None, department: str | None = None
    ) -> RunRecord | None:
        async with self._database.session() as session:
            row = (
                await session.execute(
                    _run_query(recruiter_id, department)
                    .where(RunRow.id == _uuid(run_id))
                    .limit(1)
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

    async def overview(
        self, *, recruiter_id: str | None, department: str | None, since: datetime
    ) -> OverviewRecord:
        async with self._database.session() as session:
            runs = select(func.count()).select_from(RunRow).join(
                EmployeeRow, EmployeeRow.id == RunRow.employee_id
            )
            runs = _scope_runs(runs, recruiter_id, department)
            active = await session.scalar(runs.where(RunRow.status == "active"))
            completed = await session.scalar(runs.where(RunRow.status == "completed"))

            assessments = select(
                AuditRow.fields["level"].astext, func.count()
            ).where(AuditRow.name == "risk_assessed", AuditRow.at >= since)
            if recruiter_id is not None or department is not None:
                assessments = assessments.join(
                    EmployeeRow, EmployeeRow.id == AuditRow.fields["employee_id"].astext
                ).where(*_scope_filters(recruiter_id, department))
            level_rows = (
                await session.execute(assessments.group_by(literal_column("1")))
            ).all()
            levels: dict[str, int] = {str(level): int(total) for level, total in level_rows}

            unanswered = await session.scalar(
                select(func.count())
                .select_from(QuestionRow)
                .join(EmployeeRow, EmployeeRow.id == QuestionRow.employee_id)
                .where(QuestionRow.answered.is_(False), *_scope_filters(recruiter_id, department))
            )

            tags_statement = text(
                """
                SELECT tag, count(*) AS total
                FROM audit_log, jsonb_array_elements_text(fields -> 'tags') AS tag
                WHERE name = 'risk_assessed' AND at >= :since AND fields -> 'tags' <> '[]'
                GROUP BY tag ORDER BY total DESC, tag LIMIT 5
                """
            )
            tags = tuple(
                (str(tag), int(total))
                for tag, total in (await session.execute(tags_statement, {"since": since})).all()
            )
            return OverviewRecord(
                active_runs=int(active or 0),
                completed_runs=int(completed or 0),
                high_risk=int(levels.get("high", 0)),
                medium_risk=int(levels.get("medium", 0)),
                unanswered_questions=int(unanswered or 0),
                top_tags=tags,
            )

    async def digest(
        self,
        *,
        recruiter_id: str | None,
        department: str | None,
        since: datetime,
        limit: int = 50,
    ) -> tuple[DigestRecord, ...]:
        """Signals that deserve a human this week, newest first, one row per employee and step."""
        async with self._database.session() as session:
            statement = (
                select(AuditRow, EmployeeRow.name, EmployeeRow.department)
                .join(EmployeeRow, EmployeeRow.id == AuditRow.fields["employee_id"].astext)
                .where(
                    AuditRow.name == "risk_assessed",
                    AuditRow.at >= since,
                    AuditRow.fields["level"].astext.in_(("high", "medium")),
                    *_scope_filters(recruiter_id, department),
                )
                .order_by(desc(AuditRow.at), desc(AuditRow.id))
                .limit(200)
            )
            rows = (await session.execute(statement)).all()
        seen: set[tuple[str, str]] = set()
        items: list[DigestRecord] = []
        for event, name, department_name in rows:
            employee_id = str(event.fields.get("employee_id", ""))
            step_id = str(event.fields.get("step", ""))
            if (employee_id, step_id) in seen:
                continue
            seen.add((employee_id, step_id))
            items.append(
                DigestRecord(
                    employee_id=employee_id,
                    employee_name=name,
                    department=department_name,
                    step_id=step_id,
                    level=str(event.fields.get("level", "")),
                    reasons=_texts(event.fields.get("reasons")),
                    tags=_texts(event.fields.get("tags")),
                    at=event.at,
                )
            )
            if len(items) >= limit:
                break
        return tuple(items)

    async def questions(
        self,
        *,
        recruiter_id: str | None,
        answered: bool | None,
        limit: int,
        department: str | None = None,
        employee_id: str | None = None,
    ) -> tuple[QuestionRecord, ...]:
        async with self._database.session() as session:
            statement = select(QuestionRow).join(
                EmployeeRow, EmployeeRow.id == QuestionRow.employee_id
            )
            for condition in _scope_filters(recruiter_id, department):
                statement = statement.where(condition)
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


def _texts(value: object) -> tuple[str, ...]:
    return tuple(str(item) for item in value) if isinstance(value, list) else ()


def _scope_filters(recruiter_id: str | None, department: str | None) -> tuple[Any, ...]:
    filters: list[Any] = []
    if recruiter_id is not None:
        filters.append(EmployeeRow.recruiter_id == recruiter_id)
    if department is not None:
        filters.append(EmployeeRow.department == department)
    return tuple(filters)


def _scope_runs(statement: Any, recruiter_id: str | None, department: str | None) -> Any:
    for condition in _scope_filters(recruiter_id, department):
        statement = statement.where(condition)
    return statement


def _run_query(recruiter_id: str | None, department: str | None = None) -> Any:
    statement = select(
        RunRow,
        EmployeeRow.name,
        EmployeeRow.role,
        EmployeeRow.department,
    ).join(EmployeeRow, EmployeeRow.id == RunRow.employee_id)
    for condition in _scope_filters(recruiter_id, department):
        statement = statement.where(condition)
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

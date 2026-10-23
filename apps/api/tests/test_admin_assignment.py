"""Integration: a question gets an owner, and the owner filter reads the same rows.

Skipped unless ``ONBOARDING_TEST_DATABASE`` points at a disposable database.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select, text

from onboarding.app.admin.actions import (
    QuestionAlreadyResolvedError,
    QuestionAssigner,
    QuestionNotFoundError,
    UnknownAssigneeError,
)
from onboarding.app.admin.queries import AdminQueries
from onboarding.app.db.models import AuditRow, EmployeeRow, QuestionRow
from onboarding.app.db.session import Database

pytestmark = pytest.mark.integration

NOW = datetime(2026, 10, 23, 9, 0, tzinfo=UTC)


class FrozenClock:
    def now(self) -> datetime:
        return NOW


def database_url() -> str:
    url = os.environ.get("ONBOARDING_TEST_DATABASE")
    if not url:
        pytest.skip("ONBOARDING_TEST_DATABASE is not set")
    return url


@pytest.fixture
async def database() -> AsyncIterator[Database]:
    db = Database(database_url())
    async with db.session() as session:
        await session.execute(
            text(
                "TRUNCATE messages, jobs, events, questions, audit_log, runs, employees "
                "RESTART IDENTITY CASCADE"
            )
        )
        session.add_all(
            [
                EmployeeRow(
                    id=f"40{i:02d}",
                    name=f"Сотрудник {i}",
                    role="Оператор",
                    department="Производство" if i % 2 == 0 else "Логистика",
                    recruiter_id="rec-1" if i % 2 == 0 else "rec-2",
                    started_at=date(2026, 10, 1),
                    audience=["all"],
                )
                for i in range(4)
            ]
        )
        session.add_all(
            [
                QuestionRow(
                    employee_id=f"40{i:02d}",
                    chat_id=200 + i,
                    text=f"Вопрос {i}",
                    answered=False,
                    reason="no_sources",
                    citations=[],
                    asked_at=NOW + timedelta(minutes=i),
                )
                for i in range(4)
            ]
        )
    yield db
    await db.dispose()


async def first_open(database: Database, recruiter_id: str = "rec-1") -> int:
    records, _ = await AdminQueries(database).questions_page(
        recruiter_id=recruiter_id, answered=False, limit=1
    )
    return records[0].id


async def test_claiming_sets_the_owner_and_writes_an_audit_event(
    database: Database,
) -> None:
    question_id = await first_open(database)

    assignment = await QuestionAssigner(database, FrozenClock()).assign(
        question_id,
        assignee="rec-1",
        actor="rec-1",
        known=frozenset({"rec-1", "hr-1"}),
        recruiter_id="rec-1",
        department=None,
    )

    assert assignment.assignee == "rec-1"
    async with database.session() as session:
        stored = await session.scalar(
            select(QuestionRow.assignee).where(QuestionRow.id == question_id)
        )
        names = (await session.scalars(select(AuditRow.name))).all()
    assert stored == "rec-1"
    assert "question_assigned" in names


async def test_releasing_clears_the_owner(database: Database) -> None:
    question_id = await first_open(database)
    assigner = QuestionAssigner(database, FrozenClock())

    await assigner.assign(
        question_id,
        assignee="rec-1",
        actor="rec-1",
        known=frozenset({"rec-1"}),
        recruiter_id="rec-1",
        department=None,
    )
    released = await assigner.assign(
        question_id,
        assignee=None,
        actor="rec-1",
        known=frozenset({"rec-1"}),
        recruiter_id="rec-1",
        department=None,
    )

    assert released.assignee is None
    async with database.session() as session:
        names = (await session.scalars(select(AuditRow.name))).all()
    assert "question_unassigned" in names


async def test_the_owner_filter_matches_only_claimed_rows(database: Database) -> None:
    queries = AdminQueries(database)
    records, _ = await queries.questions_page(
        recruiter_id="rec-1", answered=False, limit=10
    )
    claimed = records[0].id
    await QuestionAssigner(database, FrozenClock()).assign(
        claimed,
        assignee="rec-1",
        actor="rec-1",
        known=frozenset({"rec-1"}),
        recruiter_id="rec-1",
        department=None,
    )

    mine, _ = await queries.questions_page(
        recruiter_id="rec-1", answered=False, limit=10, assignee="rec-1"
    )
    free, _ = await queries.questions_page(
        recruiter_id="rec-1", answered=False, limit=10, unassigned=True
    )

    assert [record.id for record in mine] == [claimed]
    assert claimed not in {record.id for record in free}
    assert await queries.questions_total(
        recruiter_id="rec-1", answered=False, assignee="rec-1"
    ) == len(mine)
    assert await queries.questions_total(
        recruiter_id="rec-1", answered=False, unassigned=True
    ) == len(free)


async def test_an_unknown_owner_is_refused(database: Database) -> None:
    question_id = await first_open(database)

    with pytest.raises(UnknownAssigneeError):
        await QuestionAssigner(database, FrozenClock()).assign(
            question_id,
            assignee="nobody",
            actor="rec-1",
            known=frozenset({"rec-1"}),
            recruiter_id="rec-1",
            department=None,
        )


async def test_a_question_outside_the_scope_is_invisible(database: Database) -> None:
    """The even employee ids belong to `rec-1`; the odd ones must not leak through a claim."""
    records, _ = await AdminQueries(database).questions_page(
        recruiter_id="rec-2", answered=False, limit=1
    )
    elsewhere = records[0].id

    with pytest.raises(QuestionNotFoundError):
        await QuestionAssigner(database, FrozenClock()).assign(
            elsewhere,
            assignee="rec-1",
            actor="rec-1",
            known=frozenset({"rec-1"}),
            recruiter_id="rec-1",
            department=None,
        )


async def test_a_closed_question_cannot_be_claimed(database: Database) -> None:
    async with database.session() as session:
        closed = await session.scalar(
            select(QuestionRow.id).where(QuestionRow.answered.is_(False)).limit(1)
        )
        await session.execute(
            text("UPDATE questions SET answered = true WHERE id = :id"), {"id": closed}
        )

    with pytest.raises(QuestionAlreadyResolvedError):
        await QuestionAssigner(database, FrozenClock()).assign(
            closed,
            assignee="rec-1",
            actor="rec-1",
            known=frozenset({"rec-1"}),
            recruiter_id="rec-1",
            department=None,
        )

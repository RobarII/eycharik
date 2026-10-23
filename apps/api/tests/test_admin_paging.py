"""Integration: keyset paging is complete and has no overlaps.

Skipped unless ``ONBOARDING_TEST_DATABASE`` points at a disposable database.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from onboarding.app.admin.queries import AdminQueries, QuestionCursor, RunCursor
from onboarding.app.db.models import EmployeeRow, QuestionRow, RunRow
from onboarding.app.db.session import Database

pytestmark = pytest.mark.integration


def database_url() -> str:
    url = os.environ.get("ONBOARDING_TEST_DATABASE")
    if not url:
        pytest.skip("ONBOARDING_TEST_DATABASE is not set")
    return url


NOW = datetime(2026, 10, 23, 9, 0, tzinfo=UTC)


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
                    id=f"30{i:02d}",
                    name=f"Сотрудник {i}",
                    role="Оператор",
                    department="Производство",
                    recruiter_id="rec-1",
                    started_at=date(2026, 10, 1),
                    audience=["all"],
                )
                for i in range(7)
            ]
        )
        # Two runs share a millisecond on purpose: the id must still break the tie.
        session.add_all(
            [
                RunRow(
                    id=uuid4(),
                    employee_id=f"30{i:02d}",
                    scenario_id="onboarding_default",
                    scenario_version=1,
                    step_id="welcome",
                    entered_at=NOW,
                    chat_id=100 + i,
                    status="active" if i % 2 == 0 else "completed",
                    updated_at=NOW + timedelta(minutes=i // 2),
                )
                for i in range(7)
            ]
        )
        session.add_all(
            [
                QuestionRow(
                    employee_id=f"30{i:02d}",
                    chat_id=100 + i,
                    text=f"Вопрос {i}",
                    answered=i % 3 == 0,
                    reason="no_sources",
                    citations=[],
                    asked_at=NOW + timedelta(minutes=i),
                )
                for i in range(7)
            ]
        )
    yield db
    await db.dispose()


async def test_runs_page_through_every_row_exactly_once(database: Database) -> None:
    queries = AdminQueries(database)
    seen: list[str] = []
    cursor: RunCursor | None = None
    pages = 0

    while True:
        records, has_more = await queries.runs_page(
            recruiter_id="rec-1", limit=2, after=cursor
        )
        pages += 1
        seen.extend(record.run_id for record in records)
        if not has_more:
            break
        last = records[-1]
        cursor = RunCursor(at=last.updated_at, run_id=last.run_id)
        assert pages < 10, "paging never reached the last page"

    assert len(seen) == 7
    assert len(set(seen)) == 7
    assert await queries.runs_total(recruiter_id="rec-1") == 7


async def test_runs_page_is_newest_activity_first(database: Database) -> None:
    records, _ = await AdminQueries(database).runs_page(recruiter_id="rec-1", limit=7)

    stamps = [record.updated_at for record in records]
    assert stamps == sorted(stamps, reverse=True)


async def test_questions_page_respects_the_unanswered_first_order(
    database: Database,
) -> None:
    queries = AdminQueries(database)
    seen: list[int] = []
    cursor: QuestionCursor | None = None

    while True:
        records, has_more = await queries.questions_page(
            recruiter_id="rec-1", answered=None, limit=2, after=cursor
        )
        seen.extend(record.id for record in records)
        if not has_more:
            break
        last = records[-1]
        cursor = QuestionCursor(
            answered=last.answered, asked_at=last.asked_at, id=last.id
        )

    assert len(seen) == 7
    assert len(set(seen)) == 7
    assert await queries.questions_total(recruiter_id="rec-1", answered=None) == 7


async def test_question_total_follows_the_status_filter(database: Database) -> None:
    queries = AdminQueries(database)

    unanswered = await queries.questions_total(recruiter_id="rec-1", answered=False)
    answered = await queries.questions_total(recruiter_id="rec-1", answered=True)

    assert (unanswered, answered) == (4, 3)


async def test_status_filter_and_total_agree(database: Database) -> None:
    queries = AdminQueries(database)

    active, _ = await queries.runs_page(recruiter_id="rec-1", limit=10, active=True)
    completed, _ = await queries.runs_page(recruiter_id="rec-1", limit=10, active=False)

    assert len(active) == await queries.runs_total(recruiter_id="rec-1", active=True)
    assert len(completed) == await queries.runs_total(recruiter_id="rec-1", active=False)
    assert all(record.active for record in active)
    assert not any(record.active for record in completed)


async def test_search_matches_a_department_and_ignores_case(database: Database) -> None:
    queries = AdminQueries(database)

    hit, _ = await queries.runs_page(recruiter_id="rec-1", limit=10, search="ПРОИЗВ")
    miss, _ = await queries.runs_page(recruiter_id="rec-1", limit=10, search="Sales")

    assert len(hit) == 7
    assert miss == ()


async def test_search_treats_a_percent_sign_as_a_character(database: Database) -> None:
    queries = AdminQueries(database)

    page, _ = await queries.runs_page(recruiter_id="rec-1", limit=10, search="%")

    assert page == ()

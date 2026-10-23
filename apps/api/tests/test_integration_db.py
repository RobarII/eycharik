"""Integration: the adapters against a real Postgres with pgvector.

Skipped unless ``ONBOARDING_TEST_DATABASE`` points at a disposable database. The suite truncates
its tables, so never point it at anything you care about.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import text

from onboarding.app.admin.queries import AdminQueries
from onboarding.app.clock import FrozenClock
from onboarding.app.copy import load_copy
from onboarding.app.db.directory import SqlDirectory
from onboarding.app.db.kb import PostgresKnowledgeBase, PostgresKnowledgeWriter
from onboarding.app.db.models import EmployeeRow
from onboarding.app.db.outbox import MessageDispatcher, OutboxMessaging
from onboarding.app.db.queue import JobQueue
from onboarding.app.db.repos import (
    DatabaseAuditLog,
    DatabaseQuestionLog,
    DatabaseRunRepository,
    SqlEventDeduper,
)
from onboarding.app.db.scheduler import ReminderScheduler
from onboarding.app.db.session import Database
from onboarding.app.knowledge.embedding import HashingEmbedder
from onboarding.app.knowledge.pipeline import ingest
from onboarding.app.prompts import PromptLibrary
from onboarding.app.scenarios import ScenarioCatalog
from onboarding.app.settings import Settings
from onboarding.app.worker.actions import ActionContext, ActionExecutor
from onboarding.app.worker.answerer import Answerer
from onboarding.app.worker.service import OnboardingService
from onboarding.core.models import (
    Action,
    ActionKind,
    ChatId,
    Event,
    EventKind,
    ScheduleReminder,
)
from onboarding.ports import OutboundMessage, SearchQuery

from .fakes import (
    EMPLOYEE,
    NOW,
    FakeKnowledgeBase,
    RecordingMessaging,
    ScriptedLLM,
    scored_chunk,
)

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[3]
SCENARIOS = ROOT / "apps" / "api" / "onboarding" / "scenarios"
COPY = load_copy(ROOT / "docs" / "product" / "copy.yaml")


def database_url() -> str:
    url = os.environ.get("ONBOARDING_TEST_DATABASE")
    if not url:
        pytest.skip("ONBOARDING_TEST_DATABASE is not set")
    return url


def settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url=database_url(),
        embed_provider="hashing",
        max_webhook_secret="test",
    )


@pytest.fixture
async def database() -> AsyncIterator[Database]:
    db = Database(database_url())
    async with db.session() as session:
        await session.execute(
            text(
                "TRUNCATE messages, jobs, events, questions, audit_log, runs, employees, "
                "kb_chunks, kb_documents RESTART IDENTITY CASCADE"
            )
        )
        session.add(
            EmployeeRow(
                id=str(EMPLOYEE),
                name="Иван Иванов",
                role="Инженер",
                department="ИТ",
                recruiter_id="rec-1",
                started_at=date(2026, 10, 20),
                audience=["all", "dept:it"],
            )
        )
    yield db
    await db.dispose()


def build_service(
    db: Database, *, messaging: RecordingMessaging, knowledge: FakeKnowledgeBase
) -> OnboardingService:
    answerer = Answerer(
        knowledge=knowledge,
        llm=ScriptedLLM([]),
        prompts=PromptLibrary(ROOT / "docs" / "prompts"),
        copy=COPY,
        settings=settings(),
        audit=DatabaseAuditLog(db),
    )
    executor = ActionExecutor(
        messaging=messaging,
        answerer=answerer,
        copy=COPY,
        audit=DatabaseAuditLog(db),
        questions=DatabaseQuestionLog(db),
    )
    return OnboardingService(
        runs=DatabaseRunRepository(db),
        catalog=ScenarioCatalog.load(SCENARIOS),
        executor=executor,
        clock=FrozenClock(NOW),
        directory=SqlDirectory(db),
        audit=DatabaseAuditLog(db),
    )


async def test_start_persists_a_run_and_reaches_the_admin_view(database: Database) -> None:
    messaging = RecordingMessaging()
    service = build_service(database, messaging=messaging, knowledge=FakeKnowledgeBase())

    result = await service.start(EMPLOYEE, ChatId(1))

    assert result.handled
    assert len(messaging.sent) == 2
    active = await DatabaseRunRepository(database).find_active_by_employee(EMPLOYEE)
    assert active is not None
    assert active.state.step_id == "first_day_checklist"
    assert isinstance(active.reminder, ScheduleReminder)

    runs = await AdminQueries(database).runs(recruiter_id="rec-1", limit=10)
    assert [run.employee_id for run in runs] == [str(EMPLOYEE)]
    assert runs[0].name == "Иван Иванов"
    assert await AdminQueries(database).runs(recruiter_id="other", limit=10) == ()


async def test_second_start_is_rejected_by_the_partial_index(database: Database) -> None:
    service = build_service(
        database, messaging=RecordingMessaging(), knowledge=FakeKnowledgeBase()
    )

    first = await service.start(EMPLOYEE, ChatId(1))
    second = await service.start(EMPLOYEE, ChatId(1))

    assert first.handled
    assert not second.handled


async def test_event_deduper_accepts_one_delivery(database: Database) -> None:
    async with database.session() as session:
        deduper = SqlEventDeduper(session)
        assert await deduper.first_sighting("mid-1")
        assert not await deduper.first_sighting("mid-1")


async def test_outbox_and_dispatcher_deliver_a_message(database: Database) -> None:
    direct = RecordingMessaging()
    outbox = OutboxMessaging(database, direct)

    message_id = await outbox.send(OutboundMessage(chat_id=ChatId(7), text="привет"))

    assert message_id.isdigit()
    assert direct.sent == []
    delivered = await MessageDispatcher(database, direct).run_once()
    assert delivered == 1
    assert direct.sent[0].text == "привет"


async def test_scheduler_enqueues_a_due_reminder(database: Database) -> None:
    service = build_service(
        database, messaging=RecordingMessaging(), knowledge=FakeKnowledgeBase()
    )
    await service.start(EMPLOYEE, ChatId(1))
    async with database.session() as session:
        await session.execute(
            text("UPDATE runs SET reminder_at = now() - interval '1 minute'")
        )

    assert await ReminderScheduler(database).tick() == 1
    jobs = await JobQueue(database).claim()
    assert [job.kind for job in jobs] == ["timeout"]
    assert jobs[0].payload["employee_id"] == str(EMPLOYEE)


async def test_transition_is_persisted(database: Database) -> None:
    messaging = RecordingMessaging()
    service = build_service(database, messaging=messaging, knowledge=FakeKnowledgeBase())
    await service.start(EMPLOYEE, ChatId(1))

    result = await service.handle(
        EMPLOYEE,
        ChatId(1),
        Event(kind=EventKind.BUTTON_PRESSED, at=NOW, button_id="checklist_done"),
    )

    assert result.handled
    run = await DatabaseRunRepository(database).find_active_by_employee(EMPLOYEE)
    assert run is not None
    assert run.state.step_id == "meet_the_team"
    assert run.state.employee_id == EMPLOYEE


async def test_question_is_logged_with_citations(database: Database) -> None:
    knowledge = FakeKnowledgeBase(chunks=(scored_chunk(),))
    direct = RecordingMessaging()
    outbox = OutboxMessaging(database, direct)
    answerer = Answerer(
        knowledge=knowledge,
        llm=ScriptedLLM(
            [
                json.dumps(
                    {
                        "answer": "28 дней [hr/leave-policy#0]",
                        "citations": ["hr/leave-policy#0"],
                        "confidence": 0.9,
                        "escalate": False,
                        "reason": "answered",
                    }
                )
            ]
        ),
        prompts=PromptLibrary(ROOT / "docs" / "prompts"),
        copy=COPY,
        settings=settings(),
    )
    executor = ActionExecutor(
        messaging=outbox,
        answerer=answerer,
        copy=COPY,
        questions=DatabaseQuestionLog(database),
    )
    await executor.execute(
        Action(kind=ActionKind.ANSWER),
        ActionContext(
            chat_id=ChatId(1),
            on_date=date(2026, 10, 23),
            profile=await SqlDirectory(database).profile(EMPLOYEE),
            question="Сколько дней отпуска?",
        ),
    )

    questions = await AdminQueries(database).questions(
        recruiter_id="rec-1", answered=True, limit=10
    )
    assert questions[0].citations == ["hr/leave-policy#0"]
    assert questions[0].text == "Сколько дней отпуска?"


async def test_knowledge_round_trip(database: Database) -> None:
    embedder = HashingEmbedder(dim=1024)
    report = await ingest(
        directory=ROOT / "knowledge",
        schema_path=ROOT / "docs" / "contracts" / "doc.schema.json",
        writer=PostgresKnowledgeWriter(database),
        embedder=embedder,
    )
    assert report.documents >= 6

    kb = PostgresKnowledgeBase(database, embedder)
    results = await kb.search(
        SearchQuery(
            text="сколько дней отпуска",
            audience=("all", "dept:it"),
            on_date=date(2026, 10, 23),
            limit=5,
        )
    )

    assert results
    assert any(result.chunk.doc_id == "hr/leave-policy" for result in results)
    assert all(result.chunk.id for result in results)

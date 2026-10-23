"""Integration: the adapters against a real Postgres with pgvector.

Skipped unless ``ONBOARDING_TEST_DATABASE`` points at a disposable database. The suite truncates
its tables, so never point it at anything you care about.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from onboarding.app.admin.queries import AdminQueries
from onboarding.app.clock import FrozenClock
from onboarding.app.copy import load_copy
from onboarding.app.db.directory import SqlDirectory
from onboarding.app.db.kb import PostgresKnowledgeBase, PostgresKnowledgeWriter
from onboarding.app.db.models import EmployeeRow, QuestionRow
from onboarding.app.db.outbox import MessageDispatcher, OutboxMessaging
from onboarding.app.db.queue import JobQueue
from onboarding.app.db.repos import (
    DatabaseAuditLog,
    DatabaseQuestionLog,
    DatabaseRunRepository,
    RunAlreadyActiveError,
    SqlEventDeduper,
)
from onboarding.app.db.scheduler import ReminderScheduler
from onboarding.app.db.session import Database
from onboarding.app.knowledge.embedding import HashingEmbedder
from onboarding.app.knowledge.ingest import CorpusError
from onboarding.app.knowledge.pipeline import ingest, ingest_document
from onboarding.app.prompts import PromptLibrary
from onboarding.app.scenarios import ScenarioCatalog
from onboarding.app.scheduler.main import tick_once
from onboarding.app.settings import Settings
from onboarding.app.worker.actions import ActionContext, ActionExecutor
from onboarding.app.worker.answerer import Answerer
from onboarding.app.worker.jobs import JobRunner
from onboarding.app.worker.service import OnboardingService
from onboarding.core.models import (
    Action,
    ActionKind,
    ChatId,
    EmployeeId,
    Event,
    EventKind,
    RunId,
    ScheduleReminder,
    StepState,
    SurveyAnswer,
    TimeoutAction,
)
from onboarding.core.transitions import start as start_run
from onboarding.ports import OutboundMessage, SearchQuery, StoredRun

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
        scenario_version=1,
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


async def test_survey_progress_survives_a_save_and_load(database: Database) -> None:
    runs = DatabaseRunRepository(database)
    state = StepState(
        run_id=RunId(str(uuid4())),
        employee_id=EMPLOYEE,
        scenario_id="onboarding_default",
        scenario_version=1,
        step_id="week_two_check",
        entered_at=NOW,
        answers=(SurveyAnswer(question_id="manager", score=6),),
        question_index=1,
        pending_reason="manager",
    )
    await runs.create(StoredRun(state=state, reminder=ScheduleReminder(
        due_at=NOW, step_id="week_two_check", action=TimeoutAction.REMIND
    ), chat_id=ChatId(1)))

    loaded = await runs.load(state.run_id)

    assert loaded is not None
    assert loaded.state.answers == (SurveyAnswer(question_id="manager", score=6),)
    assert loaded.state.question_index == 1
    assert loaded.state.pending_reason == "manager"


async def test_second_start_is_rejected_by_the_partial_index(database: Database) -> None:
    service = build_service(database, messaging=RecordingMessaging(), knowledge=FakeKnowledgeBase())

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
    service = build_service(database, messaging=RecordingMessaging(), knowledge=FakeKnowledgeBase())
    await service.start(EMPLOYEE, ChatId(1))
    async with database.session() as session:
        await session.execute(text("UPDATE runs SET reminder_at = now() - interval '1 minute'"))

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


async def test_question_queue_carries_the_employee_and_respects_scope(
    database: Database,
) -> None:
    async with database.session() as session:
        session.add_all(
            [
                EmployeeRow(
                    id="2002",
                    name="Пётр Петров",
                    role="Технолог",
                    department="Производство",
                    recruiter_id="rec-2",
                    started_at=date(2026, 10, 21),
                    audience=["all"],
                ),
                QuestionRow(
                    employee_id=str(EMPLOYEE),
                    chat_id=1,
                    text="Сколько дней отпуска?",
                    answered=False,
                    reason="no_sources",
                    citations=[],
                    asked_at=datetime.now(UTC),
                ),
                QuestionRow(
                    employee_id="2002",
                    chat_id=2,
                    text="Где взять ноутбук?",
                    answered=False,
                    reason="no_sources",
                    citations=[],
                    asked_at=datetime.now(UTC),
                ),
            ]
        )

    mine = await AdminQueries(database).questions(recruiter_id="rec-1", answered=False, limit=10)
    everyone = await AdminQueries(database).questions(recruiter_id=None, answered=False, limit=10)
    only_employee = await AdminQueries(database).questions(
        recruiter_id="rec-1", answered=None, limit=10, employee_id=str(EMPLOYEE)
    )

    assert [(q.employee_id, q.employee_name) for q in mine] == [(str(EMPLOYEE), "Иван Иванов")]
    assert {q.employee_id for q in everyone} == {str(EMPLOYEE), "2002"}
    assert [q.text for q in only_employee] == ["Сколько дней отпуска?"]


async def test_creating_a_run_for_an_unknown_employee_is_not_a_race(
    database: Database,
) -> None:

    catalog = ScenarioCatalog.load(SCENARIOS)
    transition = start_run(
        catalog.active("onboarding_default"),
        RunId("00000000-0000-4000-8000-000000000404"),
        EmployeeId("404"),
        NOW,
    )

    with pytest.raises(IntegrityError) as raised:
        await DatabaseRunRepository(database).create(
            StoredRun(state=transition.state, reminder=transition.reminder, chat_id=ChatId(1))
        )

    assert not isinstance(raised.value, RunAlreadyActiveError)


async def test_a_second_active_run_for_the_same_employee_is_a_race(
    database: Database,
) -> None:
    catalog = ScenarioCatalog.load(SCENARIOS)
    scenario = catalog.active("onboarding_default")
    repository = DatabaseRunRepository(database)
    first = start_run(
        scenario,
        RunId("00000000-0000-4000-8000-000000000501"),
        EMPLOYEE,
        NOW,
    )
    await repository.create(
        StoredRun(state=first.state, reminder=first.reminder, chat_id=ChatId(1))
    )

    second = start_run(
        scenario,
        RunId("00000000-0000-4000-8000-000000000502"),
        EMPLOYEE,
        NOW,
    )
    with pytest.raises(RunAlreadyActiveError):
        await repository.create(
            StoredRun(state=second.state, reminder=second.reminder, chat_id=ChatId(1))
        )


async def test_completion_is_attached_to_the_employee(database: Database) -> None:
    service = build_service(database, messaging=RecordingMessaging(), knowledge=FakeKnowledgeBase())
    await service.start(EMPLOYEE, ChatId(1))

    for event in (
        Event(kind=EventKind.BUTTON_PRESSED, at=NOW, button_id="checklist_done"),
        Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="готово"),
        Event(kind=EventKind.FILE_RECEIVED, at=NOW, file_id="file-1"),
        Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="готово"),
    ):
        await service.handle(EMPLOYEE, ChatId(1), event)

    events = await AdminQueries(database).events(str(EMPLOYEE))
    assert "run_completed" in [event.name for event in events]


async def test_analytics_and_digest_follow_the_risk_audit(database: Database) -> None:
    service = build_service(
        database,
        messaging=RecordingMessaging(),
        knowledge=FakeKnowledgeBase(chunks=(scored_chunk(),)),
    )
    await service.start(EMPLOYEE, ChatId(1))
    audit = DatabaseAuditLog(database)
    await audit.record(
        "risk_assessed",
        employee_id=str(EMPLOYEE),
        step="week_two_survey",
        level="high",
        tags=["manager"],
        reasons=["конфликт с руководителем"],
        evidence=[{"source": "survey:difficulties", "text": "руководитель не отвечает"}],
    )
    await audit.record(
        "risk_assessed",
        employee_id=str(EMPLOYEE),
        step="day_three_survey",
        level="medium",
        tags=["access"],
        reasons=["доступ не выдали"],
    )
    await audit.record(
        "risk_assessed",
        employee_id=str(EMPLOYEE),
        step="day_three_survey",
        level="low",
        tags=[],
        reasons=[],
        evidence=[{"source": "survey:first_days_score", "text": "нет доступа к 1С"}],
    )
    queries = AdminQueries(database)

    overview = await queries.overview(
        recruiter_id="rec-1", department=None, since=datetime(2026, 10, 1, tzinfo=UTC)
    )

    assert (overview.active_runs, overview.completed_runs) == (1, 0)
    assert (overview.high_risk, overview.medium_risk) == (1, 1)
    assert dict(overview.top_tags) == {"access": 1, "manager": 1}

    digest = await queries.digest(
        recruiter_id="rec-1", department=None, since=datetime(2026, 10, 1, tzinfo=UTC)
    )
    assert [item.level for item in digest] == ["medium", "high"]
    assert digest[1].reasons == ("конфликт с руководителем",)
    assert digest[1].quote == "руководитель не отвечает"
    assert digest[0].quote == "нет доступа к 1С"

    assert (
        await queries.digest(
            recruiter_id="someone-else", department=None, since=datetime(2026, 10, 1, tzinfo=UTC)
        )
        == ()
    )
    by_department = await queries.digest(
        recruiter_id=None, department="ИТ", since=datetime(2026, 10, 1, tzinfo=UTC)
    )
    assert len(by_department) == 2


async def test_cron_pass_delivers_a_due_reminder(database: Database) -> None:
    messaging = RecordingMessaging()
    service = build_service(database, messaging=messaging, knowledge=FakeKnowledgeBase())
    await service.start(EMPLOYEE, ChatId(1))
    async with database.session() as session:
        await session.execute(text("UPDATE runs SET reminder_at = now() - interval '1 minute'"))
    direct = RecordingMessaging()
    runner = JobRunner(
        queue=JobQueue(database),
        service=service,
        clock=FrozenClock(NOW),
        audit=DatabaseAuditLog(database),
    )

    queued, handled, delivered = await tick_once(
        scheduler=ReminderScheduler(database),
        runner=runner,
        dispatcher=MessageDispatcher(database, direct),
    )

    assert (queued, handled, delivered) == (1, 1, 0)
    assert messaging.sent[-1].chat_id == ChatId(1)
    assert messaging.sent[-1].text.startswith("Напоминаем:")


async def test_uploaded_document_is_indexed_and_retrievable(database: Database) -> None:
    embedder = HashingEmbedder(dim=1024)
    text = """---
id: hr/uploaded-perk
title: Компенсация спорта
type: knowledge
status: active
owner: hr
audience: [all]
valid_from: 2026-01-01
---
## Спорт

Компания компенсирует занятия спортом до 15 000 рублей в год.
"""

    indexed = await ingest_document(
        text=text,
        source="upload",
        schema_path=ROOT / "docs" / "contracts" / "doc.schema.json",
        writer=PostgresKnowledgeWriter(database),
        embedder=embedder,
    )

    assert (indexed.id, indexed.chunks) == ("hr/uploaded-perk", 1)
    results = await PostgresKnowledgeBase(database, embedder).search(
        SearchQuery(
            text="компенсация спорта",
            audience=("all",),
            on_date=date(2026, 10, 23),
            limit=5,
        )
    )
    assert any(result.chunk.doc_id == "hr/uploaded-perk" for result in results)

    with pytest.raises(CorpusError):
        await ingest_document(
            text="---\nid: broken\n---\nbody",
            source="upload",
            schema_path=ROOT / "docs" / "contracts" / "doc.schema.json",
            writer=PostgresKnowledgeWriter(database),
            embedder=embedder,
        )

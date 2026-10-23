"""Integration: the adapters against a real Postgres with pgvector.

Skipped unless ``ONBOARDING_TEST_DATABASE`` points at a disposable database. The suite truncates
its tables, so never point it at anything you care about.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from onboarding.api.app import create_app
from onboarding.app.admin.actions import QuestionResolver
from onboarding.app.admin.queries import AdminQueries
from onboarding.app.clock import FrozenClock
from onboarding.app.copy import load_copy
from onboarding.app.db.blobs import PostgresBlobStore
from onboarding.app.db.directory import SqlDirectory
from onboarding.app.db.extractions import PostgresExtractionCache
from onboarding.app.db.kb import PostgresKnowledgeBase, PostgresKnowledgeWriter
from onboarding.app.db.models import (
    AuditRow,
    EmployeeRow,
    FileRow,
    JobRow,
    MessageRow,
    QuestionRow,
    RunRow,
)
from onboarding.app.db.outbox import MessageDispatcher, OutboxMessaging
from onboarding.app.db.queue import JobQueue
from onboarding.app.db.repos import (
    DatabaseAuditLog,
    DatabaseQuestionLog,
    DatabaseRunRepository,
    RunAlreadyActiveError,
    SqlEventDeduper,
)
from onboarding.app.db.retention import RetentionPurger
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
from onboarding.ports import ExtractionRecord, OutboundMessage, SearchQuery, StoredRun
from tests.files import digital_pdf

from .fakes import (
    EMPLOYEE,
    NOW,
    FakeKnowledgeBase,
    RecordingMessaging,
    ScriptedLLM,
    scored_chunk,
)
from .test_jobs import StubExtractor

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
                "kb_chunks, kb_documents, kb_files, kb_extractions RESTART IDENTITY CASCADE"
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

    message_id = await outbox.send(
        OutboundMessage(chat_id=ChatId(7), text="привет", image="welcome.jpg")
    )

    assert message_id.isdigit()
    assert direct.sent == []
    delivered = await MessageDispatcher(database, direct).run_once()
    assert delivered == 1
    assert direct.sent[0].text == "привет"
    assert direct.sent[0].image == "welcome.jpg"


async def test_dispatcher_reclaims_a_message_abandoned_mid_send(database: Database) -> None:
    direct = RecordingMessaging()
    abandoned = datetime.now(UTC) - timedelta(minutes=5)
    async with database.session() as session:
        session.add(
            MessageRow(
                chat_id=7,
                text="после падения воркера",
                status="sending",
                available_at=abandoned,
            )
        )

    delivered = await MessageDispatcher(database, direct).run_once()

    assert delivered == 1
    assert direct.sent[0].text == "после падения воркера"
    async with database.session() as session:
        row = await session.scalar(select(MessageRow))
        assert row is not None
        assert row.status == "sent"


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
        extractor=StubExtractor(),  # type: ignore[arg-type]
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


def admin_app() -> FastAPI:
    return create_app(
        Settings(
            _env_file=None,
            database_url=database_url(),
            embed_provider="hashing",
            admin_tokens_raw=(
                "rec:recruiter:rec-1,other:recruiter:rec-2,mgr:manager:ИТ,"
                "hr:hr_admin:hr-1,expired:hr_admin:hr-1:2020-01-01"
            ),
        )
    )


async def seed_question(database: Database, text_value: str = "Сколько дней отпуска?") -> int:
    log = DatabaseQuestionLog(database)
    await log.record_question(
        employee_id=EMPLOYEE,
        chat_id=ChatId(1),
        text=text_value,
        answered=False,
        reason="no_sources",
        citations=(),
        latency_ms=None,
    )
    async with database.session() as session:
        value = await session.scalar(select(func.max(QuestionRow.id)))
    return int(value or 0)


async def test_admin_resolves_a_question_and_queues_the_reply(database: Database) -> None:
    question_id = await seed_question(database)
    app = admin_app()
    async with (
        app.router.lifespan_context(app),  # type: ignore[attr-defined]
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as http,
    ):
            response = await http.post(
                f"/admin/api/questions/{question_id}/resolve",
                json={"text": "Отпуск — 28 дней, заявление за 14 дней."},
                headers={"Authorization": "Bearer rec"},
            )
            assert response.status_code == 200, response.text
            body = response.json()
            assert body["id"] == question_id
            assert body["answered"] is True
            assert body["resolved_by"] == "rec-1"

            second = await http.post(
                f"/admin/api/questions/{question_id}/resolve",
                json={"text": "Повтор"},
                headers={"Authorization": "Bearer rec"},
            )
            assert second.status_code == 409

            foreign = await http.post(
                f"/admin/api/questions/{question_id}/resolve",
                json={"text": "Чужой"},
                headers={"Authorization": "Bearer other"},
            )
            assert foreign.status_code == 404

            empty = await http.post(
                f"/admin/api/questions/{question_id}/resolve",
                json={"text": "   "},
                headers={"Authorization": "Bearer rec"},
            )
            assert empty.status_code == 422

    async with database.session() as session:
        question = await session.get(QuestionRow, question_id)
        assert question is not None
        assert question.answered
        assert question.resolved_by == "rec-1"
        assert question.resolution == "Отпуск — 28 дней, заявление за 14 дней."
        reply = await session.scalar(
            select(MessageRow).where(MessageRow.chat_id == 1)
        )
        assert reply is not None
        assert reply.status == "pending"
        audit = await session.scalar(
            select(AuditRow).where(AuditRow.name == "question_resolved")
        )
        assert audit is not None
        assert audit.fields["question_id"] == question_id
        assert "text" not in audit.fields


async def test_manager_scope_and_expired_token(database: Database) -> None:
    question_id = await seed_question(database)
    app = admin_app()
    async with (
        app.router.lifespan_context(app),  # type: ignore[attr-defined]
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as http,
    ):
            expired = await http.get(
                "/admin/api/questions", headers={"Authorization": "Bearer expired"}
            )
            assert expired.status_code == 401

            anonymous = await http.get("/admin/api/questions")
            assert anonymous.status_code == 401

            manager = await http.post(
                f"/admin/api/questions/{question_id}/resolve",
                json={"text": "Ответ руководителя отдела."},
                headers={"Authorization": "Bearer mgr"},
            )
            assert manager.status_code == 200, manager.text


async def test_hr_offboards_an_employee_and_purges_the_transcript(database: Database) -> None:
    service = build_service(
        database, messaging=RecordingMessaging(), knowledge=FakeKnowledgeBase()
    )
    await service.start(EMPLOYEE, ChatId(1))
    await seed_question(database)
    async with database.session() as session:
        session.add(MessageRow(chat_id=1, text="Напоминание, которое уже не нужно"))

    app = admin_app()
    async with (
        app.router.lifespan_context(app),  # type: ignore[attr-defined]
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as http,
    ):
            refused = await http.delete(
                f"/admin/api/employees/{EMPLOYEE}", headers={"Authorization": "Bearer rec"}
            )
            assert refused.status_code == 403

            removed = await http.delete(
                f"/admin/api/employees/{EMPLOYEE}", headers={"Authorization": "Bearer hr"}
            )
            assert removed.status_code == 200, removed.text
            body = removed.json()
            assert body["employee_id"] == str(EMPLOYEE)
            assert body["questions_deleted"] == 1
            assert body["messages_deleted"] == 1
            assert body["runs_closed"] == 1

            again = await http.delete(
                f"/admin/api/employees/{EMPLOYEE}", headers={"Authorization": "Bearer hr"}
            )
            assert again.status_code == 200
            assert again.json()["questions_deleted"] == 0
            assert again.json()["messages_deleted"] == 0

    async with database.session() as session:
        employee = await session.get(EmployeeRow, str(EMPLOYEE))
        assert employee is not None
        assert employee.status == "left"
        assert employee.left_at is not None
        run = await session.scalar(select(RunRow).where(RunRow.employee_id == str(EMPLOYEE)))
        assert run is not None
        assert run.status == "completed"
        assert await session.scalar(select(func.count()).select_from(QuestionRow)) == 0
        assert await session.scalar(select(func.count()).select_from(MessageRow)) == 0

    assert await SqlDirectory(database).profile(EMPLOYEE) is None


async def test_retention_purges_old_questions_and_redacts_audit(database: Database) -> None:
    old = NOW - timedelta(days=400)
    async with database.session() as session:
        session.add(
            QuestionRow(
                employee_id=str(EMPLOYEE),
                chat_id=1,
                text="старый вопрос",
                answered=True,
                reason="answered",
                asked_at=old,
            )
        )
        session.add(
            QuestionRow(
                employee_id=str(EMPLOYEE),
                chat_id=1,
                text="свежий вопрос",
                answered=False,
                reason="no_sources",
            )
        )
        session.add(
            AuditRow(
                name="risk_assessed",
                at=old,
                fields={
                    "employee_id": str(EMPLOYEE),
                    "level": "high",
                    "evidence": [{"text": "личное"}],
                },
            )
        )
        session.add(
            FileRow(
                id="0" * 64,
                filename="old-scan.pdf",
                media_type="application/pdf",
                size=4,
                content=b"old!",
                created_at=old,
            )
        )
        session.add(
            FileRow(
                id="1" * 64,
                filename="fresh-scan.pdf",
                media_type="application/pdf",
                size=5,
                content=b"fresh",
            )
        )
        session.add_all(
            [
                MessageRow(
                    chat_id=1,
                    text="старое доставленное",
                    status="sent",
                    created_at=old,
                    sent_at=old,
                ),
                MessageRow(
                    chat_id=1,
                    text="старое в очереди",
                    status="pending",
                    created_at=old,
                    available_at=old,
                ),
                MessageRow(
                    chat_id=1,
                    text="старое зависшее",
                    status="sending",
                    created_at=old,
                    available_at=old,
                ),
                MessageRow(chat_id=1, text="свежее в очереди", status="pending"),
            ]
        )

    result = await RetentionPurger(
        database, FrozenClock(NOW), days=365
    ).run_once()

    assert result.questions_deleted == 1
    assert result.files_deleted == 1
    assert result.messages_deleted == 3
    assert result.audit_redacted == 1
    async with database.session() as session:
        names = list(await session.scalars(select(FileRow.filename)))
    assert names == ["fresh-scan.pdf"]
    async with database.session() as session:
        texts = list(await session.scalars(select(QuestionRow.text)))
        assert texts == ["свежий вопрос"]
        queued = list(await session.scalars(select(MessageRow.text)))
        assert queued == ["свежее в очереди"]
        audit = await session.scalar(
            select(AuditRow).where(AuditRow.name == "risk_assessed")
        )
        assert audit is not None
        assert "evidence" not in audit.fields
        assert audit.fields["redacted"] is True
        assert audit.fields["level"] == "high"
        purged = await session.scalar(
            select(AuditRow).where(AuditRow.name == "retention_purged")
        )
        assert purged is not None
        assert purged.fields["messages_deleted"] == 3


async def test_question_resolver_uses_the_scope_and_the_outbox(database: Database) -> None:
    question_id = await seed_question(database)
    resolver = QuestionResolver(database, FrozenClock(NOW))

    with pytest.raises(Exception, match="not found"):
        await resolver.resolve(
            question_id,
            text="Чужой ответ",
            actor="rec-2",
            recruiter_id="rec-2",
            department=None,
        )

    resolution = await resolver.resolve(
        question_id,
        text="Ответ",
        actor="rec-1",
        recruiter_id="rec-1",
        department=None,
    )

    assert resolution.question_id == question_id
    async with database.session() as session:
        assert await session.scalar(select(func.count()).select_from(MessageRow)) == 1


async def test_an_uploaded_file_is_addressed_by_its_content(database: Database) -> None:
    blobs = PostgresBlobStore(database)
    content = b"%PDF-1.4 the same bytes twice"

    first = await blobs.put(content, filename="Регламент.pdf", media_type="application/pdf")
    second = await blobs.put(content, filename="reglament.pdf", media_type="application/pdf")

    assert first == second
    assert await blobs.read(first) == content
    assert await blobs.read("0" * 64) is None


async def test_a_filename_cannot_escape_the_storage(database: Database) -> None:
    blobs = PostgresBlobStore(database)

    blob_id = await blobs.put(
        b"%PDF-1.4 traversal", filename="../../etc/passwd", media_type="application/pdf"
    )

    assert await blobs.read(blob_id) is not None


async def test_the_extraction_cache_is_keyed_by_file_and_profile(database: Database) -> None:
    cache = PostgresExtractionCache(database)
    record = ExtractionRecord(
        content_hash="a" * 64,
        profile_hash="p1",
        status="indexed",
        reason=None,
        engine="pdfium",
        route="native_text",
        pages=2,
        min_confidence=1.0,
        markdown="---\nid: hr/x\n---\n\nbody\n",
        document_id="hr/x",
    )

    await cache.save(record)
    assert await cache.load("a" * 64, "p1") == record
    assert await cache.load("a" * 64, "p2") is None

    await cache.save(
        ExtractionRecord(
            content_hash="a" * 64,
            profile_hash="p2",
            status="rejected",
            reason="low_confidence",
            engine="rapidocr",
            route="ocr",
            pages=0,
            min_confidence=0.0,
        )
    )
    latest = await cache.load_latest("a" * 64)
    assert latest is not None
    assert latest.profile_hash == "p2"
    assert latest.reason == "low_confidence"


async def test_hr_uploads_a_pdf_and_the_extraction_job_is_queued(database: Database) -> None:
    app = admin_app()
    async with (
        app.router.lifespan_context(app),  # type: ignore[attr-defined]
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as http,
    ):
        response = await http.post(
            "/admin/api/knowledge/files",
            files={
                "file": (
                    "reglament.pdf",
                    digital_pdf(
                        ["Internal regulations, page one, a long enough text layer to trust"]
                    ),
                    "application/pdf",
                )
            },
            data={
                "metadata": json.dumps(
                    {
                        "id": "hr/uploaded",
                        "title": "Регламент",
                        "type": "knowledge",
                        "status": "active",
                        "owner": "hr-team",
                        "audience": ["all"],
                        "valid_from": "2026-01-01",
                    }
                )
            },
            headers={"Authorization": "Bearer hr"},
        )
        assert response.status_code == 202, response.text
        blob_id = response.json()["content_hash"]

        async with database.session() as session:
            queued = await session.scalar(
                select(JobRow).where(JobRow.kind == "extract_document")
            )
        assert queued is not None
        assert queued.payload["blob_id"] == blob_id
        assert queued.payload["metadata"]["owner"] == "hr-team"

        pending = await http.get(
            f"/admin/api/knowledge/files/{blob_id}", headers={"Authorization": "Bearer hr"}
        )
        assert pending.status_code == 404

        await PostgresExtractionCache(database).save(
            ExtractionRecord(
                content_hash=blob_id,
                profile_hash="p1",
                status="indexed",
                reason=None,
                engine="pdfium",
                route="native_text",
                pages=1,
                min_confidence=1.0,
                document_id="hr/uploaded",
            )
        )
        done = await http.get(
            f"/admin/api/knowledge/files/{blob_id}", headers={"Authorization": "Bearer hr"}
        )

    assert done.status_code == 200
    assert done.json()["status"] == "indexed"
    assert done.json()["document_id"] == "hr/uploaded"


async def test_only_hr_may_upload_a_file(database: Database) -> None:
    app = admin_app()
    async with (
        app.router.lifespan_context(app),  # type: ignore[attr-defined]
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as http,
    ):
        response = await http.post(
            "/admin/api/knowledge/files",
            files={"file": ("a.pdf", b"%PDF-1.4 x", "application/pdf")},
            data={"metadata": "{}"},
            headers={"Authorization": "Bearer rec"},
        )

    assert response.status_code == 403


async def test_knowledge_list_hides_hr_only_from_a_recruiter(database: Database) -> None:
    embedder = HashingEmbedder(dim=1024)
    await ingest(
        directory=ROOT / "knowledge",
        schema_path=ROOT / "docs" / "contracts" / "doc.schema.json",
        writer=PostgresKnowledgeWriter(database),
        embedder=embedder,
    )
    queries = AdminQueries(database)

    recruiter = await queries.knowledge(limit=200, include_hr_only=False)
    hr = await queries.knowledge(limit=200, include_hr_only=True)

    assert any("hr_only" in record.audience for record in hr)
    assert all("hr_only" not in record.audience for record in recruiter)
    assert len(recruiter) < len(hr)

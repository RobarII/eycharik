"""Integration: the adapters against a real Postgres with pgvector.

Skipped unless ``ONBOARDING_TEST_DATABASE`` points at a disposable database. The suite truncates
its tables, so never point it at anything you care about.
"""

from __future__ import annotations

import hashlib
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
from onboarding.app.admin.actions import EmployeeOffboarder, QuestionResolver
from onboarding.app.admin.queries import AdminQueries
from onboarding.app.audit import NullAudit
from onboarding.app.channels.profiles import ChannelProfileLibrary
from onboarding.app.clock import FrozenClock
from onboarding.app.copy import load_copy
from onboarding.app.db.blobs import PostgresBlobStore
from onboarding.app.db.directory import SqlDirectory
from onboarding.app.db.extractions import PostgresExtractionCache
from onboarding.app.db.kb import (
    PostgresKnowledgeBase,
    PostgresKnowledgeWriter,
    _lexical_ids,
    _lexical_query,
)
from onboarding.app.db.models import (
    AuditRow,
    ChannelIdentityRow,
    ChunkRow,
    DocumentRow,
    EmployeeRow,
    ExtractionRow,
    FileRow,
    InboundFileRow,
    IndexStateRow,
    JobRow,
    MessageRow,
    QuestionRow,
    RunRow,
)
from onboarding.app.db.outbox import MessageDispatcher, OutboxMessaging
from onboarding.app.db.predicates import acl_clause
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
from onboarding.app.files.crypto import decrypt
from onboarding.app.files.intake import InboundFileIntake
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
from onboarding.core.access import holds, predicates, subject_of
from onboarding.core.models import (
    Action,
    ActionKind,
    Address,
    Channel,
    ChatId,
    DocId,
    Document,
    EmployeeId,
    Event,
    EventKind,
    RunId,
    ScheduleReminder,
    StepState,
    SurveyAnswer,
    TimeoutAction,
)
from onboarding.core.retrieval import RetrievalPolicy
from onboarding.core.transitions import start as start_run
from onboarding.ports import (
    ExtractionRecord,
    InboundFile,
    KnowledgeUnavailableError,
    OutboundMessage,
    SearchQuery,
    StoredRun,
)
from tests.files import digital_pdf

from .fakes import (
    EMPLOYEE,
    NOW,
    FakeKnowledgeBase,
    RecordingMessaging,
    ScriptedLLM,
    scored_chunk,
)
from .test_jobs import StubExtractor, StubFiles, StubIndexer

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[3]
SCENARIOS = ROOT / "apps" / "api" / "onboarding" / "scenarios"
# The shipped profiles, so the outbox splits text exactly as a deployment would.
PROFILES = ChannelProfileLibrary(
    ROOT / "apps" / "api" / "channel-profiles",
    ROOT / "docs" / "contracts" / "channel-profile.schema.json",
).load_all()
MAX = Address(channel=Channel.MAX, chat_id=ChatId(1))
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
                "channel_identities, inbound_files, "
                "kb_chunks, kb_documents, kb_files, kb_extractions, kb_index_state "
                "RESTART IDENTITY CASCADE"
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

    result = await service.start(EMPLOYEE, MAX)

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
    await runs.create(
        StoredRun(
            state=state,
            reminder=ScheduleReminder(
                due_at=NOW, step_id="week_two_check", action=TimeoutAction.REMIND
            ),
            address=MAX,
        )
    )

    loaded = await runs.load(state.run_id)

    assert loaded is not None
    assert loaded.state.answers == (SurveyAnswer(question_id="manager", score=6),)
    assert loaded.state.question_index == 1
    assert loaded.state.pending_reason == "manager"


async def test_a_second_start_reuses_the_active_run(database: Database) -> None:
    messaging = RecordingMessaging()
    service = build_service(database, messaging=messaging, knowledge=FakeKnowledgeBase())

    first = await service.start(EMPLOYEE, MAX)
    second = await service.start(EMPLOYEE, MAX)

    # The partial index still forbids two active runs; the second start replays the current step
    # instead of creating a run, so exactly one message is added on top of the initial pair.
    assert first.handled
    assert second.handled
    assert len(messaging.sent) == 3


async def test_event_deduper_accepts_one_delivery(database: Database) -> None:
    async with database.session() as session:
        deduper = SqlEventDeduper(session)
        assert await deduper.first_sighting("mid-1")
        assert not await deduper.first_sighting("mid-1")


async def test_outbox_and_dispatcher_deliver_a_message(database: Database) -> None:
    direct = RecordingMessaging()
    outbox = OutboxMessaging(database, {Channel.MAX: direct}, PROFILES)

    message_id = await outbox.send(OutboundMessage(address=MAX, text="привет"))

    assert message_id.isdigit()
    assert direct.sent == []
    delivered = await MessageDispatcher(database, {Channel.MAX: direct}).run_once()
    assert delivered == 1
    assert direct.sent[0].text == "привет"
    assert direct.sent[0].address == MAX


async def test_dispatcher_reclaims_a_message_abandoned_mid_send(database: Database) -> None:
    direct = RecordingMessaging()
    abandoned = datetime.now(UTC) - timedelta(minutes=5)
    async with database.session() as session:
        session.add(
            MessageRow(
                channel="max",
                chat_id=7,
                text="после падения воркера",
                status="sending",
                available_at=abandoned,
            )
        )

    delivered = await MessageDispatcher(database, {Channel.MAX: direct}).run_once()

    assert delivered == 1
    assert direct.sent[0].text == "после падения воркера"
    async with database.session() as session:
        row = await session.scalar(select(MessageRow))
        assert row is not None
        assert row.status == "sent"


async def test_scheduler_enqueues_a_due_reminder(database: Database) -> None:
    service = build_service(database, messaging=RecordingMessaging(), knowledge=FakeKnowledgeBase())
    await service.start(EMPLOYEE, MAX)
    async with database.session() as session:
        await session.execute(text("UPDATE runs SET reminder_at = now() - interval '1 minute'"))

    assert await ReminderScheduler(database).tick() == 1
    jobs = await JobQueue(database).claim()
    assert [job.kind for job in jobs] == ["timeout"]
    assert jobs[0].payload["employee_id"] == str(EMPLOYEE)


async def test_scheduler_enqueues_a_delayed_step(database: Database) -> None:
    service = build_service(database, messaging=RecordingMessaging(), knowledge=FakeKnowledgeBase())
    await service.start(EMPLOYEE, MAX)
    async with database.session() as session:
        await session.execute(
            text(
                "UPDATE runs SET reminder_at = NULL, next_send_at = now() - interval '1 minute', "
                "next_send_step = 'day_before'"
            )
        )

    assert await ReminderScheduler(database).tick() == 1
    jobs = await JobQueue(database).claim()
    assert [job.kind for job in jobs] == ["send_step"]
    assert jobs[0].payload["run_id"]
    assert jobs[0].payload["step_id"] == "day_before"


async def test_transition_is_persisted(database: Database) -> None:
    messaging = RecordingMessaging()
    service = build_service(database, messaging=messaging, knowledge=FakeKnowledgeBase())
    await service.start(EMPLOYEE, MAX)

    result = await service.handle(
        EMPLOYEE,
        MAX,
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
    outbox = OutboxMessaging(database, {Channel.MAX: direct}, PROFILES)
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
            address=MAX,
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


async def test_a_search_refuses_an_index_built_by_another_embedder(
    database: Database,
) -> None:
    """A model swap without a reindex answers every question wrongly and fails none.

    The recorded fingerprint is what turns that silence into a refusal a human can act on.
    """
    await ingest(
        directory=ROOT / "knowledge",
        schema_path=ROOT / "docs" / "contracts" / "doc.schema.json",
        writer=PostgresKnowledgeWriter(database, HashingEmbedder(dim=1024)),
        embedder=HashingEmbedder(dim=1024),
    )
    async with database.session() as session:
        state = await session.get(IndexStateRow, "active")
        assert state is not None
        state.embedder = "some-other-model@1024"

    with pytest.raises(KnowledgeUnavailableError, match="reindex before serving answers"):
        await PostgresKnowledgeBase(database, HashingEmbedder(dim=1024)).search(
            SearchQuery(
                text="сколько дней отпуска",
                audience=("all",),
                on_date=date(2026, 10, 23),
                limit=5,
            )
        )


async def test_a_search_refuses_a_vector_width_the_index_does_not_have(
    database: Database,
) -> None:
    """An embedder without a fingerprint still has a width, and the column is the only witness."""

    class WidthOnlyEmbedder:
        dim = 768

        async def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
            return tuple((1.0,) * 768 for _ in texts)

    await ingest(
        directory=ROOT / "knowledge",
        schema_path=ROOT / "docs" / "contracts" / "doc.schema.json",
        writer=PostgresKnowledgeWriter(database, HashingEmbedder(dim=1024)),
        embedder=HashingEmbedder(dim=1024),
    )
    async with database.session() as session:
        state = await session.get(IndexStateRow, "active")
        assert state is not None
        state.embedder = ""

    with pytest.raises(KnowledgeUnavailableError, match="this process embeds 768"):
        await PostgresKnowledgeBase(database, WidthOnlyEmbedder()).search(
            SearchQuery(
                text="сколько дней отпуска",
                audience=("all",),
                on_date=date(2026, 10, 23),
                limit=5,
            )
        )


async def test_lexical_branch_survives_a_question_phrased_as_a_question(
    database: Database,
) -> None:
    """The lexical list must not be empty for a question an employee would actually ask.

    ``plainto_tsquery`` joins every lexeme with AND, so «Сколько дней отпуска положено в первый
    год?» demanded one chunk containing «скольк», «полож» and «год» as well. The shipped corpus
    satisfied it for 25 of 137 golden questions; for the rest the fusion ranked on the vector list
    alone and the lexical half of ADR 0003 did not exist in production.
    """
    await ingest(
        directory=ROOT / "knowledge",
        schema_path=ROOT / "docs" / "contracts" / "doc.schema.json",
        writer=PostgresKnowledgeWriter(database),
        embedder=HashingEmbedder(dim=1024),
    )
    query = SearchQuery(
        text="Сколько дней отпуска положено в первый год?",
        audience=("all", "dept:it"),
        on_date=date(2026, 10, 23),
        limit=30,
    )

    async with database.session() as session:
        ids = await _lexical_ids(session, query, RetrievalPolicy(), 30)

    assert ids, "the lexical branch returned nothing for a natural question"
    assert any(str(chunk_id).startswith("hr/leave-policy#") for chunk_id in ids)


async def test_the_lexical_branch_does_not_answer_with_one_shared_word(
    database: Database,
) -> None:
    """One matching word is not evidence, and a list built on it displaces better answers.

    Ungated, the OR query returned the whole corpus for «Сколько дней отпуска положено в первый
    год?» — every document that mentions a day or a year — and at equal fusion weight that
    ordering cost 0.015 recall. The gate asks for ``min(3, n)`` of the question's lexemes.
    """
    await ingest(
        directory=ROOT / "knowledge",
        schema_path=ROOT / "docs" / "contracts" / "doc.schema.json",
        writer=PostgresKnowledgeWriter(database),
        embedder=HashingEmbedder(dim=1024),
    )
    query = SearchQuery(
        text="Сколько дней отпуска положено в первый год?",
        audience=("all", "dept:it"),
        on_date=date(2026, 10, 23),
        limit=30,
    )

    async with database.session() as session:
        ids = await _lexical_ids(session, query, RetrievalPolicy(), 30)
        loose = (
            (
                await session.execute(
                    select(ChunkRow.id).where(ChunkRow.ts.op("@@")(_lexical_query(query.text)))
                )
            )
            .scalars()
            .all()
        )

    assert len(ids) < len(loose), "the gate did not narrow the ungated OR list"
    assert str(ids[0]).startswith("hr/leave-policy#"), "the best-covered chunk must rank first"


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
            StoredRun(state=transition.state, reminder=transition.reminder, address=MAX)
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
    await repository.create(StoredRun(state=first.state, reminder=first.reminder, address=MAX))

    second = start_run(
        scenario,
        RunId("00000000-0000-4000-8000-000000000502"),
        EMPLOYEE,
        NOW,
    )
    with pytest.raises(RunAlreadyActiveError):
        await repository.create(
            StoredRun(state=second.state, reminder=second.reminder, address=MAX)
        )


async def test_completion_is_attached_to_the_employee(database: Database) -> None:
    service = build_service(database, messaging=RecordingMessaging(), knowledge=FakeKnowledgeBase())
    await service.start(EMPLOYEE, MAX)

    for event in (
        Event(kind=EventKind.BUTTON_PRESSED, at=NOW, button_id="checklist_done"),
        Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="готово"),
        Event(kind=EventKind.FILE_RECEIVED, at=NOW, file_id="file-1"),
        Event(kind=EventKind.MESSAGE_RECEIVED, at=NOW, text="готово"),
    ):
        await service.handle(EMPLOYEE, MAX, event)

    events = await AdminQueries(database).events(str(EMPLOYEE))
    assert "run_completed" in [event.name for event in events]


async def test_analytics_and_digest_follow_the_risk_audit(database: Database) -> None:
    service = build_service(
        database,
        messaging=RecordingMessaging(),
        knowledge=FakeKnowledgeBase(chunks=(scored_chunk(),)),
    )
    await service.start(EMPLOYEE, MAX)
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
    await service.start(EMPLOYEE, MAX)
    async with database.session() as session:
        await session.execute(text("UPDATE runs SET reminder_at = now() - interval '1 minute'"))
    direct = RecordingMessaging()
    runner = JobRunner(
        queue=JobQueue(database),
        service=service,
        clock=FrozenClock(NOW),
        audit=DatabaseAuditLog(database),
        extractor=StubExtractor(),  # type: ignore[arg-type]
        indexer=StubIndexer(),  # type: ignore[arg-type]
        files=StubFiles(),  # type: ignore[arg-type]
    )

    queued, handled, delivered = await tick_once(
        scheduler=ReminderScheduler(database),
        runner=runner,
        dispatcher=MessageDispatcher(database, {Channel.MAX: direct}),
    )

    assert (queued, handled, delivered) == (1, 1, 0)
    assert messaging.sent[-1].address == MAX
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
        address=MAX,
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
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http,
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
        reply = await session.scalar(select(MessageRow).where(MessageRow.chat_id == 1))
        assert reply is not None
        assert reply.status == "pending"
        assert reply.text.startswith("HR ответил на ваш вопрос:")
        assert "«" in reply.text
        assert reply.keyboard[0][0]["id"] == "hr_continue"
        audit = await session.scalar(select(AuditRow).where(AuditRow.name == "question_resolved"))
        assert audit is not None
        assert audit.fields["question_id"] == question_id
        assert "text" not in audit.fields


async def test_admin_declines_a_question_without_a_reply(database: Database) -> None:
    question_id = await seed_question(database, "ыыы")
    app = admin_app()
    async with (
        app.router.lifespan_context(app),  # type: ignore[attr-defined]
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http,
    ):
        response = await http.post(
            f"/admin/api/questions/{question_id}/decline",
            headers={"Authorization": "Bearer rec"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["id"] == question_id
        assert body["declined"] is True
        assert body["answered"] is True
        assert body["resolved_by"] == "rec-1"

        second = await http.post(
            f"/admin/api/questions/{question_id}/decline",
            headers={"Authorization": "Bearer rec"},
        )
        assert second.status_code == 409

        foreign = await http.post(
            f"/admin/api/questions/{question_id}/decline",
            headers={"Authorization": "Bearer other"},
        )
        assert foreign.status_code == 404

        answered = await http.get(
            "/admin/api/questions?status=answered",
            headers={"Authorization": "Bearer rec"},
        )
        assert answered.status_code == 200, answered.text
        card = next(item for item in answered.json()["items"] if item["id"] == question_id)
        assert card["declined"] is True

    async with database.session() as session:
        question = await session.get(QuestionRow, question_id)
        assert question is not None
        assert question.answered
        assert question.declined
        assert question.resolution is None
        assert await session.scalar(select(func.count()).select_from(MessageRow)) == 0
        audit = await session.scalar(select(AuditRow).where(AuditRow.name == "question_declined"))
        assert audit is not None
        assert audit.fields["question_id"] == question_id
        assert audit.fields["by"] == "rec-1"


async def test_manager_scope_and_expired_token(database: Database) -> None:
    question_id = await seed_question(database)
    app = admin_app()
    async with (
        app.router.lifespan_context(app),  # type: ignore[attr-defined]
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http,
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
    service = build_service(database, messaging=RecordingMessaging(), knowledge=FakeKnowledgeBase())
    await service.start(EMPLOYEE, MAX)
    await seed_question(database)
    async with database.session() as session:
        session.add(MessageRow(chat_id=1, text="Напоминание, которое уже не нужно"))

    app = admin_app()
    async with (
        app.router.lifespan_context(app),  # type: ignore[attr-defined]
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http,
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
                MessageRow(channel="max", chat_id=1, text="свежее в очереди", status="pending"),
            ]
        )

    result = await RetentionPurger(database, FrozenClock(NOW), days=365).run_once()

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
        audit = await session.scalar(select(AuditRow).where(AuditRow.name == "risk_assessed"))
        assert audit is not None
        assert "evidence" not in audit.fields
        assert audit.fields["redacted"] is True
        assert audit.fields["level"] == "high"
        purged = await session.scalar(select(AuditRow).where(AuditRow.name == "retention_purged"))
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
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http,
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
            queued = await session.scalar(select(JobRow).where(JobRow.kind == "extract_document"))
        assert queued is not None
        assert queued.payload["blob_id"] == blob_id
        assert queued.payload["metadata"]["owner"] == "hr-team"

        pending = await http.get(
            f"/admin/api/knowledge/files/{blob_id}", headers={"Authorization": "Bearer hr"}
        )
        assert pending.status_code == 200
        assert pending.json()["status"] == "queued"

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


async def test_hr_uploads_markdown_and_the_index_job_is_queued(database: Database) -> None:
    app = admin_app()
    text = """---
id: hr/async-perk
title: Асинхронная компенсация
type: knowledge
status: active
owner: hr
audience: [all]
valid_from: 2026-01-01
---
## Спорт

Компания компенсирует занятия спортом.
"""
    async with (
        app.router.lifespan_context(app),  # type: ignore[attr-defined]
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http,
    ):
        response = await http.post(
            "/admin/api/knowledge",
            json={"text": text},
            headers={"Authorization": "Bearer hr"},
        )
        assert response.status_code == 202, response.text
        queued = response.json()
        assert queued["status"] == "queued"

        async with database.session() as session:
            job = await session.scalar(select(JobRow).where(JobRow.kind == "index_document"))
            extraction = await session.scalar(
                select(ExtractionRow).where(ExtractionRow.content_hash == queued["content_hash"])
            )
        assert job is not None
        assert extraction is not None
        assert extraction.status == "queued"

        status = await http.get(
            f"/admin/api/knowledge/files/{queued['content_hash']}",
            headers={"Authorization": "Bearer hr"},
        )

    assert status.status_code == 200
    assert status.json()["status"] == "queued"


async def test_only_hr_may_upload_a_file(database: Database) -> None:
    app = admin_app()
    async with (
        app.router.lifespan_context(app),  # type: ignore[attr-defined]
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http,
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


def channel_app() -> FastAPI:
    """An app with two channels on: MAX and Telegram, each with its own secret."""
    return create_app(
        Settings(
            _env_file=None,
            database_url=database_url(),
            embed_provider="hashing",
            channels_raw="max,telegram",
            max_webhook_secret="max-secret",
            telegram_webhook_secret="tg-secret",
        )
    )


def telegram_update(update_id: int = 100, text_value: str = "Сколько дней отпуска?") -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "date": int(NOW.timestamp()),
            "chat": {"id": 555, "type": "private"},
            "from": {"id": 222, "is_bot": False, "first_name": "Аня"},
            "text": text_value,
        },
    }


TELEGRAM_HEADERS = {"X-Telegram-Bot-Api-Secret-Token": "tg-secret"}


async def jobs(database: Database) -> list[JobRow]:
    async with database.session() as session:
        return list(await session.scalars(select(JobRow).order_by(JobRow.id)))


async def test_an_unlinked_account_is_acknowledged_and_audited(database: Database) -> None:
    app = channel_app()
    async with (
        app.router.lifespan_context(app),  # type: ignore[attr-defined]
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http,
    ):
        response = await http.post(
            "/webhook/telegram", json=telegram_update(), headers=TELEGRAM_HEADERS
        )

    assert response.status_code == 200
    assert response.text == "ok"
    assert await jobs(database) == []
    async with database.session() as session:
        audited = await session.scalar(
            select(AuditRow).where(AuditRow.name == "unlinked_channel_user")
        )
    assert audited is not None
    assert audited.fields["channel"] == "telegram"
    assert audited.fields["chat_id"] == 555
    assert audited.fields["external_id"] == "222"


async def test_a_linked_account_reaches_the_queue_once(database: Database) -> None:
    linked = await SqlDirectory(database).link(Channel.TELEGRAM, "222", EMPLOYEE)
    assert linked
    app = channel_app()
    async with (
        app.router.lifespan_context(app),  # type: ignore[attr-defined]
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http,
    ):
        first = await http.post(
            "/webhook/telegram", json=telegram_update(), headers=TELEGRAM_HEADERS
        )
        repeat = await http.post(
            "/webhook/telegram", json=telegram_update(), headers=TELEGRAM_HEADERS
        )

    assert (first.status_code, repeat.status_code) == (200, 200)
    queued = await jobs(database)
    assert [job.kind for job in queued] == ["message"]
    assert queued[0].payload["employee_id"] == str(EMPLOYEE)
    assert queued[0].payload["channel"] == "telegram"
    assert queued[0].payload["chat_id"] == 555
    assert queued[0].payload["event"]["kind"] == "message_received"


async def test_a_first_contact_queues_a_start_not_a_message(database: Database) -> None:
    await SqlDirectory(database).link(Channel.TELEGRAM, "222", EMPLOYEE)
    app = channel_app()
    async with (
        app.router.lifespan_context(app),  # type: ignore[attr-defined]
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http,
    ):
        response = await http.post(
            "/webhook/telegram",
            json=telegram_update(101, "/start"),
            headers=TELEGRAM_HEADERS,
        )

    assert response.status_code == 200
    assert [job.kind for job in await jobs(database)] == ["start"]


async def test_a_backfilled_max_link_still_starts_a_run(database: Database) -> None:
    """The migration links every existing employee to their MAX user id, so nothing breaks."""
    async with database.session() as session:
        session.add(ChannelIdentityRow(channel="max", external_id="222", employee_id=str(EMPLOYEE)))
    app = channel_app()
    body = {
        "update_type": "bot_started",
        "timestamp": 1_760_000_000_000,
        "chat_id": 1,
        "user": {"user_id": 222},
    }
    async with (
        app.router.lifespan_context(app),  # type: ignore[attr-defined]
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http,
    ):
        response = await http.post(
            "/webhook/max", json=body, headers={"X-Max-Bot-Api-Secret": "max-secret"}
        )

    assert response.status_code == 200
    queued = await jobs(database)
    assert [job.kind for job in queued] == ["start"]
    assert queued[0].payload["channel"] == "max"


async def test_the_webhook_rejects_a_wrong_secret_and_an_unknown_channel(
    database: Database,
) -> None:
    app = channel_app()
    async with (
        app.router.lifespan_context(app),  # type: ignore[attr-defined]
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http,
    ):
        wrong = await http.post(
            "/webhook/telegram",
            json=telegram_update(),
            headers={"X-Telegram-Bot-Api-Secret-Token": "nope"},
        )
        unknown = await http.post(
            "/webhook/vk", json={"type": "message_new"}, headers=TELEGRAM_HEADERS
        )

    assert wrong.status_code == 401
    assert unknown.status_code == 404


async def test_hr_creates_an_employee_and_the_list_is_scoped(database: Database) -> None:
    app = admin_app()
    body = {
        "employee_id": "2001",
        "name": "Пётр Петров",
        "role": "Оператор",
        "department": "ИТ",
        "recruiter_id": "rec-1",
        "started_at": "2026-11-01",
        "audience": ["all", "dept:it"],
        "scenario_id": "onboarding_default",
    }
    async with (
        app.router.lifespan_context(app),  # type: ignore[attr-defined]
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http,
    ):
        created = await http.post(
            "/admin/api/employees", json=body, headers={"Authorization": "Bearer hr"}
        )
        assert created.status_code == 201, created.text
        assert created.json()["employee_id"] == "2001"
        assert created.json()["channels"] == []
        assert created.json()["status"] == "active"

        repeated = await http.post(
            "/admin/api/employees", json=body, headers={"Authorization": "Bearer hr"}
        )
        assert repeated.status_code == 409
        assert repeated.json()["code"] == "employee_already_exists"

        recruiter = await http.get("/admin/api/employees", headers={"Authorization": "Bearer rec"})
        assert recruiter.status_code == 200, recruiter.text
        assert {item["employee_id"] for item in recruiter.json()["items"]} == {
            str(EMPLOYEE),
            "2001",
        }

        other = await http.get("/admin/api/employees", headers={"Authorization": "Bearer other"})
        assert other.json()["items"] == []
        assert other.json()["total"] == 0

        found = await http.get(
            "/admin/api/employees",
            params={"q": "Пётр"},
            headers={"Authorization": "Bearer rec"},
        )
        assert [item["employee_id"] for item in found.json()["items"]] == ["2001"]

        refused = await http.post(
            "/admin/api/employees", json=body, headers={"Authorization": "Bearer rec"}
        )
        assert refused.status_code == 403
        assert refused.json()["code"] == "forbidden"

        unknown = await http.post(
            "/admin/api/employees",
            json={**body, "employee_id": "2002", "scenario_id": "nope"},
            headers={"Authorization": "Bearer hr"},
        )
        assert unknown.status_code == 422
        assert unknown.json()["code"] == "unknown_scenario"


async def test_employee_detail_carries_the_linked_channels(database: Database) -> None:
    app = admin_app()
    async with (
        app.router.lifespan_context(app),  # type: ignore[attr-defined]
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http,
    ):
        linked = await http.post(
            "/admin/api/identities",
            json={"channel": "max", "external_id": "4242", "employee_id": str(EMPLOYEE)},
            headers={"Authorization": "Bearer hr"},
        )
        assert linked.status_code == 204, linked.text

        detail = await http.get(
            f"/admin/api/employees/{EMPLOYEE}", headers={"Authorization": "Bearer rec"}
        )
        assert detail.status_code == 200, detail.text
        assert detail.json()["channels"] == [
            {
                "channel": "max",
                "external_id": "4242",
                "linked_at": detail.json()["channels"][0]["linked_at"],
            }
        ]

        hidden = await http.get(
            f"/admin/api/employees/{EMPLOYEE}", headers={"Authorization": "Bearer other"}
        )
        assert hidden.status_code == 404
        assert hidden.json()["code"] == "employee_not_found"


async def test_hr_corrects_a_row_and_restores_after_leaving(database: Database) -> None:
    app = admin_app()
    async with (
        app.router.lifespan_context(app),  # type: ignore[attr-defined]
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http,
    ):
        patched = await http.patch(
            f"/admin/api/employees/{EMPLOYEE}",
            json={"name": "Иван Петров", "audience": ["all"]},
            headers={"Authorization": "Bearer hr"},
        )
        assert patched.status_code == 200, patched.text
        assert patched.json()["name"] == "Иван Петров"
        assert patched.json()["audience"] == ["all"]

        invalid = await http.patch(
            f"/admin/api/employees/{EMPLOYEE}",
            json={"audience": ["everyone"]},
            headers={"Authorization": "Bearer hr"},
        )
        assert invalid.status_code == 422
        assert invalid.json()["code"] == "validation_failed"

        left = await http.delete(
            f"/admin/api/employees/{EMPLOYEE}", headers={"Authorization": "Bearer hr"}
        )
        assert left.status_code == 200, left.text

        gone = await http.get(
            f"/admin/api/employees/{EMPLOYEE}", headers={"Authorization": "Bearer hr"}
        )
        assert gone.json()["status"] == "left"
        assert gone.json()["left_at"] is not None

        restored = await http.patch(
            f"/admin/api/employees/{EMPLOYEE}",
            json={"status": "active"},
            headers={"Authorization": "Bearer hr"},
        )
        assert restored.status_code == 200, restored.text
        assert restored.json()["status"] == "active"
        assert restored.json()["left_at"] is None


async def test_bulk_upsert_corrects_a_row_without_resurrecting_it(database: Database) -> None:
    app = admin_app()
    rows = [
        {
            "employee_id": "3001",
            "name": "Анна",
            "role": "Бухгалтер",
            "department": "Бухгалтерия",
            "started_at": "2026-11-03",
        },
        {
            "employee_id": "3002",
            "name": "Борис",
            "role": "Логист",
            "department": "Склад",
            "started_at": "2026-11-04",
        },
    ]
    async with (
        app.router.lifespan_context(app),  # type: ignore[attr-defined]
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http,
    ):
        first = await http.post(
            "/admin/api/employees/bulk",
            json={"employees": rows},
            headers={"Authorization": "Bearer hr"},
        )
        assert first.status_code == 200, first.text
        assert first.json() == {"created": 2, "updated": 0}

        second = await http.post(
            "/admin/api/employees/bulk",
            json={"employees": [{**rows[0], "role": "Старший бухгалтер"}, rows[1]]},
            headers={"Authorization": "Bearer hr"},
        )
        assert second.json() == {"created": 0, "updated": 2}

        detail = await http.get("/admin/api/employees/3001", headers={"Authorization": "Bearer hr"})
        assert detail.json()["role"] == "Старший бухгалтер"

        offboarded = await http.delete(
            "/admin/api/employees/3002", headers={"Authorization": "Bearer hr"}
        )
        assert offboarded.status_code == 200, offboarded.text

        third = await http.post(
            "/admin/api/employees/bulk",
            json={"employees": [{**rows[1], "name": "Борис С."}]},
            headers={"Authorization": "Bearer hr"},
        )
        assert third.json() == {"created": 0, "updated": 1}

        after = await http.get("/admin/api/employees/3002", headers={"Authorization": "Bearer hr"})
        assert after.json()["name"] == "Борис С."
        assert after.json()["status"] == "left"

        duplicate = await http.post(
            "/admin/api/employees/bulk",
            json={"employees": [rows[0], rows[0]]},
            headers={"Authorization": "Bearer hr"},
        )
        assert duplicate.status_code == 422
        assert duplicate.json()["code"] == "validation_failed"


async def test_the_directory_pages_without_gaps_or_repeats(database: Database) -> None:
    app = admin_app()
    rows = [
        {
            "employee_id": f"400{number}",
            "name": f"Сотрудник {number}",
            "role": "Оператор",
            "department": "Склад",
            "started_at": "2026-11-05",
        }
        for number in range(3)
    ]
    async with (
        app.router.lifespan_context(app),  # type: ignore[attr-defined]
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http,
    ):
        seeded = await http.post(
            "/admin/api/employees/bulk",
            json={"employees": rows},
            headers={"Authorization": "Bearer hr"},
        )
        assert seeded.status_code == 200, seeded.text
        # One batch shares a transaction timestamp, so the id is the tiebreaker that keeps the
        # page boundary stable.
        seen: list[str] = []
        cursor: str | None = None
        for _ in range(4):
            params: dict[str, str | int] = {"limit": 2}
            if cursor is not None:
                params["cursor"] = cursor
            page = await http.get(
                "/admin/api/employees", params=params, headers={"Authorization": "Bearer hr"}
            )
            assert page.status_code == 200, page.text
            body = page.json()
            seen.extend(item["employee_id"] for item in body["items"])
            cursor = body["next_cursor"]
            if cursor is None:
                break
        assert len(seen) == len(set(seen))
        assert set(seen) == {str(EMPLOYEE), "4000", "4001", "4002"}


# --- inbound files ---------------------------------------------------------

JPEG = b"\xff\xd8\xff\xe0" + b"scan-padding" * 20 + b"SECRET-MARKER"


class StubFetcher:
    def __init__(self, data: bytes = JPEG, error: Exception | None = None) -> None:
        self.data = data
        self.error = error
        self.calls: list[str] = []

    async def fetch(self, file: object) -> bytes:
        self.calls.append(file.token)  # type: ignore[attr-defined]
        if self.error is not None:
            raise self.error
        return self.data


def intake(
    db: Database, fetcher: StubFetcher, *, key: bytes | None = b"k" * 32, max_bytes: int = 10_000
) -> InboundFileIntake:
    return InboundFileIntake(
        database=db, fetcher=fetcher, audit=NullAudit(), key=key, max_bytes=max_bytes
    )


async def test_an_inbound_file_is_encrypted_and_stored_once(database: Database) -> None:
    fetcher = StubFetcher()
    store = intake(database, fetcher)
    attachment = InboundFile(
        token="token-1", url="https://cdn.test/1", filename="passport.jpg", size=len(JPEG)
    )

    first = await store.save(str(EMPLOYEE), MAX, [attachment])
    again = await store.save(str(EMPLOYEE), MAX, [attachment])

    assert [file.status for file in first] == ["stored"]
    assert [file.status for file in again] == ["stored"]
    # The token is the idempotency key: a redelivery does not fetch or insert twice.
    assert fetcher.calls == ["token-1"]
    async with database.session() as session:
        rows = (await session.scalars(select(InboundFileRow))).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.filename == "passport.jpg"
    assert row.media_type == "image/jpeg"
    assert row.content is not None
    assert b"SECRET-MARKER" not in row.content
    assert decrypt(b"k" * 32, row.content) == JPEG
    assert row.sha256 == hashlib.sha256(JPEG).hexdigest()


async def test_a_file_that_is_not_a_document_is_rejected(database: Database) -> None:
    store = intake(database, StubFetcher(b"just some text"))

    stored = await store.save(
        str(EMPLOYEE), MAX, [InboundFile(token="t", url="https://cdn.test/t", filename="a.jpg")]
    )

    assert stored[0].status == "rejected"
    assert stored[0].error == "unsupported_type"
    async with database.session() as session:
        row = await session.scalar(select(InboundFileRow))
    assert row is not None
    assert row.content is None


async def test_an_oversized_file_is_refused_before_download(database: Database) -> None:
    fetcher = StubFetcher()
    store = intake(database, fetcher, max_bytes=1000)

    stored = await store.save(
        str(EMPLOYEE),
        MAX,
        [InboundFile(token="t", url="https://cdn.test/t", filename="scan.pdf", size=5000)],
    )

    assert stored[0].status == "rejected"
    assert stored[0].error == "declared_size"
    assert fetcher.calls == []


async def test_a_failed_download_is_recorded_and_a_retry_fills_it(database: Database) -> None:
    failing = StubFetcher(error=RuntimeError("cdn down"))
    store = intake(database, failing)
    attachment = InboundFile(token="t", url="https://cdn.test/t", filename="scan.pdf")

    failed = await store.save(str(EMPLOYEE), MAX, [attachment])
    retried = await intake(database, StubFetcher()).save(str(EMPLOYEE), MAX, [attachment])

    assert failed[0].status == "failed"
    assert failed[0].error is not None
    assert "RuntimeError" in failed[0].error
    assert retried[0].status == "stored"


async def test_without_a_key_the_attempt_is_recorded_but_no_bytes_are_kept(
    database: Database,
) -> None:
    store = intake(database, StubFetcher(), key=None)

    stored = await store.save(
        str(EMPLOYEE), MAX, [InboundFile(token="t", url="https://cdn.test/t", filename="a.jpg")]
    )

    assert stored[0].status == "unavailable"
    assert stored[0].error == "no_key"
    async with database.session() as session:
        row = await session.scalar(select(InboundFileRow))
    assert row is not None
    assert row.content is None


async def test_offboarding_deletes_the_documents(database: Database) -> None:
    await intake(database, StubFetcher()).save(
        str(EMPLOYEE), MAX, [InboundFile(token="t", url="https://cdn.test/t", filename="a.jpg")]
    )

    result = await EmployeeOffboarder(database, FrozenClock(NOW)).offboard(
        str(EMPLOYEE), actor="hr"
    )

    assert result.files_deleted == 1
    async with database.session() as session:
        assert await session.scalar(select(func.count()).select_from(InboundFileRow)) == 0


async def test_acl_rule_agrees_with_sql(database: Database) -> None:
    """The SQL clause admits exactly the rows the rule admits, for every audience shape.

    The rule used to live twice: ``core.access.permits`` refused ``[all, hr_only]`` to everyone but
    HR while the ``WHERE`` clause was an array overlap and admitted it to anyone holding ``all``.
    The schema now forbids that shape, and this test is why the second barrier can be trusted: the
    forbidden shape stays in the corpus of the test, and both paths agree that it is closed.
    """
    on_date = date(2026, 10, 24)
    shapes: list[tuple[tuple[str, ...], str, date | None, date | None]] = [
        (("all",), "active", None, None),
        (("hr_only",), "active", None, None),
        (("dept:it",), "active", None, None),
        (("dept:sales",), "active", None, None),
        (("dept:it", "dept:sales"), "active", None, None),
        (("all", "hr_only"), "active", None, None),
        (("all",), "draft", None, None),
        (("all", "dept:it"), "active", date(2024, 1, 1), date(2025, 1, 1)),
        (("all", "dept:it"), "active", date(2024, 1, 1), None),
    ]
    documents = {}
    async with database.session() as session:
        for index, (audience, status, valid_from, valid_to) in enumerate(shapes):
            doc_id = f"acl/probe-{index}"
            row = DocumentRow(
                id=doc_id,
                title=f"Probe {index}",
                type="knowledge",
                status=status,
                owner="hr",
                audience=list(audience),
                valid_from=valid_from,
                valid_to=valid_to,
                checksum="0" * 64,
                body="body",
            )
            session.add(row)
            documents[doc_id] = row
    viewers = (
        (),
        ("all",),
        ("all", "hr_only"),
        ("all", "dept:it"),
        ("all", "dept:sales"),
        ("all", "dept:production"),
    )
    async with database.session() as session:
        for viewer in viewers:
            rows = await session.scalars(
                select(DocumentRow.id).where(acl_clause(viewer, on_date))
            )
            admitted = set(rows)
            expected = {
                doc_id
                for doc_id, row in documents.items()
                if holds(
                    predicates(viewer, on_date),
                    subject_of(
                        Document(
                            id=DocId(doc_id),
                            title=row.title,
                            text="body",
                            audience=tuple(row.audience),
                            valid_from=row.valid_from or date(1970, 1, 1),
                            valid_to=row.valid_to,
                        ),
                        status=row.status,
                    ),
                )
            }
            assert admitted == expected, viewer

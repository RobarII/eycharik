"""Composition root.

Every dependency is built once, here, from settings. Nothing else in the app constructs an HTTP
client, a database or a model adapter on its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx

from onboarding.app.clock import SystemClock
from onboarding.app.copy import Copy, load_copy
from onboarding.app.db.directory import SqlDirectory
from onboarding.app.db.kb import PostgresKnowledgeBase, assert_embedding_width
from onboarding.app.db.outbox import MessageDispatcher, OutboxMessaging
from onboarding.app.db.queue import JobQueue
from onboarding.app.db.repos import (
    DatabaseAuditLog,
    DatabaseQuestionLog,
    DatabaseRunRepository,
)
from onboarding.app.db.scheduler import ReminderScheduler
from onboarding.app.db.session import Database
from onboarding.app.llm.embeddings import build_embedder
from onboarding.app.llm.gateway import build_llm
from onboarding.app.llm.rerank import RemoteReranker
from onboarding.app.llm.sentiment import SentimentClassifier
from onboarding.app.max.client import MaxClient
from onboarding.app.prompts import PromptLibrary
from onboarding.app.scenarios import ScenarioCatalog
from onboarding.app.settings import Settings
from onboarding.app.worker.actions import ActionExecutor
from onboarding.app.worker.answerer import Answerer
from onboarding.app.worker.service import OnboardingService
from onboarding.ports import LLM, Clock, Embedder, KnowledgeBase, Messaging

SCENARIO_DIR = Path(__file__).resolve().parents[1] / "scenarios"


@dataclass(slots=True)
class Container:
    settings: Settings
    clock: Clock
    http: httpx.AsyncClient
    database: Database
    llm: LLM
    embedder: Embedder
    knowledge: KnowledgeBase
    prompts: PromptLibrary
    copy: Copy
    catalog: ScenarioCatalog
    directory: SqlDirectory
    sender: Messaging
    outbox: OutboxMessaging
    answerer: Answerer
    executor: ActionExecutor
    service: OnboardingService
    queue: JobQueue
    dispatcher: MessageDispatcher
    scheduler: ReminderScheduler
    audit: DatabaseAuditLog

    async def aclose(self) -> None:
        await self.http.aclose()
        await self.database.dispose()


def build_container(settings: Settings) -> Container:
    verify: bool | str = True
    if settings.max_ca_bundle is not None:
        verify = str(settings.max_ca_bundle)
    http = httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0), verify=verify)

    database = Database(settings.database_url)
    clock = SystemClock()
    llm = build_llm(settings, clock, http)
    embedder = build_embedder(settings, http)
    assert_embedding_width(settings.embed_dim)
    knowledge = PostgresKnowledgeBase(database, embedder)

    prompts = PromptLibrary(settings.prompts_dir)
    copy = load_copy(settings.copy_path)
    catalog = ScenarioCatalog.load(SCENARIO_DIR)
    directory = SqlDirectory(database)
    audit = DatabaseAuditLog(database)

    sender = MaxClient(
        base_url=settings.max_base_url,
        token=settings.max_bot_token,
        client=http,
        messages_per_second=settings.max_messages_per_second,
    )
    outbox = OutboxMessaging(database, sender)
    reranker = (
        RemoteReranker(
            client=http,
            base_url=settings.rerank_base_url,
            api_key=settings.rerank_api_key.get_secret_value(),
            model=settings.rerank_model,
            timeout_s=settings.rerank_timeout_s,
        )
        if settings.rerank_base_url
        else None
    )
    answerer = Answerer(
        knowledge=knowledge,
        llm=llm,
        prompts=prompts,
        copy=copy,
        settings=settings,
        audit=audit,
        reranker=reranker,
    )
    executor = ActionExecutor(
        messaging=outbox,
        answerer=answerer,
        copy=copy,
        audit=audit,
        questions=DatabaseQuestionLog(database),
    )
    classifier = (
        SentimentClassifier(llm=llm, prompts=prompts, audit=audit)
        if settings.is_llm_configured
        else None
    )
    service = OnboardingService(
        runs=DatabaseRunRepository(database),
        catalog=catalog,
        executor=executor,
        clock=clock,
        directory=directory,
        audit=audit,
        classifier=classifier,
    )
    return Container(
        settings=settings,
        clock=clock,
        http=http,
        database=database,
        llm=llm,
        embedder=embedder,
        knowledge=knowledge,
        prompts=prompts,
        copy=copy,
        catalog=catalog,
        directory=directory,
        sender=sender,
        outbox=outbox,
        answerer=answerer,
        executor=executor,
        service=service,
        queue=JobQueue(database),
        dispatcher=MessageDispatcher(database, sender),
        scheduler=ReminderScheduler(database),
        audit=audit,
    )

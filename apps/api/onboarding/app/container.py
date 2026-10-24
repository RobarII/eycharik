"""Composition root for the worker, the CLI, and the eval runner.

The API has its own container (``api_container``) and deliberately cannot construct a model. This
one builds the full graph: models, retrieval, extraction, the outbox, and the scheduler.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

from onboarding.app.channels.max.client import MaxClient
from onboarding.app.channels.max.files import MaxFiles
from onboarding.app.channels.telegram.client import TelegramClient
from onboarding.app.channels.vk.client import VkClient
from onboarding.app.composition import (
    DOC_SCHEMA,
    SCENARIO_ASSETS_DIR,
    Common,
    build_common,
)
from onboarding.app.copy import Copy, load_copy
from onboarding.app.db.kb import (
    PostgresKnowledgeBase,
    PostgresKnowledgeWriter,
    assert_embedding_width,
)
from onboarding.app.db.outbox import MessageDispatcher, OutboxMessaging
from onboarding.app.db.queue import JobQueue
from onboarding.app.db.repos import DatabaseQuestionLog, DatabaseRunRepository
from onboarding.app.db.scheduler import ReminderScheduler
from onboarding.app.files.crypto import load_key
from onboarding.app.files.intake import InboundFileIntake
from onboarding.app.knowledge.extract.ocr import build_ocr
from onboarding.app.knowledge.extract.pdf import PdfReader
from onboarding.app.knowledge.extract.pptx import PptxReader
from onboarding.app.knowledge.extract.router import RoutingExtraction
from onboarding.app.llm.embeddings import build_embedder
from onboarding.app.llm.gateway import build_llm
from onboarding.app.llm.rerank import build_reranker
from onboarding.app.llm.sentiment import build_sentiment
from onboarding.app.prompts import PromptLibrary
from onboarding.app.settings import Settings
from onboarding.app.tls import verify as tls_verify
from onboarding.app.worker.actions import ActionExecutor
from onboarding.app.worker.answerer import Answerer
from onboarding.app.worker.extract import DocumentExtractor
from onboarding.app.worker.index import DocumentIndexer
from onboarding.app.worker.service import OnboardingService
from onboarding.core.models import Channel
from onboarding.ports import (
    LLM,
    AuditLog,
    Clock,
    Embedder,
    KnowledgeBase,
    Messaging,
    SentimentAnalysis,
)


@dataclass(slots=True)
class Container(Common):
    http: httpx.AsyncClient
    llm: LLM
    embedder: Embedder
    knowledge: KnowledgeBase
    prompts: PromptLibrary
    copy: Copy
    senders: dict[Channel, Messaging]
    outbox: OutboxMessaging
    answerer: Answerer
    executor: ActionExecutor
    service: OnboardingService
    queue: JobQueue
    dispatcher: MessageDispatcher
    scheduler: ReminderScheduler
    extractor: DocumentExtractor
    indexer: DocumentIndexer
    files: InboundFileIntake

    async def aclose(self) -> None:
        await self.http.aclose()
        await Common.aclose(self)


def _demo_ids(settings: Settings) -> frozenset[int]:
    raw = settings.demo_employee_ids_raw.strip()
    if not raw:
        return frozenset()
    try:
        return frozenset(int(part) for part in raw.replace(";", ",").split(",") if part.strip())
    except ValueError:
        raise ValueError("DEMO_EMPLOYEE_IDS must be a comma-separated list of numbers") from None


def _classifier(
    settings: Settings,
    *,
    clock: Clock,
    http: httpx.AsyncClient,
    llm: LLM,
    prompts: PromptLibrary,
    audit: AuditLog,
) -> SentimentAnalysis | None:
    try:
        choice = build_sentiment(
            settings,
            clock=clock,
            client=http,
            prompts=prompts,
            audit=audit,
            llm=llm,
        )
    except ValueError as error:
        raise RuntimeError(f"sentiment provider misconfigured: {error}") from error
    # ``None`` is the worker's deterministic floor, not a third policy: ``core.risk.keyword_signal``
    # is already what a missing model signal means everywhere else.
    return None if choice.provider == "keyword" else choice.classifier


def build_container(settings: Settings) -> Container:
    common = build_common(settings)

    http = httpx.AsyncClient(
        timeout=httpx.Timeout(15.0, connect=5.0), verify=tls_verify(settings.max_ca_bundle)
    )

    llm = build_llm(settings, common.clock, http)
    embedder = build_embedder(settings, http, clock=common.clock)
    assert_embedding_width(embedder.dim)
    knowledge = PostgresKnowledgeBase(common.database, embedder, bm25=settings.bm25_enabled)
    prompts = PromptLibrary(settings.prompts_dir)
    copy = load_copy(settings.copy_path)

    enabled = set(settings.channels)
    senders: dict[Channel, Messaging] = {}
    if Channel.MAX in enabled and settings.max_webhook_secret.get_secret_value():
        senders[Channel.MAX] = MaxClient(
            base_url=settings.max_base_url,
            token=settings.max_bot_token,
            client=http,
            messages_per_second=common.profiles[Channel.MAX].messages_per_second,
            assets_dir=SCENARIO_ASSETS_DIR,
        )
    if Channel.TELEGRAM in enabled and settings.telegram_webhook_secret.get_secret_value():
        senders[Channel.TELEGRAM] = TelegramClient(
            base_url=settings.telegram_base_url,
            token=settings.telegram_bot_token,
            client=http,
            profile=common.profiles[Channel.TELEGRAM],
        )
    if (
        Channel.VK in enabled
        and settings.vk_webhook_secret.get_secret_value()
        and settings.vk_confirmation_code.get_secret_value()
    ):
        senders[Channel.VK] = VkClient(
            base_url=settings.vk_base_url,
            api_version=settings.vk_api_version,
            token=settings.vk_access_token,
            client=http,
            profile=common.profiles[Channel.VK],
        )

    outbox = OutboxMessaging(common.database, senders, common.profiles)
    files = InboundFileIntake(
        database=common.database,
        fetcher=MaxFiles(
            client=http,
            token=settings.max_bot_token,
            platform_host=urlsplit(settings.max_base_url).hostname or "",
            max_bytes=settings.inbound_files_max_bytes,
        ),
        audit=common.audit,
        key=load_key(settings.inbound_files_key.get_secret_value()),
        max_bytes=settings.inbound_files_max_bytes,
    )
    reranker = build_reranker(settings, http, clock=common.clock)
    answerer = Answerer(
        knowledge=knowledge,
        llm=llm,
        prompts=prompts,
        copy=copy,
        settings=settings,
        audit=common.audit,
        reranker=reranker,
    )
    executor = ActionExecutor(
        messaging=outbox,
        answerer=answerer,
        copy=copy,
        audit=common.audit,
        questions=DatabaseQuestionLog(common.database),
    )
    classifier = _classifier(
        settings,
        clock=common.clock,
        http=http,
        llm=llm,
        prompts=prompts,
        audit=common.audit,
    )
    service = OnboardingService(
        runs=DatabaseRunRepository(common.database),
        catalog=common.catalog,
        executor=executor,
        clock=common.clock,
        directory=common.directory,
        audit=common.audit,
        classifier=classifier,
        demo_ids=_demo_ids(settings),
    )

    writer = PostgresKnowledgeWriter(common.database, embedder)
    extractor = DocumentExtractor(
        blobs=common.blobs,
        extraction=RoutingExtraction(
            readers=(PdfReader(), PptxReader()),
            ocr=build_ocr(common.extraction_profile.family),
            max_pages=settings.extraction_max_pages,
        ),
        cache=common.extraction_cache,
        writer=writer,
        embedder=embedder,
        schema_path=settings.contracts_dir / DOC_SCHEMA,
        profile=common.extraction_profile,
        audit=common.audit,
    )
    indexer = DocumentIndexer(
        blobs=common.blobs,
        cache=common.extraction_cache,
        writer=writer,
        embedder=embedder,
        schema_path=settings.contracts_dir / DOC_SCHEMA,
        audit=common.audit,
    )

    return Container(
        settings=common.settings,
        clock=common.clock,
        database=common.database,
        audit=common.audit,
        catalog=common.catalog,
        directory=common.directory,
        profiles=common.profiles,
        ingress=common.ingress,
        blobs=common.blobs,
        extraction_cache=common.extraction_cache,
        extraction_profile=common.extraction_profile,
        http=http,
        llm=llm,
        embedder=embedder,
        knowledge=knowledge,
        prompts=prompts,
        copy=copy,
        senders=senders,
        outbox=outbox,
        answerer=answerer,
        executor=executor,
        service=service,
        queue=JobQueue(common.database),
        dispatcher=MessageDispatcher(common.database, senders),
        scheduler=ReminderScheduler(common.database),
        extractor=extractor,
        indexer=indexer,
        files=files,
    )

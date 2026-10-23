"""Composition root.

Every dependency is built once, here, from settings. Nothing else in the app constructs an HTTP
client, a database or a model adapter on its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx

from onboarding.app.channels.max.client import MaxClient
from onboarding.app.channels.max.ingress import MaxIngress
from onboarding.app.channels.profiles import ChannelProfileLibrary
from onboarding.app.channels.telegram.client import TelegramClient
from onboarding.app.channels.telegram.ingress import TelegramIngress
from onboarding.app.clock import SystemClock
from onboarding.app.copy import Copy, load_copy
from onboarding.app.db.blobs import PostgresBlobStore
from onboarding.app.db.directory import SqlDirectory
from onboarding.app.db.extractions import PostgresExtractionCache
from onboarding.app.db.kb import (
    PostgresKnowledgeBase,
    PostgresKnowledgeWriter,
    assert_embedding_width,
)
from onboarding.app.db.outbox import MessageDispatcher, OutboxMessaging
from onboarding.app.db.queue import JobQueue
from onboarding.app.db.repos import (
    DatabaseAuditLog,
    DatabaseQuestionLog,
    DatabaseRunRepository,
)
from onboarding.app.db.scheduler import ReminderScheduler
from onboarding.app.db.session import Database
from onboarding.app.knowledge.extract.ocr import build_ocr
from onboarding.app.knowledge.extract.pdf import PdfReader
from onboarding.app.knowledge.extract.pptx import PptxReader
from onboarding.app.knowledge.extract.profiles import ExtractionProfileLibrary
from onboarding.app.knowledge.extract.router import RoutingExtraction
from onboarding.app.llm.embeddings import build_embedder
from onboarding.app.llm.gateway import build_llm
from onboarding.app.llm.jev import build_jev_classifier
from onboarding.app.llm.rerank import build_reranker
from onboarding.app.llm.sentiment import SentimentClassifier
from onboarding.app.prompts import PromptLibrary
from onboarding.app.scenarios import ScenarioCatalog
from onboarding.app.settings import Settings
from onboarding.app.worker.actions import ActionExecutor
from onboarding.app.worker.answerer import Answerer
from onboarding.app.worker.extract import DocumentExtractor
from onboarding.app.worker.service import OnboardingService
from onboarding.core.channels import ChannelProfile
from onboarding.core.models import Channel
from onboarding.ports import (
    LLM,
    AuditLog,
    Clock,
    Embedder,
    Ingress,
    KnowledgeBase,
    Messaging,
    SentimentAnalysis,
)

SCENARIO_DIR = Path(__file__).resolve().parents[1] / "scenarios"
CHANNEL_PROFILES_DIR = Path(__file__).resolve().parents[1] / "channel-profiles"


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
    profiles: dict[Channel, ChannelProfile]
    senders: dict[Channel, Messaging]
    ingress: dict[Channel, Ingress]
    outbox: OutboxMessaging
    answerer: Answerer
    executor: ActionExecutor
    service: OnboardingService
    queue: JobQueue
    dispatcher: MessageDispatcher
    scheduler: ReminderScheduler
    audit: DatabaseAuditLog
    blobs: PostgresBlobStore
    extraction_cache: PostgresExtractionCache
    extractor: DocumentExtractor

    async def aclose(self) -> None:
        await self.http.aclose()
        await self.database.dispose()


def _classifier(
    settings: Settings,
    *,
    http: httpx.AsyncClient,
    llm: LLM,
    prompts: PromptLibrary,
    audit: AuditLog,
) -> SentimentAnalysis | None:
    if settings.sentiment_provider == "jev":
        return build_jev_classifier(
            client=http,
            endpoint=f"{settings.jev_base_url.rstrip('/')}/systemone",
            api_key=settings.jev_api_key,
            rubric_path=settings.prompts_dir / "sentiment-jev" / "v1.yaml",
            audit=audit,
            timeout_s=settings.jev_timeout_s,
            max_retries=settings.jev_max_retries,
        )
    if not settings.is_llm_configured:
        return None
    return SentimentClassifier(llm=llm, prompts=prompts, audit=audit)


def build_container(settings: Settings) -> Container:
    verify: bool | str = True
    if settings.max_ca_bundle is not None:
        verify = str(settings.max_ca_bundle)
    http = httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0), verify=verify)

    database = Database(settings.database_url)
    clock = SystemClock()
    llm = build_llm(settings, clock, http)
    embedder = build_embedder(settings, http)
    assert_embedding_width(embedder.dim)
    knowledge = PostgresKnowledgeBase(database, embedder, bm25=settings.bm25_enabled)

    prompts = PromptLibrary(settings.prompts_dir)
    copy = load_copy(settings.copy_path)
    catalog = ScenarioCatalog.load(SCENARIO_DIR)
    directory = SqlDirectory(database)
    audit = DatabaseAuditLog(database)

    profiles = ChannelProfileLibrary(
        settings.channel_profiles_dir,
        settings.contracts_dir / "channel-profile.schema.json",
    ).load_all()
    enabled = set(settings.channels)
    senders: dict[Channel, Messaging] = {}
    ingress: dict[Channel, Ingress] = {}
    if Channel.MAX in enabled:
        senders[Channel.MAX] = MaxClient(
            base_url=settings.max_base_url,
            token=settings.max_bot_token,
            client=http,
            messages_per_second=profiles[Channel.MAX].messages_per_second,
        )
        ingress[Channel.MAX] = MaxIngress(settings.max_webhook_secret)
    if Channel.TELEGRAM in enabled:
        senders[Channel.TELEGRAM] = TelegramClient(
            base_url=settings.telegram_base_url,
            token=settings.telegram_bot_token,
            client=http,
            profile=profiles[Channel.TELEGRAM],
        )
        ingress[Channel.TELEGRAM] = TelegramIngress(settings.telegram_webhook_secret)

    outbox = OutboxMessaging(database, senders, profiles)
    reranker = build_reranker(settings, http)
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
    classifier = _classifier(settings, http=http, llm=llm, prompts=prompts, audit=audit)
    service = OnboardingService(
        runs=DatabaseRunRepository(database),
        catalog=catalog,
        executor=executor,
        clock=clock,
        directory=directory,
        audit=audit,
        classifier=classifier,
    )
    extraction_profiles = ExtractionProfileLibrary(
        settings.extraction_profiles_dir,
        settings.contracts_dir / "extraction-profile.schema.json",
    )
    extraction_profile = extraction_profiles.load(settings.extraction_profile)
    blobs = PostgresBlobStore(database, max_bytes=settings.extraction_max_upload_bytes)
    extraction_cache = PostgresExtractionCache(database)
    extractor = DocumentExtractor(
        blobs=blobs,
        extraction=RoutingExtraction(
            readers=(PdfReader(), PptxReader()),
            ocr=build_ocr(extraction_profile.family),
            max_pages=settings.extraction_max_pages,
        ),
        cache=extraction_cache,
        writer=PostgresKnowledgeWriter(database),
        embedder=embedder,
        schema_path=settings.contracts_dir / "doc.schema.json",
        profile=extraction_profile,
        audit=audit,
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
        profiles=profiles,
        senders=senders,
        ingress=ingress,
        outbox=outbox,
        answerer=answerer,
        executor=executor,
        service=service,
        queue=JobQueue(database),
        dispatcher=MessageDispatcher(database, senders),
        scheduler=ReminderScheduler(database),
        audit=audit,
        blobs=blobs,
        extraction_cache=extraction_cache,
        extractor=extractor,
    )

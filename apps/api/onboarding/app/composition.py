"""Shared composition for every process.

The API needs addresses, ingress, storage, and read models. The worker additionally needs models,
retrieval, extraction, and the outbox. Building the common half once keeps those two worlds from
silently acquiring each other's dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from onboarding.app.channels.max.ingress import MaxIngress
from onboarding.app.channels.profiles import ChannelProfileLibrary
from onboarding.app.channels.telegram.ingress import TelegramIngress
from onboarding.app.channels.vk.ingress import VkIngress
from onboarding.app.clock import SystemClock
from onboarding.app.db.blobs import PostgresBlobStore
from onboarding.app.db.directory import SqlDirectory
from onboarding.app.db.extractions import PostgresExtractionCache
from onboarding.app.db.repos import DatabaseAuditLog
from onboarding.app.db.session import Database
from onboarding.app.knowledge.extract.profiles import ExtractionProfileLibrary
from onboarding.app.scenarios import ScenarioCatalog
from onboarding.app.settings import Settings
from onboarding.core.channels import ChannelProfile
from onboarding.core.models import Channel
from onboarding.ports import (
    AuditLog,
    Clock,
    ExtractionProfile,
    Ingress,
)

SCENARIO_DIR = Path(__file__).resolve().parents[1] / "scenarios"
SCENARIO_ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets" / "scenario"
DOC_SCHEMA = "doc.schema.json"
CHANNEL_SCHEMA = "channel-profile.schema.json"
EXTRACTION_SCHEMA = "extraction-profile.schema.json"


@dataclass(slots=True)
class Common:
    settings: Settings
    clock: Clock
    database: Database
    audit: AuditLog
    catalog: ScenarioCatalog
    directory: SqlDirectory
    profiles: dict[Channel, ChannelProfile]
    ingress: dict[Channel, Ingress]
    blobs: PostgresBlobStore
    extraction_cache: PostgresExtractionCache
    extraction_profile: ExtractionProfile

    async def aclose(self) -> None:
        await self.database.dispose()


def build_common(settings: Settings) -> Common:
    database = Database(settings.database_url)
    clock = SystemClock()
    catalog = ScenarioCatalog.load(SCENARIO_DIR)
    directory = SqlDirectory(database)
    audit = DatabaseAuditLog(database)

    profiles = ChannelProfileLibrary(
        settings.channel_profiles_dir,
        settings.contracts_dir / CHANNEL_SCHEMA,
    ).load_all()
    enabled = set(settings.channels)
    ingress: dict[Channel, Ingress] = {}
    if Channel.MAX in enabled and settings.max_webhook_secret.get_secret_value():
        ingress[Channel.MAX] = MaxIngress(settings.max_webhook_secret)
    if Channel.TELEGRAM in enabled and settings.telegram_webhook_secret.get_secret_value():
        ingress[Channel.TELEGRAM] = TelegramIngress(settings.telegram_webhook_secret)
    if (
        Channel.VK in enabled
        and settings.vk_webhook_secret.get_secret_value()
        and settings.vk_confirmation_code.get_secret_value()
    ):
        ingress[Channel.VK] = VkIngress(
            settings.vk_webhook_secret, settings.vk_confirmation_code
        )

    extraction_profile = ExtractionProfileLibrary(
        settings.extraction_profiles_dir,
        settings.contracts_dir / EXTRACTION_SCHEMA,
    ).load(settings.extraction_profile)

    return Common(
        settings=settings,
        clock=clock,
        database=database,
        audit=audit,
        catalog=catalog,
        directory=directory,
        profiles=profiles,
        ingress=ingress,
        blobs=PostgresBlobStore(database, max_bytes=settings.extraction_max_upload_bytes),
        extraction_cache=PostgresExtractionCache(database),
        extraction_profile=extraction_profile,
    )

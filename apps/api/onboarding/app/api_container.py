"""The API process has no model, no embedder, and no extractor.

That is the architectural invariant made physical: a route cannot accidentally call a provider
because the object it receives does not contain one.
"""

from __future__ import annotations

from dataclasses import dataclass

from onboarding.app.admin.service import AdminService
from onboarding.app.composition import DOC_SCHEMA, Common, build_common
from onboarding.app.db.health import DatabaseHealth
from onboarding.app.db.inbound import SqlInboundSink
from onboarding.app.db.submissions import PostgresKnowledgeSubmitter
from onboarding.app.knowledge.ingest import load_schema
from onboarding.app.settings import Settings
from onboarding.app.use_cases.inbound import AcceptInbound


@dataclass(slots=True)
class ApiContainer(Common):
    admin: AdminService
    inbound: AcceptInbound
    health: DatabaseHealth

    async def aclose(self) -> None:
        await Common.aclose(self)


def build_api_container(settings: Settings) -> ApiContainer:
    common = build_common(settings)
    submitter = PostgresKnowledgeSubmitter(
        common.database, max_bytes=settings.extraction_max_upload_bytes
    )
    admin = AdminService(
        database=common.database,
        clock=common.clock,
        settings=settings,
        catalog=common.catalog,
        directory=common.directory,
        extractions=common.extraction_cache,
        submitter=submitter,
        schema=load_schema(settings.contracts_dir / DOC_SCHEMA),
        extraction_profile_hash=common.extraction_profile.fingerprint(),
        contracts_dir=settings.contracts_dir,
        audit=common.audit,
    )
    inbound = AcceptInbound(
        ingress=common.ingress,
        directory=common.directory,
        audit=common.audit,
        clock=common.clock,
        sink=SqlInboundSink(common.database),
    )
    return ApiContainer(
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
        admin=admin,
        inbound=inbound,
        health=DatabaseHealth(common.database),
    )

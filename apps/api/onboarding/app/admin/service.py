"""The cabinet's application boundary.

Routes may call this object; they may not reach a session, a writer, or a job queue. The service
composes the existing command objects and the read model, so the cabinet's write rules stay in one
place whether the caller is HTTP, a test, or a future CLI.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from onboarding.app.admin.actions import (
    Assignment,
    EmployeeOffboarder,
    Offboarding,
    QuestionAssigner,
    QuestionResolver,
    Resolution,
)
from onboarding.app.admin.queries import AdminQueries
from onboarding.app.db.session import Database
from onboarding.app.scenarios import ScenarioCatalog
from onboarding.app.settings import Settings
from onboarding.app.use_cases.knowledge import SubmitKnowledge
from onboarding.core.models import Channel, EmployeeId
from onboarding.ports import (
    AuditLog,
    Clock,
    Directory,
    ExtractionCache,
    ExtractionRecord,
    KnowledgeSubmission,
    KnowledgeSubmitter,
)


class AdminService:
    def __init__(
        self,
        *,
        database: Database,
        clock: Clock,
        settings: Settings,
        catalog: ScenarioCatalog,
        directory: Directory,
        extractions: ExtractionCache,
        submitter: KnowledgeSubmitter,
        schema: Mapping[str, Any],
        extraction_profile_hash: str,
        contracts_dir: Path,
        audit: AuditLog,
    ) -> None:
        self.queries = AdminQueries(database)
        self.catalog = catalog
        self.directory = directory
        self.clock = clock
        self.settings = settings
        self._extractions = extractions
        self._extraction_profile_hash = extraction_profile_hash
        self._resolver = QuestionResolver(database, clock)
        self._assigner = QuestionAssigner(database, clock)
        self._offboarder = EmployeeOffboarder(database, clock)
        self._knowledge = SubmitKnowledge(
            submitter=submitter,
            schema=schema,
            audit=audit,
        )
        self.contracts_dir = contracts_dir

    async def resolve_question(
        self,
        question_id: int,
        *,
        text: str,
        actor: str,
        recruiter_id: str | None,
        department: str | None,
    ) -> Resolution:
        return await self._resolver.resolve(
            question_id,
            text=text,
            actor=actor,
            recruiter_id=recruiter_id,
            department=department,
        )

    async def assign_question(
        self,
        question_id: int,
        *,
        assignee: str | None,
        actor: str,
        recruiter_id: str | None,
        department: str | None,
    ) -> Assignment:
        return await self._assigner.assign(
            question_id,
            assignee=assignee,
            actor=actor,
            known=self.settings.admin_subjects,
            recruiter_id=recruiter_id,
            department=department,
        )

    async def offboard(self, employee_id: str, *, actor: str) -> Offboarding:
        return await self._offboarder.offboard(employee_id, actor=actor)

    async def link_identity(
        self, channel: Channel, external_id: str, employee_id: str
    ) -> bool:
        return await self.directory.link(channel, external_id, EmployeeId(employee_id))

    async def extraction(self, content_hash: str) -> ExtractionRecord | None:
        return await self._extractions.load_latest(content_hash)

    async def submit_markdown(self, text: str, *, actor: str) -> KnowledgeSubmission:
        return await self._knowledge.markdown(text, actor=actor)

    async def submit_file(
        self,
        *,
        content: bytes,
        filename: str,
        declared_media_type: str | None,
        raw_metadata: str,
        actor: str,
        max_bytes: int,
    ) -> KnowledgeSubmission:
        return await self._knowledge.file(
            content=content,
            filename=filename,
            declared_media_type=declared_media_type,
            raw_metadata=raw_metadata,
            actor=actor,
            profile_hash=self._extraction_profile_hash,
            max_bytes=max_bytes,
        )

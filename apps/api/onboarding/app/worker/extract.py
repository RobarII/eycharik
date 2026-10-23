"""The ``extract_document`` job: one uploaded file becomes one knowledge document.

Order matters and mirrors the rest of the worker:

1. read the blob (cheap), look up the cache by ``(content hash, profile hash)``;
2. extract — either native text or recognition, decided by pure code;
3. accept or refuse *before* anything is written to the corpus;
4. only an accepted document is rendered to markdown and indexed through the same
   ``parse_document`` choke point the corpus directory uses;
5. record the outcome, refusal included, so a recruiter can read it in the cabinet.

A refusal completes the job. It is a decision, not a failure, and retrying it five times would only
spend CPU to reach the same answer.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from onboarding.app.knowledge.extract.compose import render_document
from onboarding.app.knowledge.pipeline import ingest_document
from onboarding.app.worker.payload import JobPayloadError
from onboarding.core.extraction import accept
from onboarding.core.models import Accepted, ExtractedDocument, Rejected
from onboarding.ports import (
    AuditLog,
    BlobStore,
    DocumentRef,
    Embedder,
    Extraction,
    ExtractionCache,
    ExtractionProfile,
    ExtractionRecord,
    KnowledgeWriter,
)

INDEXED = "indexed"
REJECTED = "rejected"


class DocumentExtractor:
    def __init__(
        self,
        *,
        blobs: BlobStore,
        extraction: Extraction,
        cache: ExtractionCache,
        writer: KnowledgeWriter,
        embedder: Embedder,
        schema_path: Path,
        profile: ExtractionProfile,
        audit: AuditLog,
    ) -> None:
        self._blobs = blobs
        self._extraction = extraction
        self._cache = cache
        self._writer = writer
        self._embedder = embedder
        self._schema_path = schema_path
        self._profile = profile
        self._audit = audit

    @property
    def profile(self) -> ExtractionProfile:
        return self._profile

    async def run(self, payload: Mapping[str, object]) -> None:
        blob_id = _text(payload, "blob_id")
        filename = _text(payload, "filename")
        media_type = _text(payload, "media_type")
        metadata = _metadata(payload.get("metadata"))

        cached = await self._cache.load(blob_id, self._profile.fingerprint())
        if cached is not None and cached.status == INDEXED:
            await self._audit.record(
                "document_extraction_cached",
                blob=blob_id,
                document=cached.document_id,
                profile=self._profile.name,
            )
            return

        content = await self._blobs.read(blob_id)
        if content is None:
            raise JobPayloadError(f"blob {blob_id!r} is gone")

        document = await self._extraction.extract(
            content,
            DocumentRef(blob_id=blob_id, filename=filename, media_type=media_type),
            self._profile,
        )
        outcome = accept(document, self._profile.acceptance)
        if isinstance(outcome, Rejected):
            await self._record_refusal(blob_id, document, outcome)
            return

        markdown = render_document(metadata, outcome.text)
        indexed = await ingest_document(
            text=markdown,
            source=f"upload:{blob_id}",
            schema_path=self._schema_path,
            writer=self._writer,
            embedder=self._embedder,
        )
        await self._cache.save(_record(self._profile, document, outcome, markdown, indexed.id))
        await self._audit.record(
            "document_extracted",
            blob=blob_id,
            document=indexed.id,
            chunks=indexed.chunks,
            engine=document.engine,
            route=document.route.value,
            pages=outcome.pages,
            min_confidence=round(outcome.min_confidence, 4),
            profile=self._profile.name,
        )

    async def _record_refusal(
        self, blob_id: str, document: ExtractedDocument, rejection: Rejected
    ) -> None:
        await self._cache.save(
            ExtractionRecord(
                content_hash=document.content_hash,
                profile_hash=self._profile.fingerprint(),
                status=REJECTED,
                reason=rejection.reason.value,
                engine=document.engine,
                route=document.route.value,
                pages=len(document.pages),
                min_confidence=0.0,
            )
        )
        await self._audit.record(
            "document_rejected",
            blob=blob_id,
            reason=rejection.reason.value,
            page=rejection.page,
            detail=rejection.detail[:200],
            engine=document.engine,
            route=document.route.value,
            profile=self._profile.name,
        )


def _record(
    profile: ExtractionProfile,
    document: ExtractedDocument,
    outcome: Accepted,
    markdown: str,
    document_id: str,
) -> ExtractionRecord:
    return ExtractionRecord(
        content_hash=document.content_hash,
        profile_hash=profile.fingerprint(),
        status=INDEXED,
        reason=None,
        engine=document.engine,
        route=document.route.value,
        pages=outcome.pages,
        min_confidence=round(outcome.min_confidence, 4),
        markdown=markdown,
        document_id=document_id,
    )


def _text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise JobPayloadError(f"{key} must be a non-empty string")
    return value


def _metadata(value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        raise JobPayloadError("metadata must be a non-empty object")
    if not all(isinstance(key, str) and key for key in value):
        raise JobPayloadError("metadata keys must be non-empty strings")
    return cast(dict[str, Any], value)

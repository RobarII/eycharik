"""The ``index_document`` job: an uploaded markdown document becomes corpus chunks.

The API validates the frontmatter before it accepts the upload. This job validates it again on the
worker side, because a job payload is untrusted input too, then embeds and writes through the same
``ingest_document`` choke point the corpus directory uses.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from onboarding.app.knowledge.ingest import CorpusError
from onboarding.app.knowledge.markdown import MARKDOWN_PROFILE_HASH
from onboarding.app.knowledge.pipeline import ingest_document
from onboarding.app.worker.extract import INDEXED, REJECTED
from onboarding.app.worker.payload import JobPayloadError
from onboarding.ports import (
    AuditLog,
    BlobStore,
    Embedder,
    ExtractionCache,
    ExtractionRecord,
    KnowledgeWriter,
)

ENGINE = "markdown"
ROUTE = "text"


class DocumentIndexer:
    def __init__(
        self,
        *,
        blobs: BlobStore,
        cache: ExtractionCache,
        writer: KnowledgeWriter,
        embedder: Embedder,
        schema_path: Path,
        audit: AuditLog,
    ) -> None:
        self._blobs = blobs
        self._cache = cache
        self._writer = writer
        self._embedder = embedder
        self._schema_path = schema_path
        self._audit = audit

    async def run(self, payload: Mapping[str, object]) -> None:
        blob_id = _text(payload, "blob_id")
        cached = await self._cache.load(blob_id, MARKDOWN_PROFILE_HASH)
        if cached is not None and cached.status in {INDEXED, REJECTED}:
            await self._audit.record(
                "document_index_cached",
                blob=blob_id,
                document=cached.document_id,
            )
            return

        content = await self._blobs.read(blob_id)
        if content is None:
            raise JobPayloadError(f"blob {blob_id!r} is gone")
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as error:
            await self._reject(blob_id, f"not utf-8: {error}")
            return

        try:
            indexed = await ingest_document(
                text=text,
                source=f"upload:{blob_id}",
                schema_path=self._schema_path,
                writer=self._writer,
                embedder=self._embedder,
            )
        except CorpusError as error:
            await self._reject(blob_id, str(error))
            return

        await self._cache.save(
            ExtractionRecord(
                content_hash=blob_id,
                profile_hash=MARKDOWN_PROFILE_HASH,
                status=INDEXED,
                reason=None,
                engine=ENGINE,
                route=ROUTE,
                pages=0,
                min_confidence=1.0,
                markdown=text,
                document_id=indexed.id,
            )
        )
        await self._audit.record(
            "document_indexed",
            blob=blob_id,
            document=indexed.id,
            chunks=indexed.chunks,
            engine=ENGINE,
            route=ROUTE,
        )

    async def _reject(self, blob_id: str, detail: str) -> None:
        await self._cache.save(
            ExtractionRecord(
                content_hash=blob_id,
                profile_hash=MARKDOWN_PROFILE_HASH,
                status=REJECTED,
                reason="invalid_document",
                engine=ENGINE,
                route=ROUTE,
                pages=0,
                min_confidence=0.0,
            )
        )
        await self._audit.record(
            "document_rejected",
            blob=blob_id,
            reason="invalid_document",
            detail=detail[:200],
            engine=ENGINE,
            route=ROUTE,
        )


def _text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise JobPayloadError(f"{key} must be a non-empty string")
    return value

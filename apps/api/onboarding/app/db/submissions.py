"""Atomic upload acceptance: bytes, visible status, and the job that will index them.

A recruiter must never see ``queued`` for a blob that no job will read, or a job for a blob that
was never stored. One transaction makes those states inseparable.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping

from sqlalchemy.dialects.postgresql import insert

from onboarding.app.db.blobs import MAX_BLOB_BYTES, BlobTooLargeError, safe_filename
from onboarding.app.db.models import ExtractionRow, FileRow, JobRow
from onboarding.app.db.session import Database
from onboarding.ports import KnowledgeSubmission

TERMINAL = frozenset({"indexed", "rejected"})


class PostgresKnowledgeSubmitter:
    def __init__(self, database: Database, *, max_bytes: int = MAX_BLOB_BYTES) -> None:
        self._database = database
        self._max_bytes = max_bytes

    async def submit(
        self,
        *,
        content: bytes,
        filename: str,
        media_type: str,
        metadata: Mapping[str, object],
        job_kind: str,
        profile_hash: str | None = None,
    ) -> KnowledgeSubmission:
        if not content:
            raise ValueError("empty upload")
        if len(content) > self._max_bytes:
            raise BlobTooLargeError(f"{len(content)} bytes exceeds {self._max_bytes}")

        digest = hashlib.sha256(content).hexdigest()
        async with self._database.session() as session:
            await session.execute(
                insert(FileRow)
                .values(
                    id=digest,
                    filename=safe_filename(filename),
                    media_type=media_type[:120],
                    size=len(content),
                    content=content,
                )
                .on_conflict_do_nothing(index_elements=[FileRow.id])
            )

            if profile_hash is not None:
                created = await session.scalar(
                    insert(ExtractionRow)
                    .values(
                        content_hash=digest,
                        profile_hash=profile_hash,
                        status="queued",
                        reason=None,
                        engine="pending",
                        route="pending",
                        pages=0,
                        min_confidence=0.0,
                    )
                    .on_conflict_do_nothing(
                        index_elements=[ExtractionRow.content_hash, ExtractionRow.profile_hash]
                    )
                    .returning(ExtractionRow.content_hash)
                )
                if created is None:
                    # Indexed, rejected, or already queued: this upload has been seen before.
                    return KnowledgeSubmission(content_hash=digest, queued=False)

            session.add(
                JobRow(
                    kind=job_kind,
                    payload={
                        "blob_id": digest,
                        "filename": safe_filename(filename),
                        "media_type": media_type,
                        "metadata": dict(metadata),
                    },
                )
            )
        return KnowledgeSubmission(content_hash=digest, queued=True)

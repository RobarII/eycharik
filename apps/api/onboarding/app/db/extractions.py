"""Extraction results, cached by (file hash, profile hash).

Recognition is expensive and deterministic for a fixed profile, so the same file is never read
twice with the same configuration. Two independent hashes mean a profile change re-reads the file
instead of silently reusing a result produced by different thresholds.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from onboarding.app.db.models import ExtractionRow
from onboarding.app.db.session import Database
from onboarding.ports import ExtractionRecord


class PostgresExtractionCache:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def load(self, content_hash: str, profile_hash: str) -> ExtractionRecord | None:
        async with self._database.session() as session:
            row = await session.scalar(
                select(ExtractionRow).where(
                    ExtractionRow.content_hash == content_hash,
                    ExtractionRow.profile_hash == profile_hash,
                )
            )
            return None if row is None else _record(row)

    async def load_latest(self, content_hash: str) -> ExtractionRecord | None:
        """The newest record for a file, whichever profile produced it. Used by the cabinet."""
        async with self._database.session() as session:
            row = await session.scalar(
                select(ExtractionRow)
                .where(ExtractionRow.content_hash == content_hash)
                .order_by(ExtractionRow.updated_at.desc())
                .limit(1)
            )
            return None if row is None else _record(row)

    async def save(self, record: ExtractionRecord) -> None:
        async with self._database.session() as session:
            await session.execute(
                insert(ExtractionRow)
                .values(
                    content_hash=record.content_hash,
                    profile_hash=record.profile_hash,
                    status=record.status,
                    reason=record.reason,
                    engine=record.engine,
                    route=record.route,
                    pages=record.pages,
                    min_confidence=record.min_confidence,
                    markdown=record.markdown,
                    document_id=record.document_id,
                )
                .on_conflict_do_update(
                    index_elements=[ExtractionRow.content_hash, ExtractionRow.profile_hash],
                    set_={
                        "status": record.status,
                        "reason": record.reason,
                        "engine": record.engine,
                        "route": record.route,
                        "pages": record.pages,
                        "min_confidence": record.min_confidence,
                        "markdown": record.markdown,
                        "document_id": record.document_id,
                    },
                )
            )


def _record(row: ExtractionRow) -> ExtractionRecord:
    return ExtractionRecord(
        content_hash=row.content_hash,
        profile_hash=row.profile_hash,
        status=row.status,
        reason=row.reason,
        engine=row.engine,
        route=row.route,
        pages=row.pages,
        min_confidence=row.min_confidence,
        markdown=row.markdown,
        document_id=row.document_id,
    )

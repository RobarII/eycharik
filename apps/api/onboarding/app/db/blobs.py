"""Uploaded bytes, stored in the same Postgres as everything else (ADR 0005).

Content addressing is deliberate: the row id is the SHA-256 of the bytes, so the database itself
enforces "one file, one row". A recruiter who uploads the same regulation twice gets the same blob
id, no second job, and no second recognition.
"""

from __future__ import annotations

import hashlib
from pathlib import PurePosixPath

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from onboarding.app.db.models import FileRow
from onboarding.app.db.session import Database

MAX_BLOB_BYTES = 25 * 1024 * 1024
MAX_FILENAME_CHARS = 300


class BlobTooLargeError(ValueError):
    """The upload exceeds the configured limit; the caller answers 413 before any work happens."""


class PostgresBlobStore:
    def __init__(self, database: Database, *, max_bytes: int = MAX_BLOB_BYTES) -> None:
        self._database = database
        self._max_bytes = max_bytes

    async def put(self, content: bytes, *, filename: str, media_type: str) -> str:
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
                    filename=_safe_name(filename),
                    media_type=media_type[:120],
                    size=len(content),
                    content=content,
                )
                .on_conflict_do_nothing(index_elements=[FileRow.id])
            )
        return digest

    async def read(self, blob_id: str) -> bytes | None:
        async with self._database.session() as session:
            row = await session.scalar(select(FileRow).where(FileRow.id == blob_id))
            return None if row is None else bytes(row.content)


def _safe_name(filename: str) -> str:
    """A filename is user input: keep the last path component and nothing executable."""
    name = PurePosixPath(filename.replace("\\", "/")).name.strip()
    return (name or "upload")[:MAX_FILENAME_CHARS]

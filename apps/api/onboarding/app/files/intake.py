"""Store the documents people send in a chat.

This is the only place that turns an attachment into a row. It runs in the worker, after the
webhook has already answered 200, so a large scan never holds a delivery open.

Rules that matter:

* the messenger token is the idempotency key — a redelivery cannot store a passport twice;
* the declared or actual size is capped before anything is read into memory;
* the media type is sniffed from the bytes, never trusted from the messenger or the filename;
* the bytes are encrypted with the deployment key; without a key the row records the attempt but
  keeps no document;
* a failure is recorded, not raised: the scenario step has already moved, and replaying the job
  would replay the conversation.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from onboarding.app.db.models import InboundFileRow
from onboarding.app.db.session import Database
from onboarding.app.files.crypto import decrypt, encrypt
from onboarding.app.files.errors import FileNotAvailableError, FileTooLargeError
from onboarding.core.models import Address
from onboarding.ports import AuditLog, FileFetcher, InboundFile

MAX_FILENAME = 120
_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "application/pdf": ".pdf",
}
# Formats a recruiter can open and that cannot execute. Anything else is refused, not stored.
ALLOWED_TYPES = frozenset(_EXTENSIONS)
_UNSAFE = re.compile(r"[^\w.\- ()\[\]]+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class StoredFile:
    """What one save attempt produced. ``status`` is ``stored``, ``rejected`` or ``failed``."""

    id: str
    filename: str
    status: str
    error: str | None = None


def sniff_media_type(data: bytes) -> str | None:
    """The format the bytes actually are, independent of any name the messenger supplied."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[4:8] == b"ftyp" and data[8:12] in {b"heic", b"heix", b"hevc", b"mif1", b"msf1"}:
        return "image/heic"
    return None


def safe_filename(name: str | None, media_type: str, token: str) -> str:
    """A name a browser can save without escaping out of the download directory."""
    base = (name or "").replace("\\", "/").rsplit("/", 1)[-1]
    base = _UNSAFE.sub("_", base).strip(" .")
    if not base:
        base = f"file-{token[:8] or 'document'}{_EXTENSIONS[media_type]}"
    if len(base) > MAX_FILENAME:
        stem, dot, suffix = base.rpartition(".")
        base = stem[: MAX_FILENAME - len(suffix) - 1] + dot + suffix if dot else base[:MAX_FILENAME]
    return base


class InboundFileIntake:
    """Downloads, validates, encrypts and records each attachment of one delivery."""

    def __init__(
        self,
        *,
        database: Database,
        fetcher: FileFetcher,
        audit: AuditLog,
        key: bytes | None,
        max_bytes: int,
    ) -> None:
        self._database = database
        self._fetcher = fetcher
        self._audit = audit
        self._key = key
        self._max_bytes = max_bytes

    async def save(
        self, employee_id: str, address: Address, files: Sequence[InboundFile]
    ) -> list[StoredFile]:
        stored: list[StoredFile] = []
        for file in files:
            stored.append(await self._save_one(employee_id, address, file))
        return stored

    async def _save_one(self, employee_id: str, address: Address, file: InboundFile) -> StoredFile:
        async with self._database.session() as session:
            existing = await session.scalar(
                select(InboundFileRow).where(
                    InboundFileRow.channel == address.channel.value,
                    InboundFileRow.chat_id == int(address.chat_id),
                    InboundFileRow.token == file.token,
                )
            )
            if existing is not None and existing.status == "stored":
                return StoredFile(
                    id=str(existing.id),
                    filename=existing.filename,
                    status=existing.status,
                )

        try:
            data = await self._download(file)
        except (FileTooLargeError, FileNotAvailableError) as error:
            return await self._record(
                employee_id, address, file, status="rejected", error=str(error)
            )
        except Exception as error:  # noqa: BLE001 - a CDN outage must not replay the conversation
            return await self._record(
                employee_id,
                address,
                file,
                status="failed",
                error=f"{type(error).__name__}: {error}"[:200],
            )

        media_type = sniff_media_type(data)
        if media_type is None or media_type not in ALLOWED_TYPES:
            return await self._record(
                employee_id, address, file, status="rejected", error="unsupported_type"
            )

        return await self._record(
            employee_id,
            address,
            file,
            status="stored",
            media_type=media_type,
            data=data,
        )

    async def _download(self, file: InboundFile) -> bytes:
        if file.size is not None and file.size > self._max_bytes:
            raise FileTooLargeError("declared_size")
        if file.url is None:
            raise FileNotAvailableError("no_url")
        data = await self._fetcher.fetch(file)
        if not data:
            raise FileNotAvailableError("empty")
        if len(data) > self._max_bytes:
            raise FileTooLargeError("actual_size")
        return data

    async def _record(
        self,
        employee_id: str,
        address: Address,
        file: InboundFile,
        *,
        status: str,
        error: str | None = None,
        media_type: str | None = None,
        data: bytes | None = None,
    ) -> StoredFile:
        resolved_type = media_type or (file.media_type or "application/octet-stream")
        extension_type = resolved_type if resolved_type in _EXTENSIONS else "application/pdf"
        filename = safe_filename(file.filename, extension_type, file.token)
        payload: bytes | None = None
        if data is not None and self._key is not None:
            payload = encrypt(self._key, data)
        elif data is not None:
            status = "unavailable"
            error = "no_key"

        async with self._database.session() as session:
            row = await session.scalar(
                select(InboundFileRow).where(
                    InboundFileRow.channel == address.channel.value,
                    InboundFileRow.chat_id == int(address.chat_id),
                    InboundFileRow.token == file.token,
                )
            )
            if row is None:
                row = InboundFileRow(
                    employee_id=employee_id,
                    channel=address.channel.value,
                    chat_id=int(address.chat_id),
                    token=file.token,
                )
                session.add(row)
            row.filename = filename
            row.media_type = resolved_type
            row.size = len(data) if data is not None else (file.size or 0)
            row.sha256 = hashlib.sha256(data).hexdigest() if data is not None else ""
            row.content = payload
            row.status = status
            row.error = error
            try:
                await session.flush()
            except IntegrityError:
                # Two workers raced on the same token; the first row is the record of truth.
                await session.rollback()
                row = await session.scalar(
                    select(InboundFileRow).where(
                        InboundFileRow.channel == address.channel.value,
                        InboundFileRow.chat_id == int(address.chat_id),
                        InboundFileRow.token == file.token,
                    )
                )
                if row is None:
                    raise
            file_id = str(row.id)

        await self._audit.record(
            "file_stored" if status == "stored" else "file_not_stored",
            employee_id=employee_id,
            file_id=file_id,
            status=status,
            media_type=resolved_type,
            size=len(data) if data is not None else (file.size or 0),
            error=error,
        )
        return StoredFile(id=file_id, filename=filename, status=status, error=error)


def decrypt_file(key: bytes | None, blob: bytes | None) -> bytes | None:
    """The bytes a recruiter downloads, or ``None`` when the row holds no document."""
    if blob is None or key is None:
        return None
    return decrypt(key, blob)

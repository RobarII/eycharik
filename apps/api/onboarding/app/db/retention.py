"""Apply the retention window to questions, files, outbound messages, and audit rows.

Questions disappear: their text is the employee's own words and has no value after the window.
Uploaded bytes disappear for the same reason: the accepted markdown became a document, and keeping
a photograph of a passport scan forever is a liability, not an archive. Outbound messages are a
queue, not an archive: a delivered row is deleted after the window, and an undelivered row that is
older than the window will never be useful. Audit rows stay as a skeleton, because counts and
incident timelines must remain traceable; only the personal fragments are removed and the row is
marked ``redacted``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.engine import CursorResult

from onboarding.app.db.models import AuditRow, FileRow, MessageRow, QuestionRow
from onboarding.app.db.session import Database
from onboarding.core.retention import cutoff, redact_fields
from onboarding.ports import Clock


@dataclass(frozen=True, slots=True)
class PurgeResult:
    questions_deleted: int
    files_deleted: int
    messages_deleted: int
    audit_redacted: int


class RetentionPurger:
    def __init__(self, database: Database, clock: Clock, *, days: int, batch: int = 1000) -> None:
        if days < 1:
            raise ValueError("retention days must be at least 1")
        self._database = database
        self._clock = clock
        self._days = days
        self._batch = batch

    async def run_once(self) -> PurgeResult:
        oldest = cutoff(self._clock.now(), self._days)
        async with self._database.session() as session:
            deleted = await session.execute(
                delete(QuestionRow).where(QuestionRow.asked_at < oldest)
            )
            files = await session.execute(
                delete(FileRow).where(FileRow.created_at < oldest)
            )
            messages_deleted = 0
            while True:
                expired = (
                    select(MessageRow.id)
                    .where(
                        or_(
                            and_(
                                MessageRow.status == "sent",
                                MessageRow.sent_at < oldest,
                            ),
                            and_(
                                MessageRow.status.in_(("pending", "sending", "failed")),
                                MessageRow.created_at < oldest,
                            ),
                        )
                    )
                    .limit(self._batch)
                )
                purged = await session.execute(
                    delete(MessageRow).where(MessageRow.id.in_(expired))
                )
                batch = int(cast(CursorResult[Any], purged).rowcount or 0)
                messages_deleted += batch
                if batch < self._batch:
                    break
            audits = (
                await session.scalars(
                    select(AuditRow)
                    .where(AuditRow.at < oldest)
                    .order_by(AuditRow.id)
                    .limit(self._batch)
                )
            ).all()
            redacted = 0
            for audit in audits:
                cleaned = redact_fields(audit.fields)
                if cleaned != audit.fields:
                    audit.fields = cleaned
                    redacted += 1

            questions_deleted = int(cast(CursorResult[Any], deleted).rowcount or 0)
            files_deleted = int(cast(CursorResult[Any], files).rowcount or 0)
            if questions_deleted or files_deleted or messages_deleted or redacted:
                session.add(
                    AuditRow(
                        name="retention_purged",
                        fields={
                            "questions_deleted": questions_deleted,
                            "files_deleted": files_deleted,
                            "messages_deleted": messages_deleted,
                            "audit_redacted": redacted,
                            "cutoff": oldest.isoformat(),
                        },
                    )
                )
            return PurgeResult(
                questions_deleted=questions_deleted,
                files_deleted=files_deleted,
                messages_deleted=messages_deleted,
                audit_redacted=redacted,
            )

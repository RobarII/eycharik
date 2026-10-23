"""Postgres-backed job queue.

``FOR UPDATE SKIP LOCKED`` gives several workers disjoint batches without a broker. Jobs are
enqueued in the same transaction as the state that justifies them.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from onboarding.app.db.models import JobRow
from onboarding.app.db.session import Database
from onboarding.ports import ClaimedJob

MAX_ATTEMPTS = 5


class JobQueue:
    def __init__(self, database: Database, *, batch: int = 10) -> None:
        self._database = database
        self._batch = batch

    @staticmethod
    async def enqueue(
        session: AsyncSession, kind: str, payload: dict[str, object]
    ) -> None:
        session.add(JobRow(kind=kind, payload=payload))

    async def claim(self) -> tuple[ClaimedJob, ...]:
        claimable = (
            select(JobRow.id)
            .where(JobRow.status == "pending", JobRow.available_at <= func.now())
            .order_by(JobRow.id)
            .limit(self._batch)
            .with_for_update(skip_locked=True)
        )
        async with self._database.session() as session:
            rows = await session.scalars(
                update(JobRow)
                .where(JobRow.id.in_(claimable))
                .values(status="running")
                .returning(JobRow)
            )
            return tuple(
                ClaimedJob(
                    id=row.id, kind=row.kind, payload=row.payload, attempts=row.attempts
                )
                for row in rows
            )

    async def complete(self, job: ClaimedJob) -> None:
        async with self._database.session() as session:
            await session.execute(
                update(JobRow)
                .where(JobRow.id == job.id)
                .values(status="done", last_error=None)
            )

    async def fail(self, job: ClaimedJob, error: Exception) -> None:
        attempts = job.attempts + 1
        async with self._database.session() as session:
            await session.execute(
                update(JobRow)
                .where(JobRow.id == job.id)
                .values(
                    status="failed" if attempts >= MAX_ATTEMPTS else "pending",
                    attempts=attempts,
                    available_at=func.now() + timedelta(seconds=10 * attempts),
                    last_error=str(error)[:500],
                )
            )

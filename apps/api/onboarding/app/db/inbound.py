"""The database side of inbound acceptance.

Deduplication and job insertion are one transaction. A messenger can retry a delivery forever; the
``events`` primary key decides, not the HTTP route.
"""

from __future__ import annotations

from collections.abc import Mapping

from onboarding.app.db.queue import JobQueue
from onboarding.app.db.repos import SqlEventDeduper
from onboarding.app.db.session import Database


class SqlInboundSink:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def accept(
        self, *, dedupe_key: str, job_kind: str, payload: Mapping[str, object]
    ) -> bool:
        async with self._database.session() as session:
            if not await SqlEventDeduper(session).first_sighting(dedupe_key):
                return False
            await JobQueue.enqueue(session, job_kind, dict(payload))
        return True

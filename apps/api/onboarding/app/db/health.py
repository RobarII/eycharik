"""Readiness is one round trip to the only stateful dependency."""

from __future__ import annotations

from sqlalchemy import text

from onboarding.app.db.session import Database


class DatabaseHealth:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def ping(self) -> bool:
        try:
            async with self._database.session() as session:
                await session.execute(text("select 1"))
        except Exception:  # noqa: BLE001 - readiness must answer, not raise
            return False
        return True

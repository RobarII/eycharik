"""Turn due run reminders into timeout jobs.

Clearing the reminder and enqueuing the job happen in one statement pair inside one transaction:
either both are visible or neither is, so a crash cannot drop a reminder silently.
"""

from __future__ import annotations

from sqlalchemy import func, update

from onboarding.app.db.models import JobRow, RunRow
from onboarding.app.db.session import Database


class ReminderScheduler:
    def __init__(self, database: Database, *, batch: int = 50) -> None:
        self._database = database
        self._batch = batch

    async def tick(self) -> int:
        async with self._database.session() as session:
            due = (
                update(RunRow)
                .where(
                    RunRow.status == "active",
                    RunRow.reminder_at.is_not(None),
                    RunRow.reminder_at <= func.now(),
                )
                .values(reminder_at=None)
                .returning(RunRow.id, RunRow.employee_id, RunRow.channel, RunRow.chat_id)
                .execution_options(synchronize_session=False)
            )
            rows = (await session.execute(due)).all()
            for run_id, employee_id, channel, chat_id in rows[: self._batch]:
                session.add(
                    JobRow(
                        kind="timeout",
                        payload={
                            "run_id": str(run_id),
                            "employee_id": employee_id,
                            "channel": channel,
                            "chat_id": chat_id,
                        },
                    )
                )
        return len(rows)

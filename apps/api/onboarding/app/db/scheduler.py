"""Turn due run reminders into timeout jobs.

Clearing the reminder and enqueuing the job happen in one statement pair inside one transaction:
either both are visible or neither is, so a crash cannot drop a reminder silently.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, update

from onboarding.app.db.models import JobRow, RunRow
from onboarding.app.db.session import Database
from onboarding.app.jobs import SEND_STEP
from onboarding.core.quiet_hours import QuietHours


class ReminderScheduler:
    def __init__(
        self,
        database: Database,
        *,
        batch: int = 50,
        quiet: QuietHours | None = None,
        now: datetime | None = None,
    ) -> None:
        self._database = database
        self._batch = batch
        # A proactive message is the bot's own idea, so quiet hours hold it until morning. Answers
        # to a live person never pass here and are never delayed.
        self._quiet = quiet
        self._now = now

    async def tick(self) -> int:
        available_at = self._available_at()
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
                        available_at=available_at,
                        payload={
                            "run_id": str(run_id),
                            "employee_id": employee_id,
                            "channel": channel,
                            "chat_id": chat_id,
                        },
                    )
                )

            due_sends = (
                update(RunRow)
                .where(
                    RunRow.status == "active",
                    RunRow.next_send_at.is_not(None),
                    RunRow.next_send_at <= func.now(),
                )
                .values(next_send_at=None)
                .returning(
                    RunRow.id,
                    RunRow.employee_id,
                    RunRow.channel,
                    RunRow.chat_id,
                    RunRow.next_send_step,
                )
                .execution_options(synchronize_session=False)
            )
            send_rows = (await session.execute(due_sends)).all()
            for run_id, employee_id, channel, chat_id, step_id in send_rows[: self._batch]:
                if step_id is None:
                    continue
                session.add(
                    JobRow(
                        kind=SEND_STEP,
                        available_at=available_at,
                        payload={
                            "run_id": str(run_id),
                            "employee_id": employee_id,
                            "channel": channel,
                            "chat_id": chat_id,
                            "step_id": step_id,
                        },
                    )
                )
        return len(rows) + len(send_rows)

    def _available_at(self) -> datetime | None:
        """Jobs wait for the morning instead of waking the person up.

        ``None`` keeps the column default: the job is available the moment it is written.
        """
        if self._quiet is None:
            return None
        return self._quiet.next_allowed(self._now or datetime.now(UTC))

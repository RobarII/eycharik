"""Employee directory and channel identity links, backed by Postgres.

``employees`` holds the person; ``channel_identities`` holds the messenger accounts that person
speaks through. The link is the access gate: an unlinked account gets no run (ADR 0019).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from onboarding.app.db.models import ChannelIdentityRow, EmployeeRow
from onboarding.app.db.session import Database
from onboarding.core.models import Channel, EmployeeId, EmployeeProfile


class SqlDirectory:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def profile(self, employee_id: EmployeeId) -> EmployeeProfile | None:
        async with self._database.session() as session:
            row = await session.scalar(
                select(EmployeeRow).where(
                    EmployeeRow.id == str(employee_id),
                    EmployeeRow.status == "active",
                )
            )
        if row is None:
            return None
        return EmployeeProfile(
            employee_id=EmployeeId(row.id),
            name=row.name,
            role=row.role,
            department=row.department,
            started_at=row.started_at,
            audience=tuple(row.audience),
            recruiter_id=row.recruiter_id,
            scenario_id=row.scenario_id,
        )

    async def resolve(self, channel: Channel, external_id: str) -> EmployeeId | None:
        """The employee behind one messenger account, and only an active one."""
        async with self._database.session() as session:
            employee_id = await session.scalar(
                select(ChannelIdentityRow.employee_id)
                .join(EmployeeRow, EmployeeRow.id == ChannelIdentityRow.employee_id)
                .where(
                    ChannelIdentityRow.channel == channel.value,
                    ChannelIdentityRow.external_id == external_id,
                    EmployeeRow.status == "active",
                )
            )
        return EmployeeId(employee_id) if employee_id is not None else None

    async def link(self, channel: Channel, external_id: str, employee_id: EmployeeId) -> None:
        """Bind an account to an employee. Re-linking the same pair is a no-op."""
        async with self._database.session() as session:
            await session.execute(
                insert(ChannelIdentityRow)
                .values(
                    channel=channel.value,
                    external_id=external_id,
                    employee_id=str(employee_id),
                )
                .on_conflict_do_update(
                    index_elements=[ChannelIdentityRow.channel, ChannelIdentityRow.external_id],
                    set_={"employee_id": str(employee_id)},
                )
            )

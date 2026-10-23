"""Employee directory backed by the ``employees`` table."""

from __future__ import annotations

from onboarding.app.db.models import EmployeeRow
from onboarding.app.db.session import Database
from onboarding.core.models import EmployeeId, EmployeeProfile


class SqlDirectory:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def profile(self, employee_id: EmployeeId) -> EmployeeProfile | None:
        async with self._database.session() as session:
            row = await session.get(EmployeeRow, str(employee_id))
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
        )

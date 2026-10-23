"""Employee lifecycle and retention.

An employee who leaves stops being a subject of new onboarding, but the row stays so a reporting
count and the audit log still make sense. ``left_at`` is the moment the cabinet removed them, and
the retention purge uses it as the earliest possible cutoff for their transcript.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_employee_lifecycle"
down_revision: str | None = "0005_question_resolution"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns() -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns("employees")}


def _indexes() -> set[str]:
    return {
            str(index["name"])
            for index in sa.inspect(op.get_bind()).get_indexes("employees")
        }


def upgrade() -> None:
    existing = _columns()
    if "status" not in existing:
        op.add_column(
            "employees",
            sa.Column(
                "status",
                sa.String(length=16),
                nullable=False,
                server_default=sa.text("'active'"),
            ),
        )
    if "left_at" not in existing:
        op.add_column(
            "employees",
            sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "employees_status_idx" not in _indexes():
        op.create_index("employees_status_idx", "employees", ["status"])


def downgrade() -> None:
    if "employees_status_idx" in _indexes():
        op.drop_index("employees_status_idx", table_name="employees")
    existing = _columns()
    if "left_at" in existing:
        op.drop_column("employees", "left_at")
    if "status" in existing:
        op.drop_column("employees", "status")

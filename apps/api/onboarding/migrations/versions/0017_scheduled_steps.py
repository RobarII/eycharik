"""Run rows remember the next delayed step.

A stage is selected by the scenario, but its message must not be shown until ``next_send_at``.
The scheduler clears these columns and enqueues one job in the same transaction, so a crash cannot
silently lose a scheduled stage.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_scheduled_steps"
down_revision: str | None = "0016_inbound_files"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns("runs")}


def upgrade() -> None:
    columns = _columns()
    if "next_send_at" not in columns:
        op.add_column("runs", sa.Column("next_send_at", sa.DateTime(timezone=True), nullable=True))
    if "next_send_step" not in columns:
        op.add_column("runs", sa.Column("next_send_step", sa.String(64), nullable=True))
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("runs")}
    if "runs_send_idx" not in indexes:
        op.create_index(
            "runs_send_idx",
            "runs",
            ["next_send_at"],
            postgresql_where=sa.text("status = 'active'"),
        )


def downgrade() -> None:
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("runs")}
    if "runs_send_idx" in indexes:
        op.drop_index("runs_send_idx", table_name="runs")
    columns = _columns()
    if "next_send_step" in columns:
        op.drop_column("runs", "next_send_step")
    if "next_send_at" in columns:
        op.drop_column("runs", "next_send_at")

"""Survey progress on a run.

A survey is asked one question at a time, so the run must remember which question is current, the
answers collected so far, and whether it is waiting for a reason after a low score. The columns are
JSONB and integers, never a serialized Python object.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_survey_progress"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns() -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns("runs")}


def upgrade() -> None:
    existing = _columns()
    if "answers" not in existing:
        op.add_column(
            "runs",
            sa.Column(
                "answers",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
        )
    if "question_index" not in existing:
        op.add_column(
            "runs",
            sa.Column("question_index", sa.Integer(), nullable=False, server_default=sa.text("0")),
        )
    if "pending_reason" not in existing:
        op.add_column("runs", sa.Column("pending_reason", sa.String(length=64), nullable=True))


def downgrade() -> None:
    existing = _columns()
    if "pending_reason" in existing:
        op.drop_column("runs", "pending_reason")
    if "question_index" in existing:
        op.drop_column("runs", "question_index")
    if "answers" in existing:
        op.drop_column("runs", "answers")

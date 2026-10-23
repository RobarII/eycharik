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


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column(
            "answers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "runs",
        sa.Column("question_index", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column("runs", sa.Column("pending_reason", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("runs", "pending_reason")
    op.drop_column("runs", "question_index")
    op.drop_column("runs", "answers")

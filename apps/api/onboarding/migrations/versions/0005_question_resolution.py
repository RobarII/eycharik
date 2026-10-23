"""A recruiter's reply closes an escalated question.

The reply is sent to the employee through the outbox, but the question row must carry who closed
it, when, and what was promised. The text itself is stored so a second recruiter sees the answer
they would otherwise repeat; it is deleted by the retention purge like the question text.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_question_resolution"
down_revision: str | None = "0004_run_tone"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns() -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns("questions")}


def _indexes() -> set[str]:
    return {
            str(index["name"])
            for index in sa.inspect(op.get_bind()).get_indexes("questions")
        }


def upgrade() -> None:
    existing = _columns()
    if "resolved_at" not in existing:
        op.add_column(
            "questions",
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "resolved_by" not in existing:
        op.add_column(
            "questions",
            sa.Column("resolved_by", sa.String(length=200), nullable=True),
        )
    if "resolution" not in existing:
        op.add_column("questions", sa.Column("resolution", sa.Text(), nullable=True))
    if "questions_answered_idx" not in _indexes():
        op.create_index(
            "questions_answered_idx",
            "questions",
            ["answered", "asked_at"],
        )


def downgrade() -> None:
    if "questions_answered_idx" in _indexes():
        op.drop_index("questions_answered_idx", table_name="questions")
    existing = _columns()
    if "resolution" in existing:
        op.drop_column("questions", "resolution")
    if "resolved_by" in existing:
        op.drop_column("questions", "resolved_by")
    if "resolved_at" in existing:
        op.drop_column("questions", "resolved_at")

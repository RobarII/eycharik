"""A question can be closed without a reply.

The queue exists for questions the assistant could not answer. Some of them are noise, not
knowledge gaps: HR must be able to close such a card without sending anything to the employee.
`declined` keeps that decision distinguishable from a real answer in the cabinet.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_question_declined"
down_revision: str | None = "0017_scheduled_steps"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if "questions" not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns("questions")}


def upgrade() -> None:
    if "declined" in _columns():
        return
    op.add_column(
        "questions",
        sa.Column("declined", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    if "declined" not in _columns():
        return
    op.drop_column("questions", "declined")

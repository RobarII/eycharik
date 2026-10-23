"""Give a question an owner.

A shared queue has no memory: two recruiters open the same card and both write an answer. One
nullable column fixes that without touching the transcript. Existing rows stay unassigned, which is
exactly what "nobody has picked this up yet" means.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_question_assignee"
down_revision: str | None = "0012_kb_index_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    if "assignee" in _columns("questions"):
        return
    op.add_column("questions", sa.Column("assignee", sa.String(200), nullable=True))
    op.create_index(
        "questions_assignee_idx",
        "questions",
        ["assignee", "answered", "asked_at"],
    )


def downgrade() -> None:
    op.drop_index("questions_assignee_idx", table_name="questions")
    op.drop_column("questions", "assignee")

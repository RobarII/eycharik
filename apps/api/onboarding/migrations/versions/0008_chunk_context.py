"""Chunk context for contextual retrieval (ADR 0016).

The column is additive and defaulted: a corpus indexed before this revision keeps reading with an
empty context, and the embedding path falls back to the chunk text. Nothing has to be reindexed
until the contextual pass is switched on.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_chunk_context"
down_revision: str | None = "0007_extraction"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if "kb_chunks" not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns("kb_chunks")}


def upgrade() -> None:
    if "context" in _columns():
        return
    op.add_column(
        "kb_chunks",
        sa.Column("context", sa.Text(), nullable=False, server_default=sa.text("''")),
    )


def downgrade() -> None:
    if "context" not in _columns():
        return
    op.drop_column("kb_chunks", "context")

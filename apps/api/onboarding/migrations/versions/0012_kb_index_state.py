"""Record which embedder built the vector index.

The column is one row, so the upgrade is free on an existing deployment: no backfill, and a missing
row means "older than this revision" rather than "wrong". From here on, an ingest writes its
identity and a search that sees a different one refuses to answer.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_kb_index_state"
down_revision: str | None = "0011_message_images"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "kb_index_state" in _tables():
        return
    op.create_table(
        "kb_index_state",
        sa.Column("id", sa.String(16), primary_key=True),
        sa.Column("embedder", sa.String(120), nullable=False),
        sa.Column("dim", sa.Integer(), nullable=False),
        sa.Column("chunks", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    if "kb_index_state" not in _tables():
        return
    op.drop_table("kb_index_state")

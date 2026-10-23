"""Carry a bundled scenario image through the outbox.

The dispatcher is the only process that talks to MAX, so the asset name has to survive the
transaction that enqueues a message. The name is a file in ``onboarding/assets/scenario``;
the MAX adapter uploads it once and caches the media token.

Revision ID: 0011_message_images
Revises: 0010_messages_retention
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_message_images"
down_revision: str | None = "0010_messages_retention"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    # The baseline is derived from ``Base.metadata``, so a fresh database already has the column.
    if "image" in _columns("messages"):
        return
    op.add_column("messages", sa.Column("image", sa.String(length=80), nullable=True))


def downgrade() -> None:
    if "image" not in _columns("messages"):
        return
    op.drop_column("messages", "image")

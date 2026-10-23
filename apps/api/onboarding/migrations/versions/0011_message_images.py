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


def upgrade() -> None:
    op.add_column("messages", sa.Column("image", sa.String(length=80), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "image")

"""Index the outbox for the retention pass and offboarding.

The purge deletes delivered rows by ``sent_at`` and abandoned rows by ``created_at``; the
dispatcher claims and reclaims by ``(status, available_at)``. Offboarding deletes every message of
a chat. Without these indexes each hourly pass and each offboarding is a sequential scan.

Revision ID: 0010_messages_retention
Revises: 0009_optional_bm25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_messages_retention"
down_revision: str | None = "0009_optional_bm25"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # A delivered row written before ``sent_at`` existed still has to age out by a known clock.
    op.execute(
        "UPDATE messages SET sent_at = created_at "
        "WHERE status = 'sent' AND sent_at IS NULL"
    )
    op.create_index(
        "messages_sent_idx",
        "messages",
        ["sent_at"],
        postgresql_where=sa.text("status = 'sent'"),
    )
    op.create_index(
        "messages_undelivered_idx",
        "messages",
        ["created_at"],
        postgresql_where=sa.text("status in ('pending', 'sending', 'failed')"),
    )
    op.create_index("messages_chat_idx", "messages", ["chat_id"])


def downgrade() -> None:
    op.drop_index("messages_chat_idx", table_name="messages")
    op.drop_index("messages_undelivered_idx", table_name="messages")
    op.drop_index("messages_sent_idx", table_name="messages")

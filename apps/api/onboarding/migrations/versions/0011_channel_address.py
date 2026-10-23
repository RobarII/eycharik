"""Every conversation remembers which messenger it belongs to.

``chat_id`` alone was enough while MAX was the only client. A second channel makes it ambiguous:
the dispatcher cannot pick an API from a number, and two messengers can hand out the same chat id.
The ``channel`` column fixes the address.

``channel_identities`` replaces the implicit rule "a MAX user id is an employee id". A person is
linked to an employee once; the webhook resolves the link, and an unlinked sender is refused
(ADR 0019). The backfill reproduces the old rule exactly, so an existing deployment keeps working.

The baseline is derived from ``Base.metadata`` (see ``0001_initial``), so a fresh database already
has these columns and this table. Every step here is therefore idempotent: it checks the catalog
before it changes anything.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_channel_address"
down_revision: str | None = "0010_messages_retention"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ADDRESSED_TABLES = ("messages", "questions", "runs")
CHANNEL_COLUMN = sa.Column(
    "channel", sa.String(16), nullable=False, server_default=sa.text("'max'")
)


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _columns(table: str) -> set[str]:
    return {str(column["name"]) for column in _inspector().get_columns(table)}


def _indexes(table: str) -> set[str]:
    return {str(index["name"]) for index in _inspector().get_indexes(table)}


def upgrade() -> None:
    inspector = _inspector()
    tables = set(inspector.get_table_names())
    for table in ADDRESSED_TABLES:
        if "channel" not in _columns(table):
            op.add_column(table, CHANNEL_COLUMN)
    # Offboarding deletes a conversation's rows; the address is now a pair.
    if "messages_channel_chat_idx" not in _indexes("messages"):
        op.create_index("messages_channel_chat_idx", "messages", ["channel", "chat_id"])
    if "messages_chat_idx" in _indexes("messages"):
        op.drop_index("messages_chat_idx", table_name="messages")

    if "channel_identities" not in tables:
        op.create_table(
            "channel_identities",
            sa.Column("channel", sa.String(16), primary_key=True),
            sa.Column("external_id", sa.String(64), primary_key=True),
            sa.Column(
                "employee_id",
                sa.String(64),
                sa.ForeignKey("employees.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "linked_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
    if "channel_identities_employee_idx" not in _indexes("channel_identities"):
        op.create_index("channel_identities_employee_idx", "channel_identities", ["employee_id"])

    # Before channels existed, a MAX user id was the employee id. Keep that link working.
    op.execute(
        "INSERT INTO channel_identities (channel, external_id, employee_id) "
        "SELECT 'max', id, id FROM employees ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    if "channel_identities_employee_idx" in _indexes("channel_identities"):
        op.drop_index("channel_identities_employee_idx", table_name="channel_identities")
    if "channel_identities" in set(_inspector().get_table_names()):
        op.drop_table("channel_identities")
    if "messages_chat_idx" not in _indexes("messages"):
        op.create_index("messages_chat_idx", "messages", ["chat_id"])
    if "messages_channel_chat_idx" in _indexes("messages"):
        op.drop_index("messages_channel_chat_idx", table_name="messages")
    for table in ADDRESSED_TABLES:
        if "channel" in _columns(table):
            op.drop_column(table, "channel")

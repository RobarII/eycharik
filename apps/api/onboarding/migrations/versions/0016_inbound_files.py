"""Documents people send in a chat are kept for the recruiter.

The scenario already promises "send the files here", and until now the bot only counted the fact.
``inbound_files`` stores the bytes, encrypted with the deployment key, plus the messenger token that
makes a redelivery idempotent. Offboarding deletes the rows with the rest of the conversation.

The baseline is derived from ``Base.metadata`` (see ``0001_initial``), so a fresh database already
has this table. The upgrade checks the catalog first and is therefore idempotent.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_inbound_files"
down_revision: str | None = "0015_document_body"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def upgrade() -> None:
    if "inbound_files" in set(_inspector().get_table_names()):
        return
    op.create_table(
        "inbound_files",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_id", sa.String(64), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("token", sa.String(300), nullable=False),
        sa.Column("filename", sa.String(300), nullable=False),
        sa.Column("media_type", sa.String(120), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("error", sa.String(200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("channel", "chat_id", "token", name="inbound_files_token_uq"),
    )
    op.create_index("ix_inbound_files_employee_id", "inbound_files", ["employee_id"])


def downgrade() -> None:
    if "inbound_files" in set(_inspector().get_table_names()):
        op.drop_table("inbound_files")

"""Uploaded files and cached extraction results.

Both tables are keyed by content hash, which is what makes the ingestion path idempotent: the same
bytes never produce a second row, a second job, or a second recognition. ``kb_extractions`` is keyed
by the pair (file hash, profile hash) so a changed extraction profile re-reads the file instead of
trusting a result produced by different thresholds.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_extraction"
down_revision: str | None = "0006_employee_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    tables = _tables()
    if "kb_files" not in tables:
        op.create_table(
            "kb_files",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("filename", sa.String(length=300), nullable=False),
            sa.Column("media_type", sa.String(length=120), nullable=False),
            sa.Column("size", sa.Integer(), nullable=False),
            sa.Column("content", sa.LargeBinary(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
    if "kb_extractions" not in tables:
        op.create_table(
            "kb_extractions",
            sa.Column("content_hash", sa.String(length=64), primary_key=True),
            sa.Column("profile_hash", sa.String(length=64), primary_key=True),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("reason", sa.String(length=32), nullable=True),
            sa.Column("engine", sa.String(length=32), nullable=False),
            sa.Column("route", sa.String(length=16), nullable=False),
            sa.Column("pages", sa.Integer(), nullable=False),
            sa.Column("min_confidence", sa.Float(), nullable=False),
            sa.Column("markdown", sa.Text(), nullable=True),
            sa.Column("document_id", sa.String(length=200), nullable=True),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )


def downgrade() -> None:
    tables = _tables()
    if "kb_extractions" in tables:
        op.drop_table("kb_extractions")
    if "kb_files" in tables:
        op.drop_table("kb_files")

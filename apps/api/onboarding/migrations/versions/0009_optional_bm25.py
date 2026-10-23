"""Optional BM25 index (ADR 0012 experiment).

The deployment image is plain `pgvector/pgvector:pg16`, so the extension is not available there and
this migration must be a no-op: migrations stay runnable on every environment. On a ParadeDB image
the index is created and the knowledge base adds BM25 as a third ranking list, off by default
(`BM25_ENABLED`).

The Russian stemmer keeps the index aligned with the `ts_rank_cd` branch instead of comparing raw
word forms. Re-run this migration after a corpus reindex: `paradedb` indexes new rows on insert, so
a reindex is enough and no separate rebuild step exists.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_optional_bm25"
down_revision: str | None = "0008_chunk_context"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "kb_chunks_bm25_idx"


def _available() -> bool:
    found = op.get_bind().execute(
        sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'pg_search'")
    )
    return found.scalar() is not None


def upgrade() -> None:
    if not _available():
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_search")
    op.execute(
        f"CREATE INDEX IF NOT EXISTS {INDEX_NAME} ON kb_chunks "
        "USING paradedb (id, (text::pdb.simple('stemmer=russian'))) "
        "WITH (key_field='id')"
    )


def downgrade() -> None:
    if not _available():
        return
    op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")

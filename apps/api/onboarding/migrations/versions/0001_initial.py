"""Initial schema.

The baseline is derived from ``Base.metadata`` so it cannot drift from the models on day one.
Later revisions are written by hand and reviewed like code.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from onboarding.app.db.models import Base

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind, checkfirst=True)

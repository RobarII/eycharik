"""Remember the form of address the employee chose.

The tone changes message copy, so it belongs to the run, not to the process that handled the
button. Existing runs stay formal, matching the wording they already received.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_run_tone"
down_revision: str | None = "0003_employee_scenario"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "runs",
        sa.Column(
            "tone",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'formal'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("runs", "tone")

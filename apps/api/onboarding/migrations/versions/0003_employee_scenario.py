"""Let the directory choose the scenario for an employee.

The plant variant of the onboarding scenario is not dead content: an employee row names the
scenario to start. A missing value keeps the office default, so existing rows upgrade in place.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_employee_scenario"
down_revision: str | None = "0002_survey_progress"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "employees",
        sa.Column(
            "scenario_id",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("'onboarding_default'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("employees", "scenario_id")

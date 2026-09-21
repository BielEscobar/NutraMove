"""Persist structural rest-day information on workout days.

Revision ID: 20260920_12
Revises: 20260918_11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260920_12"
down_revision: str | Sequence[str] | None = "20260918_11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workout_days",
        sa.Column("is_rest", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("workout_days", "is_rest")

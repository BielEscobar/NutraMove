"""Rate-limit windows for login, registration, and AI generation.

Revision ID: 20260913_10
Revises: 20260913_09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260913_10"
down_revision: str | Sequence[str] | None = "20260913_09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_windows",
        sa.Column("key_hash", sa.String(length=64), primary_key=True),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("attempts > 0", name="ck_rate_limit_attempts"),
    )
    op.create_index("ix_rate_limit_updated", "rate_limit_windows", ["updated_at"])


def downgrade() -> None:
    op.drop_index("ix_rate_limit_updated", table_name="rate_limit_windows")
    op.drop_table("rate_limit_windows")

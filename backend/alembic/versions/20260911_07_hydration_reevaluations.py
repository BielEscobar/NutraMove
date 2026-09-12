"""hydration_reevaluations

Revision ID: 20260911_07
Revises: 20260911_06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260911_07"
down_revision: str | Sequence[str] | None = "20260911_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reevaluation_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("professional_id", sa.Uuid(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "DIET",
                "WORKOUT",
                "EVOLUTION",
                "DIFFICULTY",
                "OTHER",
                name="reevaluation_category",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("reason", sa.String(length=2000), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "IN_REVIEW",
                "COMPLETED",
                "CANCELLED",
                name="reevaluation_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("professional_response", sa.String(length=2000), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("completed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("cancelled_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status <> 'COMPLETED' OR (professional_response IS NOT NULL AND "
            "length(trim(professional_response)) > 0 AND completed_at IS NOT NULL)",
            name="ck_reevaluation_completion",
        ),
        sa.CheckConstraint(
            "length(trim(reason)) BETWEEN 10 AND 2000", name="ck_reevaluation_reason"
        ),
        sa.ForeignKeyConstraint(["cancelled_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["completed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["professional_id"], ["professionals.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reevaluation_status", "reevaluation_requests", ["status"], unique=False)
    op.create_index(
        "ix_reevaluation_student_created",
        "reevaluation_requests",
        ["student_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "uq_reevaluation_open",
        "reevaluation_requests",
        ["student_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING', 'IN_REVIEW')"),
    )
    op.create_table(
        "water_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("amount_ml", sa.Integer(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount_ml BETWEEN 1 AND 10000", name="ck_water_amount"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_water_student_consumed", "water_records", ["student_id", "consumed_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_water_student_consumed", table_name="water_records")
    op.drop_table("water_records")
    op.drop_index(
        "uq_reevaluation_open",
        table_name="reevaluation_requests",
        postgresql_where=sa.text("status IN ('PENDING', 'IN_REVIEW')"),
    )
    op.drop_index("ix_reevaluation_student_created", table_name="reevaluation_requests")
    op.drop_index("ix_reevaluation_status", table_name="reevaluation_requests")
    op.drop_table("reevaluation_requests")

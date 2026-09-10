"""Create structured students linked to users and professionals.

Revision ID: 20260910_03
Revises: 20260910_02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260910_03"
down_revision: str | Sequence[str] | None = "20260910_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "students",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("professional_id", sa.Uuid(), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("phone", sa.String(40), nullable=True),
        sa.Column("goal_detail", sa.String(500), nullable=True),
        sa.Column("preferred_training_time", sa.String(120), nullable=True),
        sa.Column("work_routine", sa.String(1000), nullable=True),
        sa.Column("meal_schedule", sa.String(1000), nullable=True),
        sa.Column("food_preferences", sa.String(1000), nullable=True),
        sa.Column("food_restrictions", sa.String(1000), nullable=True),
        sa.Column("notes", sa.String(2000), nullable=True),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("height", sa.Float(), nullable=False),
        sa.Column("approximate_water_intake", sa.Float(), nullable=True),
        sa.Column("water_goal", sa.Float(), nullable=True),
        sa.Column("training_frequency", sa.Integer(), nullable=False),
        sa.Column(
            "goal",
            sa.Enum(
                "WEIGHT_LOSS",
                "MUSCLE_GAIN",
                "MAINTENANCE",
                "FITNESS",
                "BODY_RECOMPOSITION",
                "OTHER",
                name="student_goal",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "activity_level",
            sa.Enum(
                "LOW",
                "MODERATE",
                "HIGH",
                name="student_activity_level",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "training_experience",
            sa.Enum(
                "NONE",
                "BEGINNER",
                "INTERMEDIATE",
                "ADVANCED",
                name="student_training_experience",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING_APPROVAL",
                "ACTIVE",
                "INACTIVE",
                "REJECTED",
                name="student_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["professional_id"], ["professionals.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("weight > 0 AND weight < 'Infinity'::float8", name="ck_students_weight"),
        sa.CheckConstraint("height > 0 AND height < 'Infinity'::float8", name="ck_students_height"),
        sa.CheckConstraint("training_frequency BETWEEN 0 AND 7", name="ck_students_frequency"),
        sa.CheckConstraint(
            "water_goal IS NULL OR (water_goal >= 0 AND water_goal < 'Infinity'::float8)",
            name="ck_students_water_goal",
        ),
        sa.CheckConstraint(
            "approximate_water_intake IS NULL OR (approximate_water_intake >= 0 "
            "AND approximate_water_intake < 'Infinity'::float8)",
            name="ck_students_water_intake",
        ),
        sa.CheckConstraint(
            "(goal = 'OTHER' AND goal_detail IS NOT NULL AND length(trim(goal_detail)) > 0) "
            "OR (goal <> 'OTHER' AND goal_detail IS NULL)",
            name="ck_students_goal_detail",
        ),
    )
    op.create_index("ix_students_professional_id", "students", ["professional_id"])


def downgrade() -> None:
    op.drop_index("ix_students_professional_id", table_name="students")
    op.drop_table("students")

"""workout_versions

Revision ID: 20260910_05
Revises: 20260910_04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260910_05"
down_revision: str | Sequence[str] | None = "20260910_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workouts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("professional_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
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
        sa.ForeignKeyConstraint(["professional_id"], ["professionals.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_workouts_professional_id"), "workouts", ["professional_id"], unique=False
    )
    op.create_index(op.f("ix_workouts_student_id"), "workouts", ["student_id"], unique=False)
    op.create_table(
        "workout_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workout_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("edit_revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("goal", sa.String(length=500), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "PENDING_REVIEW",
                "APPROVED",
                "ARCHIVED",
                name="workout_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.Enum(
                "MANUAL",
                "AI_GENERATED",
                name="workout_source",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("next_review_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.String(length=4000), nullable=True),
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
        sa.Column("frequency_per_week", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "status <> 'APPROVED' OR approved_at IS NOT NULL", name="ck_workout_approval_required"
        ),
        sa.CheckConstraint(
            "status NOT IN ('DRAFT', 'PENDING_REVIEW') OR approved_at IS NULL",
            name="ck_workout_draft_approval",
        ),
        sa.CheckConstraint(
            "(approved_by_user_id IS NULL) = (approved_at IS NULL)", name="ck_workout_approval_pair"
        ),
        sa.CheckConstraint("frequency_per_week BETWEEN 1 AND 7", name="ck_workout_frequency"),
        sa.CheckConstraint(
            "next_review_date IS NULL OR start_date IS NULL OR next_review_date >= start_date",
            name="ck_workout_version_dates",
        ),
        sa.CheckConstraint(
            "version_number > 0 AND edit_revision > 0", name="ck_workout_version_numbers"
        ),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workout_id"], ["workouts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workout_id", "version_number", name="uq_workout_version_number"),
    )
    op.create_index(
        op.f("ix_workout_versions_workout_id"), "workout_versions", ["workout_id"], unique=False
    )
    op.create_index(
        "uq_workout_approved",
        "workout_versions",
        ["workout_id"],
        unique=True,
        postgresql_where=sa.text("status = 'APPROVED'"),
    )
    op.create_table(
        "workout_days",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workout_version_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_workout_day_position"),
        sa.ForeignKeyConstraint(
            ["workout_version_id"], ["workout_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workout_version_id", "position"),
    )
    op.create_index(
        op.f("ix_workout_days_workout_version_id"),
        "workout_days",
        ["workout_version_id"],
        unique=False,
    )
    op.create_table(
        "workout_exercises",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workout_day_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("muscle_group", sa.String(length=160), nullable=True),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("instructions", sa.String(length=2000), nullable=True),
        sa.Column("sets", sa.Integer(), nullable=True),
        sa.Column("repetitions", sa.String(length=160), nullable=True),
        sa.Column("load", sa.String(length=160), nullable=True),
        sa.Column("duration", sa.String(length=160), nullable=True),
        sa.Column("rest_seconds", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_workout_exercise_position"),
        sa.CheckConstraint("rest_seconds BETWEEN 0 AND 86400", name="ck_workout_exercise_rest"),
        sa.CheckConstraint("sets BETWEEN 1 AND 100", name="ck_workout_exercise_sets"),
        sa.ForeignKeyConstraint(["workout_day_id"], ["workout_days.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workout_day_id", "position"),
    )
    op.create_index(
        op.f("ix_workout_exercises_workout_day_id"),
        "workout_exercises",
        ["workout_day_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_workout_exercises_workout_day_id"), table_name="workout_exercises")
    op.drop_table("workout_exercises")
    op.drop_index(op.f("ix_workout_days_workout_version_id"), table_name="workout_days")
    op.drop_table("workout_days")
    op.drop_index(
        "uq_workout_approved",
        table_name="workout_versions",
        postgresql_where=sa.text("status = 'APPROVED'"),
    )
    op.drop_index(op.f("ix_workout_versions_workout_id"), table_name="workout_versions")
    op.drop_table("workout_versions")
    op.drop_index(op.f("ix_workouts_student_id"), table_name="workouts")
    op.drop_index(op.f("ix_workouts_professional_id"), table_name="workouts")
    op.drop_table("workouts")

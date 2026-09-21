# ruff: noqa: E501
"""Expanded anamnesis, reevaluation snapshots, and private progress photos.

Revision ID: 20260918_11
Revises: 20260913_10
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260918_11"
down_revision: str | Sequence[str] | None = "20260913_10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    columns: list[sa.Column[Any]] = [
        sa.Column(
            "sex",
            sa.Enum(
                "FEMALE",
                "MALE",
                "OTHER",
                "NOT_INFORMED",
                name="student_sex",
                native_enum=False,
                create_constraint=True,
            ),
        ),
        sa.Column("desired_weight", sa.Float()),
        sa.Column("wake_time", sa.Time()),
        sa.Column("sleep_time", sa.Time()),
        sa.Column("trains_currently", sa.Boolean()),
        sa.Column("training_history", sa.String(1000)),
        sa.Column(
            "training_location",
            sa.Enum(
                "GYM",
                "HOME",
                "CONDOMINIUM",
                "OTHER",
                name="student_training_location",
                native_enum=False,
                create_constraint=True,
            ),
        ),
        sa.Column("available_equipment", sa.String(1000)),
        sa.Column("available_training_days", sa.String(500)),
        sa.Column("training_duration_minutes", sa.Integer()),
        sa.Column("meal_count", sa.Integer()),
        sa.Column(
            "cooking_skill",
            sa.Enum(
                "EASY",
                "MODERATE",
                "ADVANCED",
                name="student_cooking_skill",
                native_enum=False,
                create_constraint=True,
            ),
        ),
        sa.Column("disliked_foods", sa.String(1000)),
        sa.Column("food_allergies", sa.String(1000)),
        sa.Column("weekly_food_budget", sa.Float()),
        sa.Column("food_notes", sa.String(2000)),
        sa.Column("has_injury", sa.Boolean()),
        sa.Column("injury_description", sa.String(2000)),
        sa.Column("physical_limitations", sa.String(2000)),
        sa.Column("medical_restrictions", sa.String(2000)),
    ]
    for column in columns:
        op.add_column("students", column)
    op.create_check_constraint(
        "ck_students_desired_weight",
        "students",
        "desired_weight IS NULL OR (desired_weight > 0 AND desired_weight < 'Infinity'::float8)",
    )
    op.create_check_constraint(
        "ck_students_meal_count", "students", "meal_count IS NULL OR meal_count BETWEEN 1 AND 12"
    )
    op.create_check_constraint(
        "ck_students_training_duration",
        "students",
        "training_duration_minutes IS NULL OR training_duration_minutes BETWEEN 10 AND 360",
    )
    op.create_check_constraint(
        "ck_students_injury_description",
        "students",
        "(has_injury IS NOT TRUE) OR (injury_description IS NOT NULL AND length(trim(injury_description)) > 0)",
    )
    op.add_column(
        "reevaluation_requests", sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()))
    )
    op.create_table(
        "progress_photo_sets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "student_id",
            sa.Uuid(),
            sa.ForeignKey("students.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "reevaluation_id",
            sa.Uuid(),
            sa.ForeignKey("reevaluation_requests.id", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.Column(
            "source",
            sa.Enum(
                "INITIAL",
                "REEVALUATION",
                name="photo_set_source",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("context", sa.String(500)),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_photo_sets_student_created", "progress_photo_sets", ["student_id", "created_at"]
    )
    op.create_table(
        "progress_photos",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "photo_set_id",
            sa.Uuid(),
            sa.ForeignKey("progress_photo_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "position",
            sa.Enum(
                "FRONT", "SIDE", name="photo_position", native_enum=False, create_constraint=True
            ),
            nullable=False,
        ),
        sa.Column("storage_key", sa.String(120), nullable=False, unique=True),
        sa.Column("mime_type", sa.String(40), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("photo_set_id", "position", name="uq_photo_set_position"),
    )
    op.create_index("ix_progress_photos_photo_set_id", "progress_photos", ["photo_set_id"])


def downgrade() -> None:
    op.drop_index("ix_progress_photos_photo_set_id", table_name="progress_photos")
    op.drop_table("progress_photos")
    op.drop_index("ix_photo_sets_student_created", table_name="progress_photo_sets")
    op.drop_table("progress_photo_sets")
    op.drop_column("reevaluation_requests", "snapshot")
    for name in (
        "medical_restrictions",
        "physical_limitations",
        "injury_description",
        "has_injury",
        "food_notes",
        "weekly_food_budget",
        "food_allergies",
        "disliked_foods",
        "cooking_skill",
        "meal_count",
        "training_duration_minutes",
        "available_training_days",
        "available_equipment",
        "training_location",
        "training_history",
        "trains_currently",
        "sleep_time",
        "wake_time",
        "desired_weight",
        "sex",
    ):
        op.drop_column("students", name)

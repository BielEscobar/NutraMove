"""assessments

Revision ID: 20260911_06
Revises: 20260910_05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260911_06"
down_revision: str | Sequence[str] | None = "20260910_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("professional_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_date", sa.Date(), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("height_cm", sa.Float(), nullable=True),
        sa.Column("notes", sa.String(length=4000), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("edit_revision", sa.Integer(), server_default="1", nullable=False),
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
            "height_cm IS NULL OR (height_cm > 0 AND height_cm < 'Infinity'::float8)",
            name="ck_assessment_height",
        ),
        sa.CheckConstraint(
            "weight_kg IS NULL OR (weight_kg > 0 AND weight_kg < 'Infinity'::float8)",
            name="ck_assessment_weight",
        ),
        sa.CheckConstraint("edit_revision > 0", name="ck_assessment_revision"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["professional_id"], ["professionals.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_assessment_student_date",
        "assessments",
        ["student_id", "assessment_date", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessments_professional_id"), "assessments", ["professional_id"], unique=False
    )
    op.create_table(
        "measurements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column(
            "measurement_type",
            sa.Enum(
                "ARM",
                "CHEST",
                "WAIST",
                "ABDOMEN",
                "HIP",
                "THIGH",
                "CALF",
                name="measurement_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "side",
            sa.Enum(
                "LEFT", "RIGHT", name="measurement_side", native_enum=False, create_constraint=True
            ),
            nullable=True,
        ),
        sa.Column("value_cm", sa.Float(), nullable=False),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.CheckConstraint(
            "side IS NULL OR measurement_type IN ('ARM','THIGH','CALF')", name="ck_measurement_side"
        ),
        sa.CheckConstraint(
            "value_cm > 0 AND value_cm < 'Infinity'::float8", name="ck_measurement_value"
        ),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_measurements_assessment_id"), "measurements", ["assessment_id"], unique=False
    )
    op.create_index(
        "uq_measurement_kind",
        "measurements",
        ["assessment_id", "measurement_type", "side"],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_measurement_kind", table_name="measurements", postgresql_nulls_not_distinct=True
    )
    op.drop_index(op.f("ix_measurements_assessment_id"), table_name="measurements")
    op.drop_table("measurements")
    op.drop_index(op.f("ix_assessments_professional_id"), table_name="assessments")
    op.drop_index("ix_assessment_student_date", table_name="assessments")
    op.drop_table("assessments")

"""diet_versions

Revision ID: 20260910_04
Revises: 20260910_03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260910_04"
down_revision: str | Sequence[str] | None = "20260910_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "diets",
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
    op.create_index(op.f("ix_diets_professional_id"), "diets", ["professional_id"], unique=False)
    op.create_index(op.f("ix_diets_student_id"), "diets", ["student_id"], unique=False)
    op.create_table(
        "diet_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("diet_id", sa.Uuid(), nullable=False),
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
                name="diet_status",
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
                name="diet_source",
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
        sa.CheckConstraint(
            "status <> 'APPROVED' OR approved_at IS NOT NULL", name="ck_diet_approval_required"
        ),
        sa.CheckConstraint(
            "status NOT IN ('DRAFT', 'PENDING_REVIEW') OR approved_at IS NULL",
            name="ck_diet_draft_approval",
        ),
        sa.CheckConstraint(
            "(approved_by_user_id IS NULL) = (approved_at IS NULL)", name="ck_diet_approval_pair"
        ),
        sa.CheckConstraint(
            "next_review_date IS NULL OR start_date IS NULL OR next_review_date >= start_date",
            name="ck_diet_version_dates",
        ),
        sa.CheckConstraint(
            "version_number > 0 AND edit_revision > 0", name="ck_diet_version_numbers"
        ),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["diet_id"], ["diets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("diet_id", "version_number", name="uq_diet_version_number"),
    )
    op.create_index(op.f("ix_diet_versions_diet_id"), "diet_versions", ["diet_id"], unique=False)
    op.create_index(
        "uq_diet_approved",
        "diet_versions",
        ["diet_id"],
        unique=True,
        postgresql_where=sa.text("status = 'APPROVED'"),
    )
    op.create_table(
        "diet_meals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("diet_version_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("time", sa.Time(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_meal_position"),
        sa.ForeignKeyConstraint(["diet_version_id"], ["diet_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("diet_version_id", "position"),
    )
    op.create_index(
        op.f("ix_diet_meals_diet_version_id"), "diet_meals", ["diet_version_id"], unique=False
    )
    op.create_table(
        "diet_foods",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("meal_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=False),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "quantity > 0 AND quantity < 'Infinity'::numeric", name="ck_food_quantity"
        ),
        sa.CheckConstraint("position >= 0", name="ck_food_position"),
        sa.ForeignKeyConstraint(["meal_id"], ["diet_meals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("meal_id", "position"),
    )
    op.create_index(op.f("ix_diet_foods_meal_id"), "diet_foods", ["meal_id"], unique=False)
    op.create_table(
        "diet_food_substitutions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("food_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("unit", sa.String(length=40), nullable=True),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "quantity IS NULL OR (quantity > 0 AND quantity < 'Infinity'::numeric)",
            name="ck_substitution_quantity",
        ),
        sa.CheckConstraint("(quantity IS NULL) = (unit IS NULL)", name="ck_substitution_unit"),
        sa.CheckConstraint("position >= 0", name="ck_substitution_position"),
        sa.ForeignKeyConstraint(["food_id"], ["diet_foods.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("food_id", "position"),
    )
    op.create_index(
        op.f("ix_diet_food_substitutions_food_id"),
        "diet_food_substitutions",
        ["food_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_diet_food_substitutions_food_id"), table_name="diet_food_substitutions")
    op.drop_table("diet_food_substitutions")
    op.drop_index(op.f("ix_diet_foods_meal_id"), table_name="diet_foods")
    op.drop_table("diet_foods")
    op.drop_index(op.f("ix_diet_meals_diet_version_id"), table_name="diet_meals")
    op.drop_table("diet_meals")
    op.drop_index(
        "uq_diet_approved",
        table_name="diet_versions",
        postgresql_where=sa.text("status = 'APPROVED'"),
    )
    op.drop_index(op.f("ix_diet_versions_diet_id"), table_name="diet_versions")
    op.drop_table("diet_versions")
    op.drop_index(op.f("ix_diets_student_id"), table_name="diets")
    op.drop_index(op.f("ix_diets_professional_id"), table_name="diets")
    op.drop_table("diets")

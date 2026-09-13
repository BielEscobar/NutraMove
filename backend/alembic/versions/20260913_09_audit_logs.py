"""audit logs for student assignments and transfers

Revision ID: 20260913_09
Revises: 20260912_08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260913_09"
down_revision: str | Sequence[str] | None = "20260912_08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "action",
            sa.Enum(
                "STUDENT_ASSIGNED",
                "STUDENT_TRANSFERRED",
                name="audit_action",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("resource_type", sa.String(length=30), server_default="STUDENT", nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("old_professional_id", sa.Uuid(), nullable=True),
        sa.Column("new_professional_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("length(trim(reason)) BETWEEN 5 AND 500", name="ck_audit_reason"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["old_professional_id"], ["professionals.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["new_professional_id"], ["professionals.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_created", "audit_logs", ["created_at", "id"])
    op.create_index("ix_audit_resource_created", "audit_logs", ["resource_id", "created_at"])
    op.create_index("ix_audit_actor_created", "audit_logs", ["actor_user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_actor_created", table_name="audit_logs")
    op.drop_index("ix_audit_resource_created", table_name="audit_logs")
    op.drop_index("ix_audit_created", table_name="audit_logs")
    op.drop_table("audit_logs")

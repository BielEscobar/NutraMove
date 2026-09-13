from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditAction(StrEnum):
    STUDENT_ASSIGNED = "STUDENT_ASSIGNED"
    STUDENT_TRANSFERRED = "STUDENT_TRANSFERRED"


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint("length(trim(reason)) BETWEEN 5 AND 500", name="ck_audit_reason"),
        Index("ix_audit_created", "created_at", "id"),
        Index("ix_audit_resource_created", "resource_id", "created_at"),
        Index("ix_audit_actor_created", "actor_user_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    actor_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action", native_enum=False, create_constraint=True)
    )
    resource_type: Mapped[str] = mapped_column(
        String(30), default="STUDENT", server_default="STUDENT"
    )
    resource_id: Mapped[UUID]
    old_professional_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("professionals.id", ondelete="RESTRICT")
    )
    new_professional_id: Mapped[UUID] = mapped_column(
        ForeignKey("professionals.id", ondelete="RESTRICT")
    )
    reason: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

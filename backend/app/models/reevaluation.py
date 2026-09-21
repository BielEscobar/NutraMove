from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReevaluationCategory(StrEnum):
    DIET = "DIET"
    WORKOUT = "WORKOUT"
    EVOLUTION = "EVOLUTION"
    DIFFICULTY = "DIFFICULTY"
    OTHER = "OTHER"


class ReevaluationStatus(StrEnum):
    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ReevaluationRequest(Base):
    __tablename__ = "reevaluation_requests"
    __table_args__ = (
        Index("ix_reevaluation_student_created", "student_id", "created_at"),
        Index("ix_reevaluation_status", "status"),
        Index(
            "uq_reevaluation_open",
            "student_id",
            unique=True,
            postgresql_where=text("status IN ('PENDING', 'IN_REVIEW')"),
        ),
        CheckConstraint("length(trim(reason)) BETWEEN 10 AND 2000", name="ck_reevaluation_reason"),
        CheckConstraint(
            "status <> 'COMPLETED' OR (professional_response IS NOT NULL AND "
            "length(trim(professional_response)) > 0 AND completed_at IS NOT NULL)",
            name="ck_reevaluation_completion",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id", ondelete="RESTRICT"))
    # Historical recipient; authorization always follows the current Student portfolio.
    professional_id: Mapped[UUID] = mapped_column(
        ForeignKey("professionals.id", ondelete="RESTRICT")
    )
    category: Mapped[ReevaluationCategory] = mapped_column(
        Enum(
            ReevaluationCategory,
            name="reevaluation_category",
            native_enum=False,
            create_constraint=True,
        )
    )
    reason: Mapped[str] = mapped_column(String(2000))
    status: Mapped[ReevaluationStatus] = mapped_column(
        Enum(
            ReevaluationStatus,
            name="reevaluation_status",
            native_enum=False,
            create_constraint=True,
        )
    )
    professional_response: Mapped[str | None] = mapped_column(String(2000))
    snapshot: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    completed_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    cancelled_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

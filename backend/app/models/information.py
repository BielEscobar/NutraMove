from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InformationCategory(StrEnum):
    INFO = "INFO"
    TIP = "TIP"
    NOTICE = "NOTICE"
    GUIDANCE = "GUIDANCE"


class InformationStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class Information(Base):
    __tablename__ = "informations"
    __table_args__ = (
        Index("ix_information_portfolio_status_date", "professional_id", "status", "published_at"),
        CheckConstraint("length(trim(title)) BETWEEN 3 AND 160", name="ck_information_title"),
        CheckConstraint(
            "length(trim(content)) BETWEEN 10 AND 10000", name="ck_information_content"
        ),
        CheckConstraint("edit_revision > 0", name="ck_information_revision"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    professional_id: Mapped[UUID] = mapped_column(
        ForeignKey("professionals.id", ondelete="RESTRICT")
    )
    student_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("students.id", ondelete="RESTRICT"), index=True
    )
    title: Mapped[str] = mapped_column(String(160))
    content: Mapped[str] = mapped_column(String(10000))
    category: Mapped[InformationCategory] = mapped_column(
        Enum(
            InformationCategory,
            name="information_category",
            native_enum=False,
            create_constraint=True,
        )
    )
    status: Mapped[InformationStatus] = mapped_column(
        Enum(
            InformationStatus, name="information_status", native_enum=False, create_constraint=True
        )
    )
    edit_revision: Mapped[int] = mapped_column(default=1, server_default="1")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

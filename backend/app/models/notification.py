from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationType(StrEnum):
    DIET_UPDATED = "DIET_UPDATED"
    WORKOUT_UPDATED = "WORKOUT_UPDATED"
    REEVALUATION_CREATED = "REEVALUATION_CREATED"
    REEVALUATION_IN_REVIEW = "REEVALUATION_IN_REVIEW"
    REEVALUATION_COMPLETED = "REEVALUATION_COMPLETED"
    REEVALUATION_CANCELLED = "REEVALUATION_CANCELLED"
    INFORMATION_PUBLISHED = "INFORMATION_PUBLISHED"
    STUDENT_PENDING_APPROVAL = "STUDENT_PENDING_APPROVAL"


class ResourceType(StrEnum):
    DIET_VERSION = "DIET_VERSION"
    WORKOUT_VERSION = "WORKOUT_VERSION"
    REEVALUATION = "REEVALUATION"
    INFORMATION = "INFORMATION"
    STUDENT = "STUDENT"


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notification_user_created", "user_id", "created_at", "id"),
        Index("ix_notification_unread_user", "user_id", postgresql_where=text("read_at IS NULL")),
        UniqueConstraint("user_id", "type", "resource_id", name="uq_notification_event_recipient"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type", native_enum=False, create_constraint=True)
    )
    title: Mapped[str] = mapped_column(String(160))
    message: Mapped[str] = mapped_column(String(300))
    resource_type: Mapped[ResourceType] = mapped_column(
        Enum(
            ResourceType,
            name="notification_resource_type",
            native_enum=False,
            create_constraint=True,
        )
    )
    resource_id: Mapped[UUID]
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

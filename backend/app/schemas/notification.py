from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.notification import NotificationType, ResourceType


class NotificationFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    unread_only: bool = False


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    type: NotificationType
    title: str
    message: str
    resource_type: ResourceType
    resource_id: UUID
    read_at: datetime | None
    created_at: datetime


class NotificationList(BaseModel):
    items: list[NotificationResponse]
    total: int
    page: int
    page_size: int


class UnreadCount(BaseModel):
    count: int

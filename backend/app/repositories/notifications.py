from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.schemas.notification import NotificationFilters, NotificationList, NotificationResponse


def detail(
    db: Session, user_id: UUID, notification_id: UUID, *, lock: bool = False
) -> Notification:
    query = select(Notification).where(
        Notification.user_id == user_id, Notification.id == notification_id
    )
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    record = db.scalar(query)
    if record is None:
        raise HTTPException(404, "Notificação não encontrada.")
    return record


def unread_count(db: Session, user_id: UUID) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        )
        or 0
    )


def listing(db: Session, user_id: UUID, filters: NotificationFilters) -> NotificationList:
    query = select(Notification).where(Notification.user_id == user_id)
    if filters.unread_only:
        query = query.where(Notification.read_at.is_(None))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset((filters.page - 1) * filters.page_size)
        .limit(filters.page_size)
    )
    return NotificationList(
        items=[NotificationResponse.model_validate(item) for item in items],
        total=total,
        page=filters.page,
        page_size=filters.page_size,
    )

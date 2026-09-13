from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.api.dependencies import CurrentUser, DbSession
from app.api.professionals import no_cache
from app.repositories import notifications
from app.schemas.notification import (
    NotificationFilters,
    NotificationList,
    NotificationResponse,
    UnreadCount,
)
from app.services import notifications as service

router = APIRouter(
    prefix="/notifications", tags=["notifications"], dependencies=[Depends(no_cache)]
)


@router.get("")
def listing(
    db: DbSession, actor: CurrentUser, filters: Annotated[NotificationFilters, Query()]
) -> NotificationList:
    return notifications.listing(db, actor.id, filters)


@router.get("/unread-count")
def unread_count(db: DbSession, actor: CurrentUser) -> UnreadCount:
    return UnreadCount(count=notifications.unread_count(db, actor.id))


@router.post("/read-all", status_code=204)
def read_all(db: DbSession, actor: CurrentUser) -> Response:
    service.read_all(db, actor.id)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.get("/{notification_id}")
def detail(notification_id: UUID, db: DbSession, actor: CurrentUser) -> NotificationResponse:
    return NotificationResponse.model_validate(notifications.detail(db, actor.id, notification_id))


@router.post("/{notification_id}/read")
def mark_read(notification_id: UUID, db: DbSession, actor: CurrentUser) -> NotificationResponse:
    return NotificationResponse.model_validate(service.mark_read(db, actor.id, notification_id))

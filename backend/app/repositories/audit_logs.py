from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Select, func, select
from sqlalchemy.engine import Row
from sqlalchemy.orm import Session, aliased

from app.models import Professional, User
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditFilters, AuditList, AuditResponse


def rows_query() -> Select[tuple[AuditLog, str, str, str]]:
    actor = aliased(User)
    old_professional = aliased(Professional)
    old_user = aliased(User)
    new_professional = aliased(Professional)
    new_user = aliased(User)
    query = (
        select(AuditLog, actor.name, old_user.name, new_user.name)
        .join(actor, actor.id == AuditLog.actor_user_id)
        .outerjoin(old_professional, old_professional.id == AuditLog.old_professional_id)
        .outerjoin(old_user, old_user.id == old_professional.user_id)
        .join(new_professional, new_professional.id == AuditLog.new_professional_id)
        .join(new_user, new_user.id == new_professional.user_id)
    )
    return query


def response(row: Row[tuple[AuditLog, str, str, str]]) -> AuditResponse:
    record, actor_name, old_name, new_name = row
    return AuditResponse(
        id=record.id,
        actor_user_id=record.actor_user_id,
        actor_name=actor_name,
        action=record.action,
        resource_type=record.resource_type,
        resource_id=record.resource_id,
        old_professional_id=record.old_professional_id,
        old_professional_name=old_name,
        new_professional_id=record.new_professional_id,
        new_professional_name=new_name,
        reason=record.reason,
        created_at=record.created_at,
    )


def listing(db: Session, filters: AuditFilters) -> AuditList:
    query = rows_query()
    if filters.action is not None:
        query = query.where(AuditLog.action == filters.action)
    if filters.resource_id is not None:
        query = query.where(AuditLog.resource_id == filters.resource_id)
    if filters.actor_user_id is not None:
        query = query.where(AuditLog.actor_user_id == filters.actor_user_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((filters.page - 1) * filters.page_size)
        .limit(filters.page_size)
    )
    return AuditList(
        items=[response(row) for row in rows],
        total=total,
        page=filters.page,
        page_size=filters.page_size,
    )


def detail(db: Session, audit_id: UUID) -> AuditResponse:
    row = db.execute(rows_query().where(AuditLog.id == audit_id)).one_or_none()
    if row is None:
        raise HTTPException(404, "Registro de auditoria não encontrado.")
    return response(row)

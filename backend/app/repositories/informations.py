from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import Professional, User, UserRole
from app.models.information import Information, InformationStatus
from app.repositories.students import get_student
from app.schemas.information import InformationFilters, StaffInformationFilters


def professional_id(db: Session, actor: User) -> UUID:
    result = db.scalar(select(Professional.id).where(Professional.user_id == actor.id))
    if result is None:
        raise HTTPException(403, "Perfil profissional não encontrado.")
    return result


def scope(db: Session, actor: User) -> Select[tuple[Information]]:
    query = select(Information)
    if actor.role == UserRole.MASTER:
        return query
    if actor.role == UserRole.PROFESSIONAL:
        return query.where(Information.professional_id == professional_id(db, actor))
    owner = get_student(db, actor)
    if owner is None:
        raise HTTPException(404, "Aluno não encontrado.")
    return query.where(
        Information.status == InformationStatus.PUBLISHED,
        Information.professional_id == owner.professional_id,
        (Information.student_id.is_(None) | (Information.student_id == owner.id)),
    )


def detail(db: Session, actor: User, information_id: UUID, *, lock: bool = False) -> Information:
    query = scope(db, actor).where(Information.id == information_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    record = db.scalar(query)
    if record is None:
        raise HTTPException(404, "Informativo não encontrado.")
    return record


def listing(db: Session, actor: User, filters: InformationFilters) -> tuple[list[Information], int]:
    query = scope(db, actor)
    if filters.category:
        query = query.where(Information.category == filters.category)
    if isinstance(filters, StaffInformationFilters):
        if filters.status:
            query = query.where(Information.status == filters.status)
        if filters.student_id:
            if get_student(db, actor, filters.student_id) is None:
                raise HTTPException(404, "Aluno não encontrado.")
            query = query.where(Information.student_id == filters.student_id)
        if filters.general_only:
            query = query.where(Information.student_id.is_(None))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(Information.created_at.desc(), Information.id.desc())
        .offset((filters.page - 1) * filters.page_size)
        .limit(filters.page_size)
    )
    return list(items), total

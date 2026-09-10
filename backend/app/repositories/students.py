from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, contains_eager, joinedload

from app.models import Professional, User, UserRole
from app.models.student import Student
from app.schemas.student import MasterStudentFilters, StudentFilters


def scoped_query(db: Session, actor: User) -> Select[tuple[Student]]:
    query = (
        select(Student)
        .join(Student.user)
        .options(
            contains_eager(Student.user),
            joinedload(Student.professional).joinedload(Professional.user),
        )
        .where(User.role == UserRole.STUDENT)
    )
    if actor.role == UserRole.MASTER:
        return query
    if actor.role == UserRole.PROFESSIONAL:
        professional_id = db.scalar(select(Professional.id).where(Professional.user_id == actor.id))
        if professional_id is None:
            raise HTTPException(403, "Perfil profissional não encontrado.")
        return query.where(Student.professional_id == professional_id)
    if actor.role == UserRole.STUDENT:
        return query.where(Student.user_id == actor.id)
    raise HTTPException(403, "Acesso não permitido.")


def get_student(
    db: Session, actor: User, student_id: UUID | None = None, *, lock: bool = False
) -> Student | None:
    query = scoped_query(db, actor)
    if student_id is not None:
        query = query.where(Student.id == student_id)
    if lock:
        query = query.with_for_update(of=(Student, User)).execution_options(populate_existing=True)
    return db.scalar(query)


def list_students(db: Session, actor: User, filters: StudentFilters) -> tuple[list[Student], int]:
    query = scoped_query(db, actor)
    if filters.q.strip():
        query = query.where(
            or_(
                User.name.icontains(filters.q.strip(), autoescape=True),
                User.email.icontains(filters.q.strip(), autoescape=True),
            )
        )
    if filters.status is not None:
        query = query.where(Student.status == filters.status)
    if isinstance(filters, MasterStudentFilters):
        if filters.professional_id is not None:
            query = query.where(Student.professional_id == filters.professional_id)
        if filters.unassigned:
            query = query.where(Student.professional_id.is_(None))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = list(
        db.scalars(
            query.order_by(func.lower(User.name), Student.id)
            .offset((filters.page - 1) * filters.page_size)
            .limit(filters.page_size)
        )
    )
    return items, total

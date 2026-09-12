from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import Student, User
from app.models.reevaluation import ReevaluationRequest, ReevaluationStatus
from app.repositories.students import scoped_query
from app.schemas.reevaluation import ReevaluationFilters, StaffReevaluationFilters
from app.services.students import get as get_student


def scope(db: Session, actor: User) -> Select[tuple[ReevaluationRequest]]:
    return select(ReevaluationRequest).where(
        ReevaluationRequest.student_id.in_(scoped_query(db, actor).with_only_columns(Student.id))
    )


def detail(
    db: Session, actor: User, request_id: UUID, *, lock: bool = False
) -> ReevaluationRequest:
    query = scope(db, actor).where(ReevaluationRequest.id == request_id)
    record = db.scalar(query)
    if record is None:
        raise HTTPException(404, "Solicitação não encontrada.")
    if lock:
        get_student(db, actor, record.student_id, lock=True)
        record = db.scalar(
            query.with_for_update(of=ReevaluationRequest).execution_options(populate_existing=True)
        )
        if record is None:
            raise HTTPException(404, "Solicitação não encontrada.")
    return record


def listing(
    db: Session, actor: User, filters: ReevaluationFilters
) -> tuple[list[tuple[ReevaluationRequest, str]], int]:
    query = scope(db, actor)
    if isinstance(filters, StaffReevaluationFilters) and filters.student_id:
        get_student(db, actor, filters.student_id)
        query = query.where(ReevaluationRequest.student_id == filters.student_id)
    if filters.status:
        query = query.where(ReevaluationRequest.status == filters.status)
    if filters.category:
        query = query.where(ReevaluationRequest.category == filters.category)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.add_columns(User.name)
        .join(Student, Student.id == ReevaluationRequest.student_id)
        .join(User, User.id == Student.user_id)
        .order_by(ReevaluationRequest.created_at.desc(), ReevaluationRequest.id.desc())
        .offset((filters.page - 1) * filters.page_size)
        .limit(filters.page_size)
    )
    return [(row[0], row[1]) for row in rows], total


def open_counts(db: Session, actor: User) -> tuple[int, int]:
    row = db.execute(
        scope(db, actor).with_only_columns(
            func.count().filter(ReevaluationRequest.status == ReevaluationStatus.PENDING),
            func.count().filter(ReevaluationRequest.status == ReevaluationStatus.IN_REVIEW),
        )
    ).one()
    return int(row[0]), int(row[1])

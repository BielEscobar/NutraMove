from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User
from app.models.information import Information
from app.models.information import InformationStatus as Status
from app.repositories import informations
from app.repositories.students import get_student
from app.schemas.information import InformationContent, InformationUpdate
from app.services.notifications import information_published


def validate_audience(db: Session, actor: User, student_id: UUID | None) -> None:
    if student_id is not None and get_student(db, actor, student_id) is None:
        raise HTTPException(404, "Aluno não encontrado.")


def commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Conflito ao salvar o informativo.") from None


def create(db: Session, actor: User, data: InformationContent) -> Information:
    owner = informations.professional_id(db, actor)
    validate_audience(db, actor, data.student_id)
    record = Information(
        **data.model_dump(), professional_id=owner, created_by_user_id=actor.id, status=Status.DRAFT
    )
    db.add(record)
    commit(db)
    return record


def check_revision(record: Information, expected: int) -> None:
    if record.edit_revision != expected:
        raise HTTPException(409, "O informativo mudou. Recarregue antes de continuar.")


def edit(db: Session, actor: User, information_id: UUID, data: InformationUpdate) -> Information:
    record = informations.detail(db, actor, information_id, lock=True)
    check_revision(record, data.expected_revision)
    if record.status != Status.DRAFT:
        raise HTTPException(409, "Somente rascunhos podem ser editados.")
    validate_audience(db, actor, data.student_id)
    for key, value in data.model_dump(exclude={"expected_revision"}).items():
        setattr(record, key, value)
    record.edit_revision += 1
    record.updated_at = datetime.now(UTC)
    commit(db)
    return record


def transition(
    db: Session, actor: User, information_id: UUID, expected: int, *, publish: bool
) -> Information:
    record = informations.detail(db, actor, information_id, lock=True)
    check_revision(record, expected)
    if record.status == Status.ARCHIVED or (publish and record.status != Status.DRAFT):
        raise HTTPException(409, "Esta ação não está disponível no status atual.")
    validate_audience(db, actor, record.student_id)
    record.status = Status.PUBLISHED if publish else Status.ARCHIVED
    record.updated_at = datetime.now(UTC)
    record.edit_revision += 1
    try:
        if publish:
            record.published_at = datetime.now(UTC)
            information_published(db, record)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Conflito ao publicar ou arquivar o informativo.") from None
    return record

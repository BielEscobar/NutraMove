from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Student, User
from app.models.assessment import Assessment, Measurement
from app.repositories import assessments
from app.schemas.assessment import AssessmentContent, AssessmentCreate, AssessmentUpdate


def apply_content(record: Assessment, data: AssessmentContent) -> None:
    record.weight_kg = data.weight_kg
    record.height_cm = data.height_cm
    record.notes = data.notes
    record.measurements = [Measurement(**item.model_dump()) for item in data.measurements]


def synchronize_weight(db: Session, owner: Student) -> None:
    latest = assessments.latest_weight(db, owner.id)
    if latest and latest.weight_kg is not None:
        owner.weight = latest.weight_kg
        owner.updated_at = datetime.now(UTC)


def create(db: Session, actor: User, student_id: UUID, data: AssessmentCreate) -> Assessment:
    owner = assessments.student(db, actor, student_id, lock=True)
    if owner.professional_id is None:
        raise HTTPException(404, "Aluno não encontrado.")
    record = Assessment(
        student_id=owner.id,
        professional_id=owner.professional_id,
        assessment_date=data.assessment_date,
        created_by_user_id=actor.id,
        updated_by_user_id=actor.id,
    )
    apply_content(record, data)
    try:
        db.add(record)
        db.flush()
        synchronize_weight(db, owner)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Conflito ao salvar avaliação.") from None
    return record


def edit(db: Session, actor: User, assessment_id: UUID, data: AssessmentUpdate) -> Assessment:
    record = assessments.detail(db, actor, assessment_id, lock=True)
    if record.edit_revision != data.expected_revision:
        raise HTTPException(409, "A avaliação mudou. Recarregue antes de corrigir.")
    # Keep the historical weight series nonempty and avoid losing the original profile baseline.
    if record.weight_kg is not None and data.weight_kg is None:
        raise HTTPException(422, "Corrija o peso informado; não remova um peso já registrado.")
    owner = assessments.student(db, actor, record.student_id)
    try:
        record.measurements.clear()
        db.flush()
        apply_content(record, data)
        record.updated_at = datetime.now(UTC)
        record.updated_by_user_id = actor.id
        record.edit_revision += 1
        db.flush()
        synchronize_weight(db, owner)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Conflito ao corrigir avaliação.") from None
    return record

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import StudentStatus, User, UserRole
from app.models.notification import NotificationType
from app.models.reevaluation import ReevaluationRequest
from app.models.reevaluation import ReevaluationStatus as Status
from app.repositories import reevaluations
from app.schemas.reevaluation import ReevaluationCreate
from app.services.notifications import add as notify
from app.services.students import get

Action = Literal["start-review", "complete", "cancel"]
OPEN_CONFLICT = "Você já possui uma solicitação de reavaliação em andamento."


def create(db: Session, actor: User, data: ReevaluationCreate) -> ReevaluationRequest:
    owner = get(db, actor, lock=True)
    if not owner.user.is_active:
        raise HTTPException(401, "Sessão inválida ou expirada.")
    if owner.status != StudentStatus.ACTIVE:
        raise HTTPException(409, "Seu cadastro precisa estar ativo para solicitar reavaliação.")
    if not owner.professional or not owner.professional.user.is_active:
        raise HTTPException(409, "É necessário um profissional ativo vinculado ao seu cadastro.")
    existing = db.scalar(
        select(ReevaluationRequest.id).where(
            ReevaluationRequest.student_id == owner.id,
            ReevaluationRequest.status.in_([Status.PENDING, Status.IN_REVIEW]),
        )
    )
    if existing:
        raise HTTPException(409, OPEN_CONFLICT)
    record = ReevaluationRequest(
        student_id=owner.id,
        professional_id=owner.professional.id,
        status=Status.PENDING,
        **data.model_dump(),
    )
    try:
        db.add(record)
        db.flush()
        notify(db, owner.professional.user_id, NotificationType.REEVALUATION_CREATED, record.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, OPEN_CONFLICT) from None
    return record


def transition(
    db: Session, actor: User, request_id: UUID, action: Action, response: str | None = None
) -> ReevaluationRequest:
    record = reevaluations.detail(db, actor, request_id, lock=True)
    if actor.role == UserRole.MASTER:
        raise HTTPException(403, "Consulta administrativa somente para leitura.")
    if actor.role == UserRole.STUDENT and (action != "cancel" or record.status != Status.PENDING):
        raise HTTPException(409, "Só é possível cancelar uma solicitação pendente.")
    sources = {
        "start-review": {Status.PENDING},
        "complete": {Status.IN_REVIEW},
        "cancel": {Status.PENDING, Status.IN_REVIEW},
    }
    if record.status not in sources[action]:
        raise HTTPException(409, "Esta ação não está disponível no status atual.")
    now = datetime.now(UTC)
    if action == "start-review":
        record.status = Status.IN_REVIEW
        record.reviewed_at = now
        record.reviewed_by_user_id = actor.id
    elif action == "complete":
        if not response or not response.strip():
            raise HTTPException(422, "Informe uma resposta para concluir.")
        record.status = Status.COMPLETED
        record.professional_response = response
        record.completed_at = now
        record.completed_by_user_id = actor.id
    else:
        record.status = Status.CANCELLED
        record.cancelled_at = now
        record.cancelled_by_user_id = actor.id
    record.updated_at = now
    if actor.role == UserRole.PROFESSIONAL:
        owner = get(db, actor, record.student_id)
        kinds = {
            "start-review": NotificationType.REEVALUATION_IN_REVIEW,
            "complete": NotificationType.REEVALUATION_COMPLETED,
            "cancel": NotificationType.REEVALUATION_CANCELLED,
        }
        notify(db, owner.user_id, kinds[action], record.id)
    db.commit()
    return record

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Professional, StudentStatus, User, UserRole
from app.models.audit_log import AuditAction, AuditLog
from app.models.reevaluation import ReevaluationRequest, ReevaluationStatus
from app.repositories.students import get_student
from app.schemas.audit_log import StudentTransfer, TransferResponse


def transfer(db: Session, actor: User, student_id: UUID, data: StudentTransfer) -> TransferResponse:
    if actor.role != UserRole.MASTER:
        raise HTTPException(403, "Apenas MASTER pode transferir alunos.")
    student = get_student(db, actor, student_id, lock=True)
    if student is None:
        raise HTTPException(404, "Aluno não encontrado.")
    if student.professional_id != data.expected_professional_id:
        raise HTTPException(409, "O profissional responsável mudou. Recarregue o aluno.")
    if student.status == StudentStatus.REJECTED:
        raise HTTPException(409, "Cadastro rejeitado não pode ser transferido.")
    if student.professional_id == data.new_professional_id:
        raise HTTPException(409, "O aluno já pertence ao profissional escolhido.")
    destination = db.scalar(
        select(Professional).where(Professional.id == data.new_professional_id).with_for_update()
    )
    if destination is None:
        raise HTTPException(404, "Profissional de destino não encontrado.")
    destination_user = db.scalar(
        select(User).where(User.id == destination.user_id).with_for_update()
    )
    if (
        destination_user is None
        or not destination_user.is_active
        or destination_user.role != UserRole.PROFESSIONAL
    ):
        raise HTTPException(409, "O profissional de destino precisa estar ativo.")
    in_review = db.scalar(
        select(ReevaluationRequest.id).where(
            ReevaluationRequest.student_id == student.id,
            ReevaluationRequest.status == ReevaluationStatus.IN_REVIEW,
        )
    )
    if in_review is not None:
        raise HTTPException(409, "Conclua ou cancele a reavaliação em análise antes de transferir.")
    old_professional_id = student.professional_id
    student.professional_id = destination.id
    student.updated_at = datetime.now(UTC)
    audit = AuditLog(
        actor_user_id=actor.id,
        action=(
            AuditAction.STUDENT_ASSIGNED
            if old_professional_id is None
            else AuditAction.STUDENT_TRANSFERRED
        ),
        resource_type="STUDENT",
        resource_id=student.id,
        old_professional_id=old_professional_id,
        new_professional_id=destination.id,
        reason=data.reason,
    )
    try:
        db.add(audit)
        db.flush()
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Conflito ao transferir aluno.") from None
    return TransferResponse(
        student_id=student.id,
        old_professional_id=old_professional_id,
        new_professional_id=destination.id,
        audit_log_id=audit.id,
        transferred_at=audit.created_at,
    )

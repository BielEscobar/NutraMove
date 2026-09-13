from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, insert, literal, select, update
from sqlalchemy.orm import Session

from app.models import Student, StudentStatus, User
from app.models.information import Information
from app.models.notification import Notification
from app.models.notification import NotificationType as Kind
from app.models.notification import ResourceType as Resource
from app.repositories import notifications

# Messages are fixed application text; event content never enters the inbox.
MESSAGES: dict[Kind, tuple[str, str, Resource]] = {
    Kind.DIET_UPDATED: (
        "Dieta atualizada",
        "Seu profissional publicou uma nova versão da sua dieta.",
        Resource.DIET_VERSION,
    ),
    Kind.WORKOUT_UPDATED: (
        "Treino atualizado",
        "Seu profissional publicou uma nova versão do seu treino.",
        Resource.WORKOUT_VERSION,
    ),
    Kind.REEVALUATION_CREATED: (
        "Nova reavaliação",
        "Um aluno enviou uma solicitação de reavaliação.",
        Resource.REEVALUATION,
    ),
    Kind.REEVALUATION_IN_REVIEW: (
        "Reavaliação em análise",
        "Sua solicitação está em análise.",
        Resource.REEVALUATION,
    ),
    Kind.REEVALUATION_COMPLETED: (
        "Reavaliação concluída",
        "Seu profissional respondeu à sua solicitação.",
        Resource.REEVALUATION,
    ),
    Kind.REEVALUATION_CANCELLED: (
        "Reavaliação cancelada",
        "Seu profissional cancelou a solicitação.",
        Resource.REEVALUATION,
    ),
    Kind.INFORMATION_PUBLISHED: (
        "Novo informativo",
        "Seu profissional publicou um informativo para você.",
        Resource.INFORMATION,
    ),
    Kind.STUDENT_PENDING_APPROVAL: (
        "Novo cadastro",
        "Novo aluno aguardando aprovação.",
        Resource.STUDENT,
    ),
}


def add(db: Session, user_id: UUID, kind: Kind, resource_id: UUID) -> None:
    """Append to the caller's transaction; never commit an event separately."""
    title, message, resource = MESSAGES[kind]
    db.add(
        Notification(
            user_id=user_id,
            type=kind,
            title=title,
            message=message,
            resource_type=resource,
            resource_id=resource_id,
        )
    )


def information_published(db: Session, information: Information) -> None:
    title, message, resource = MESSAGES[Kind.INFORMATION_PUBLISHED]
    # INSERT SELECT broadcasts without loading a complete portfolio into Python.
    recipients = (
        select(
            func.gen_random_uuid(),
            Student.user_id,
            literal(Kind.INFORMATION_PUBLISHED.value),
            literal(title),
            literal(message),
            literal(resource.value),
            literal(information.id),
            func.now(),
        )
        .join(User, User.id == Student.user_id)
        .where(
            Student.professional_id == information.professional_id,
            Student.status == StudentStatus.ACTIVE,
            User.is_active.is_(True),
        )
    )
    if information.student_id is not None:
        recipients = recipients.where(Student.id == information.student_id)
    db.execute(
        insert(Notification).from_select(
            [
                "id",
                "user_id",
                "type",
                "title",
                "message",
                "resource_type",
                "resource_id",
                "created_at",
            ],
            recipients,
        )
    )


def mark_read(db: Session, user_id: UUID, notification_id: UUID) -> Notification:
    record = notifications.detail(db, user_id, notification_id, lock=True)
    if record.read_at is None:
        record.read_at = datetime.now(UTC)
    db.commit()
    return record


def read_all(db: Session, user_id: UUID) -> None:
    db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        .values(read_at=datetime.now(UTC))
    )
    db.commit()

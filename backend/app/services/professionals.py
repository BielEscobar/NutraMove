from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.professional import Professional
from app.models.user import User, UserRole
from app.repositories import auth_sessions, professionals, users
from app.schemas.professional import ProfessionalCreate, ProfessionalResponse, ProfessionalUpdate


def to_response(professional: Professional) -> ProfessionalResponse:
    return ProfessionalResponse(
        id=professional.id,
        user_id=professional.user_id,
        name=professional.user.name,
        email=professional.user.email,
        specialty=professional.specialty,
        is_active=professional.user.is_active,
        created_at=professional.created_at,
        updated_at=professional.updated_at,
    )


def get_professional(db: Session, professional_id: UUID, *, lock: bool = False) -> Professional:
    professional = professionals.get_by_id(db, professional_id, lock=lock)
    if professional is None:
        raise HTTPException(404, "Profissional não encontrado.")
    return professional


def create(db: Session, data: ProfessionalCreate) -> Professional:
    if users.get_by_email(db, str(data.email)):
        raise HTTPException(409, "E-mail já cadastrado.")
    user = User(
        name=data.name,
        email=str(data.email),
        password_hash=hash_password(data.password.get_secret_value()),
        role=UserRole.PROFESSIONAL,
        is_active=True,
    )
    professional = Professional(user=user, specialty=data.specialty)
    try:
        db.add(professional)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "E-mail ou vínculo já cadastrado.") from None
    return professional


def update(db: Session, professional_id: UUID, data: ProfessionalUpdate) -> Professional:
    professional = get_professional(db, professional_id, lock=True)
    if data.email is not None:
        existing = users.get_by_email(db, str(data.email))
        if existing is not None and existing.id != professional.user_id:
            raise HTTPException(409, "E-mail já cadastrado.")
        professional.user.email = str(data.email)
    if data.name is not None:
        professional.user.name = data.name
    if "specialty" in data.model_fields_set:
        professional.specialty = data.specialty
    professional.updated_at = datetime.now(UTC)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "E-mail já cadastrado.") from None
    return professional


def set_active(db: Session, professional_id: UUID, *, active: bool) -> Professional:
    # The same User row is locked during login to serialize session creation/revocation.
    professional = get_professional(db, professional_id, lock=True)
    professional.user.is_active = active
    if not active:
        auth_sessions.revoke_all(db, professional.user_id)
    professional.updated_at = datetime.now(UTC)
    db.commit()
    return professional

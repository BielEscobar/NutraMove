from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import User, UserRole
from app.models.student import Student, StudentStatus
from app.repositories import auth_sessions, professionals, students, users
from app.schemas.student import (
    StudentBrief,
    StudentCreate,
    StudentProfile,
    StudentResponse,
    StudentUpdate,
)

StudentAction = Literal["approve", "reject", "activate", "deactivate"]


def brief(student: Student) -> StudentBrief:
    return StudentBrief(
        id=student.id,
        name=student.user.name,
        email=student.user.email,
        goal=student.goal,
        status=student.status,
        professional_id=student.professional_id,
        professional_name=student.professional.user.name if student.professional else None,
    )


def response(student: Student) -> StudentResponse:
    profile = StudentProfile.model_validate(student)
    return StudentResponse(
        **profile.model_dump(),
        id=student.id,
        name=student.user.name,
        email=student.user.email,
        professional_id=student.professional_id,
        professional_name=student.professional.user.name if student.professional else None,
        status=student.status,
        is_active=student.user.is_active,
        water_goal=student.water_goal,
        created_at=student.created_at,
        updated_at=student.updated_at,
    )


def create(db: Session, data: StudentCreate) -> Student:
    if users.get_by_email(db, str(data.email)):
        raise HTTPException(409, "E-mail já cadastrado.")
    if data.professional_id is not None:
        professional = professionals.get_by_id(db, data.professional_id, lock=True)
        if professional is None or not professional.user.is_active:
            raise HTTPException(422, "Profissional indisponível para cadastro.")
    user = User(
        name=data.name,
        email=str(data.email),
        password_hash=hash_password(data.password.get_secret_value()),
        role=UserRole.STUDENT,
        is_active=True,
    )
    profile = data.model_dump(include=set(StudentProfile.model_fields))
    student = Student(
        **profile,
        user=user,
        professional_id=data.professional_id,
        status=StudentStatus.PENDING_APPROVAL,
    )
    try:
        db.add(student)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Cadastro não pôde ser concluído por conflito de dados.") from None
    return student


def get(db: Session, actor: User, student_id: UUID | None = None, *, lock: bool = False) -> Student:
    student = students.get_student(db, actor, student_id, lock=lock)
    if student is None:
        raise HTTPException(404, "Aluno não encontrado.")
    return student


def update(db: Session, actor: User, student_id: UUID, data: StudentUpdate) -> Student:
    student = get(db, actor, student_id, lock=True)
    changes = data.model_dump(exclude_unset=True)
    profile_changes = {
        key: value for key, value in changes.items() if key in StudentProfile.model_fields
    }
    merged = StudentProfile.model_validate(student).model_dump() | profile_changes
    try:
        validated = StudentProfile.model_validate(merged)
    except ValidationError:
        raise HTTPException(422, "Revise os dados do aluno e o complemento do objetivo.") from None
    for key, value in validated.model_dump().items():
        setattr(student, key, value)
    if "water_goal" in changes:
        student.water_goal = data.water_goal
    student.updated_at = datetime.now(UTC)
    db.commit()
    return student


def transition(db: Session, actor: User, student_id: UUID, action: StudentAction) -> Student:
    student = get(db, actor, student_id, lock=True)
    transitions = {
        "approve": (StudentStatus.PENDING_APPROVAL, StudentStatus.ACTIVE),
        "reject": (StudentStatus.PENDING_APPROVAL, StudentStatus.REJECTED),
        "deactivate": (StudentStatus.ACTIVE, StudentStatus.INACTIVE),
        "activate": (StudentStatus.INACTIVE, StudentStatus.ACTIVE),
    }
    source, target = transitions[action]
    if student.status != source:
        raise HTTPException(409, "Esta ação não está disponível no status atual.")
    student.status = target
    student.user.is_active = target != StudentStatus.INACTIVE
    if not student.user.is_active:
        auth_sessions.revoke_all(db, student.user_id)
    student.updated_at = datetime.now(UTC)
    db.commit()
    return student

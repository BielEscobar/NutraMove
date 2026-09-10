from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.models import Student, StudentStatus, User, UserRole
from app.models.diet import Diet, DietStatus, DietVersion, Food, Meal
from app.repositories.students import get_student as find_student
from app.repositories.students import scoped_query


def diet_scope(db: Session, actor: User) -> Select[tuple[Diet]]:
    student_ids = scoped_query(db, actor).with_only_columns(Student.id)
    query = select(Diet).where(Diet.student_id.in_(student_ids))
    if actor.role == UserRole.PROFESSIONAL:
        query = query.join(Student, Student.id == Diet.student_id).where(
            Diet.professional_id == Student.professional_id
        )
    return query


def get_diet(db: Session, actor: User, diet_id: UUID, *, lock: bool = False) -> Diet:
    query = diet_scope(db, actor).where(Diet.id == diet_id)
    diet = db.scalar(query)
    if diet is None:
        raise HTTPException(404, "Dieta não encontrada.")
    if lock:
        # All writes lock Student first, then Diet: publication across plans is serialized.
        get_student(db, actor, diet.student_id, lock=True)
        diet = db.scalar(query.with_for_update(of=Diet).execution_options(populate_existing=True))
        if diet is None:
            raise HTTPException(404, "Dieta não encontrada.")
    return diet


def version_query() -> Select[tuple[DietVersion]]:
    return select(DietVersion).options(
        selectinload(DietVersion.meals).selectinload(Meal.foods).selectinload(Food.substitutions)
    )


def get_version(db: Session, actor: User, version_id: UUID, *, lock: bool = False) -> DietVersion:
    query = version_query().where(
        DietVersion.id == version_id,
        DietVersion.diet_id.in_(diet_scope(db, actor).with_only_columns(Diet.id)),
    )
    version = db.scalar(query)
    if version is None:
        raise HTTPException(404, "Versão não encontrada.")
    if lock:
        get_diet(db, actor, version.diet_id, lock=True)
        version = db.scalar(query.execution_options(populate_existing=True))
        if version is None:
            raise HTTPException(404, "Versão não encontrada.")
    return version


def list_diets(db: Session, actor: User, student_id: UUID) -> list[Diet]:
    get_student(db, actor, student_id)
    return list(
        db.scalars(
            diet_scope(db, actor)
            .where(Diet.student_id == student_id)
            .order_by(Diet.created_at.desc(), Diet.id)
        )
    )


def list_versions(db: Session, actor: User, diet_id: UUID) -> list[DietVersion]:
    get_diet(db, actor, diet_id)
    return list(
        db.scalars(
            select(DietVersion)
            .where(DietVersion.diet_id == diet_id)
            .order_by(DietVersion.version_number.desc())
        )
    )


def current_student_version(db: Session, actor: User) -> DietVersion | None:
    student = get_student(db, actor)
    # Pending/rejected students retain their account, but cannot read published plans.
    if student.status != StudentStatus.ACTIVE:
        return None
    return db.scalar(
        version_query()
        .join(Diet)
        .where(Diet.student_id == student.id, DietVersion.status == DietStatus.APPROVED)
        .order_by(DietVersion.approved_at.desc(), DietVersion.id.desc())
        .limit(1)
    )


def get_student(
    db: Session, actor: User, student_id: UUID | None = None, *, lock: bool = False
) -> Student:
    student = find_student(db, actor, student_id, lock=lock)
    if student is None:
        raise HTTPException(404, "Student not found.")
    return student

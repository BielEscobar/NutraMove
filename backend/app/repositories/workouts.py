from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.models import Student, StudentStatus, User, UserRole
from app.models.workout import Workout, WorkoutDay, WorkoutStatus, WorkoutVersion
from app.repositories.students import get_student as find_student
from app.repositories.students import scoped_query


def workout_scope(db: Session, actor: User) -> Select[tuple[Workout]]:
    student_ids = scoped_query(db, actor).with_only_columns(Student.id)
    query = select(Workout).where(Workout.student_id.in_(student_ids))
    if actor.role == UserRole.PROFESSIONAL:
        query = query.join(Student, Student.id == Workout.student_id).where(
            Workout.professional_id == Student.professional_id
        )
    return query


def get_workout(db: Session, actor: User, workout_id: UUID, *, lock: bool = False) -> Workout:
    query = workout_scope(db, actor).where(Workout.id == workout_id)
    workout = db.scalar(query)
    if workout is None:
        raise HTTPException(404, "Treino não encontrado.")
    if lock:
        # All writes lock Student first, then Workout: publication across plans is serialized.
        get_student(db, actor, workout.student_id, lock=True)
        workout = db.scalar(
            query.with_for_update(of=Workout).execution_options(populate_existing=True)
        )
        if workout is None:
            raise HTTPException(404, "Treino não encontrado.")
    return workout


def version_query() -> Select[tuple[WorkoutVersion]]:
    return select(WorkoutVersion).options(
        selectinload(WorkoutVersion.days).selectinload(WorkoutDay.exercises)
    )


def get_version(
    db: Session, actor: User, version_id: UUID, *, lock: bool = False
) -> WorkoutVersion:
    query = version_query().where(
        WorkoutVersion.id == version_id,
        WorkoutVersion.workout_id.in_(workout_scope(db, actor).with_only_columns(Workout.id)),
    )
    version = db.scalar(query)
    if version is None:
        raise HTTPException(404, "Versão não encontrada.")
    if lock:
        get_workout(db, actor, version.workout_id, lock=True)
        version = db.scalar(query.execution_options(populate_existing=True))
        if version is None:
            raise HTTPException(404, "Versão não encontrada.")
    return version


def list_workouts(db: Session, actor: User, student_id: UUID) -> list[Workout]:
    get_student(db, actor, student_id)
    return list(
        db.scalars(
            workout_scope(db, actor)
            .where(Workout.student_id == student_id)
            .order_by(Workout.created_at.desc(), Workout.id)
        )
    )


def list_versions(db: Session, actor: User, workout_id: UUID) -> list[WorkoutVersion]:
    get_workout(db, actor, workout_id)
    return list(
        db.scalars(
            select(WorkoutVersion)
            .where(WorkoutVersion.workout_id == workout_id)
            .order_by(WorkoutVersion.version_number.desc())
        )
    )


def current_student_version(db: Session, actor: User) -> WorkoutVersion | None:
    student = get_student(db, actor)
    # Pending/rejected students retain their account, but cannot read published plans.
    if student.status != StudentStatus.ACTIVE:
        return None
    return db.scalar(
        version_query()
        .join(Workout)
        .where(Workout.student_id == student.id, WorkoutVersion.status == WorkoutStatus.APPROVED)
        .order_by(WorkoutVersion.approved_at.desc(), WorkoutVersion.id.desc())
        .limit(1)
    )


def get_student(
    db: Session, actor: User, student_id: UUID | None = None, *, lock: bool = False
) -> Student:
    student = find_student(db, actor, student_id, lock=lock)
    if student is None:
        raise HTTPException(404, "Student not found.")
    return student

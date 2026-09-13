from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import StudentStatus, User
from app.models.notification import NotificationType
from app.models.workout import (
    Workout,
    WorkoutDay,
    WorkoutExercise,
    WorkoutSource,
    WorkoutStatus,
    WorkoutVersion,
)
from app.repositories import workouts
from app.schemas.workout import VersionContent, VersionUpdate
from app.services.notifications import add as notify
from app.services.students import get as get_student


def content_of(version: WorkoutVersion) -> VersionContent:
    return VersionContent.model_validate(version)


def apply_content(version: WorkoutVersion, content: VersionContent) -> None:
    version.name = content.name
    version.goal = content.goal
    version.start_date = content.start_date
    version.next_review_date = content.next_review_date
    version.notes = content.notes
    version.frequency_per_week = content.frequency_per_week
    version.days = [
        WorkoutDay(
            name=day.name,
            description=day.description,
            position=day_index,
            exercises=[
                WorkoutExercise(**exercise.model_dump(), position=exercise_index)
                for exercise_index, exercise in enumerate(day.exercises)
            ],
        )
        for day_index, day in enumerate(content.days)
    ]


def commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409, "Conflito ao salvar o treino. Atualize e tente novamente."
        ) from None


def new_version(
    db: Session, actor: User, workout: Workout, content: VersionContent
) -> WorkoutVersion:
    # Caller holds the Workout lock (or just created the parent within the transaction).
    last = (
        db.scalar(
            select(func.max(WorkoutVersion.version_number)).where(
                WorkoutVersion.workout_id == workout.id
            )
        )
        or 0
    )
    version = WorkoutVersion(
        workout_id=workout.id,
        version_number=last + 1,
        status=WorkoutStatus.DRAFT,
        source=WorkoutSource.MANUAL,
        created_by_user_id=actor.id,
    )
    apply_content(version, content)
    db.add(version)
    workout.updated_at = datetime.now(UTC)
    return version


def create_workout(
    db: Session, actor: User, student_id: UUID, content: VersionContent
) -> WorkoutVersion:
    student = get_student(db, actor, student_id, lock=True)
    if student.professional_id is None:
        raise HTTPException(404, "Aluno não encontrado.")
    workout = Workout(
        student_id=student.id, professional_id=student.professional_id, name=content.name
    )
    db.add(workout)
    db.flush()
    version = new_version(db, actor, workout, content)
    commit(db)
    return version


def create_version(
    db: Session, actor: User, workout_id: UUID, content: VersionContent
) -> WorkoutVersion:
    workout = workouts.get_workout(db, actor, workout_id, lock=True)
    version = new_version(db, actor, workout, content)
    commit(db)
    return version


def duplicate(db: Session, actor: User, version_id: UUID) -> WorkoutVersion:
    source = workouts.get_version(db, actor, version_id, lock=True)
    workout = workouts.get_workout(db, actor, source.workout_id)
    version = new_version(db, actor, workout, content_of(source))
    commit(db)
    return version


def check_editable(version: WorkoutVersion, expected_revision: int) -> None:
    if version.status not in {WorkoutStatus.DRAFT, WorkoutStatus.PENDING_REVIEW}:
        raise HTTPException(409, "Versão publicada ou arquivada: crie uma nova versão.")
    if version.edit_revision != expected_revision:
        raise HTTPException(409, "A versão mudou. Recarregue antes de continuar.")


def edit(db: Session, actor: User, version_id: UUID, data: VersionUpdate) -> WorkoutVersion:
    version = workouts.get_version(db, actor, version_id, lock=True)
    check_editable(version, data.expected_revision)
    # Delete old children before inserting new positions; rollback restores the entire tree.
    try:
        version.days.clear()
        db.flush()
        apply_content(
            version, VersionContent.model_validate(data.model_dump(exclude={"expected_revision"}))
        )
        version.edit_revision += 1
        version.updated_at = datetime.now(UTC)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409, "Conflito ao salvar o treino. Atualize e tente novamente."
        ) from None
    return version


def approve(db: Session, actor: User, version_id: UUID, expected_revision: int) -> WorkoutVersion:
    version = workouts.get_version(db, actor, version_id, lock=True)
    check_editable(version, expected_revision)
    workout = workouts.get_workout(db, actor, version.workout_id)
    student = get_student(db, actor, workout.student_id)
    if student.status != StudentStatus.ACTIVE:
        raise HTTPException(409, "A publicação exige um aluno com acompanhamento ativo.")
    if not version.days or any(not day.exercises for day in version.days):
        raise HTTPException(422, "Inclua ao menos uma divisão e um exercício por divisão.")
    now = datetime.now(UTC)
    db.execute(
        update(WorkoutVersion)
        .where(
            WorkoutVersion.workout_id.in_(
                select(Workout.id).where(Workout.student_id == workout.student_id)
            ),
            WorkoutVersion.status == WorkoutStatus.APPROVED,
        )
        .values(status=WorkoutStatus.ARCHIVED, updated_at=now),
        execution_options={"synchronize_session": "fetch"},
    )
    version.status = WorkoutStatus.APPROVED
    version.approved_by_user_id = actor.id
    version.approved_at = now
    version.updated_at = now
    version.edit_revision += 1
    notify(db, student.user_id, NotificationType.WORKOUT_UPDATED, version.id)
    commit(db)
    return version

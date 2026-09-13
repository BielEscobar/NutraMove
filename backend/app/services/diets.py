from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import StudentStatus, User
from app.models.diet import Diet, DietSource, DietStatus, DietVersion, Food, FoodSubstitution, Meal
from app.models.notification import NotificationType
from app.repositories import diets
from app.schemas.diet import VersionContent, VersionUpdate
from app.services.notifications import add as notify
from app.services.students import get as get_student


def content_of(version: DietVersion) -> VersionContent:
    return VersionContent.model_validate(version)


def apply_content(version: DietVersion, content: VersionContent) -> None:
    version.name = content.name
    version.goal = content.goal
    version.start_date = content.start_date
    version.next_review_date = content.next_review_date
    version.notes = content.notes
    version.meals = [
        Meal(
            name=meal.name,
            time=meal.time,
            position=meal_index,
            foods=[
                Food(
                    name=food.name,
                    quantity=food.quantity,
                    unit=food.unit,
                    notes=food.notes,
                    position=food_index,
                    substitutions=[
                        FoodSubstitution(
                            name=item.name,
                            quantity=item.quantity,
                            unit=item.unit,
                            notes=item.notes,
                            position=sub_index,
                        )
                        for sub_index, item in enumerate(food.substitutions)
                    ],
                )
                for food_index, food in enumerate(meal.foods)
            ],
        )
        for meal_index, meal in enumerate(content.meals)
    ]


def commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409, "Conflito ao salvar a dieta. Atualize e tente novamente."
        ) from None


def new_version(db: Session, actor: User, diet: Diet, content: VersionContent) -> DietVersion:
    # Caller holds the Diet lock (or just created the parent within the transaction).
    last = (
        db.scalar(
            select(func.max(DietVersion.version_number)).where(DietVersion.diet_id == diet.id)
        )
        or 0
    )
    version = DietVersion(
        diet_id=diet.id,
        version_number=last + 1,
        status=DietStatus.DRAFT,
        source=DietSource.MANUAL,
        created_by_user_id=actor.id,
    )
    apply_content(version, content)
    db.add(version)
    diet.updated_at = datetime.now(UTC)
    return version


def create_diet(db: Session, actor: User, student_id: UUID, content: VersionContent) -> DietVersion:
    student = get_student(db, actor, student_id, lock=True)
    if student.professional_id is None:
        raise HTTPException(404, "Aluno não encontrado.")
    diet = Diet(student_id=student.id, professional_id=student.professional_id, name=content.name)
    db.add(diet)
    db.flush()
    version = new_version(db, actor, diet, content)
    commit(db)
    return version


def create_version(db: Session, actor: User, diet_id: UUID, content: VersionContent) -> DietVersion:
    diet = diets.get_diet(db, actor, diet_id, lock=True)
    version = new_version(db, actor, diet, content)
    commit(db)
    return version


def duplicate(db: Session, actor: User, version_id: UUID) -> DietVersion:
    source = diets.get_version(db, actor, version_id, lock=True)
    diet = diets.get_diet(db, actor, source.diet_id)
    version = new_version(db, actor, diet, content_of(source))
    commit(db)
    return version


def check_editable(version: DietVersion, expected_revision: int) -> None:
    if version.status not in {DietStatus.DRAFT, DietStatus.PENDING_REVIEW}:
        raise HTTPException(409, "Versão publicada ou arquivada: crie uma nova versão.")
    if version.edit_revision != expected_revision:
        raise HTTPException(409, "A versão mudou. Recarregue antes de continuar.")


def edit(db: Session, actor: User, version_id: UUID, data: VersionUpdate) -> DietVersion:
    version = diets.get_version(db, actor, version_id, lock=True)
    check_editable(version, data.expected_revision)
    # Delete old children before inserting new positions; rollback restores the entire tree.
    try:
        version.meals.clear()
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
            409, "Conflito ao salvar a dieta. Atualize e tente novamente."
        ) from None
    return version


def approve(db: Session, actor: User, version_id: UUID, expected_revision: int) -> DietVersion:
    version = diets.get_version(db, actor, version_id, lock=True)
    check_editable(version, expected_revision)
    diet = diets.get_diet(db, actor, version.diet_id)
    student = get_student(db, actor, diet.student_id)
    if student.status != StudentStatus.ACTIVE:
        raise HTTPException(409, "A publicação exige um aluno com acompanhamento ativo.")
    if not version.meals or any(not meal.foods for meal in version.meals):
        raise HTTPException(422, "Inclua ao menos uma refeição e um alimento por refeição.")
    now = datetime.now(UTC)
    db.execute(
        update(DietVersion)
        .where(
            DietVersion.diet_id.in_(select(Diet.id).where(Diet.student_id == diet.student_id)),
            DietVersion.status == DietStatus.APPROVED,
        )
        .values(status=DietStatus.ARCHIVED, updated_at=now),
        execution_options={"synchronize_session": "fetch"},
    )
    version.status = DietStatus.APPROVED
    version.approved_by_user_id = actor.id
    version.approved_at = now
    version.updated_at = now
    version.edit_revision += 1
    notify(db, student.user_id, NotificationType.DIET_UPDATED, version.id)
    commit(db)
    return version

import logging
import re
from datetime import UTC, date, datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.provider import AIProvider, ProviderFailure
from app.ai.safety import validate_scope
from app.core.config import Settings
from app.models import StudentStatus, User
from app.models.assessment import Assessment
from app.models.diet import Diet, DietSource, DietStatus, DietVersion
from app.models.reevaluation import ReevaluationRequest, ReevaluationStatus
from app.models.workout import Workout, WorkoutSource, WorkoutStatus, WorkoutVersion
from app.schemas.diet import VersionContent as DietContent
from app.schemas.workout import VersionContent as WorkoutContent
from app.services import diets, workouts
from app.services.students import get as get_student

logger = logging.getLogger(__name__)
_SAFE_FIELD = re.compile(r"^[A-Za-z_][A-Za-z_0-9]*$|^[0-9]+$")


def _validation_field(location: tuple[str | int, ...]) -> str:
    return ".".join(
        str(part) if _SAFE_FIELD.fullmatch(str(part)) else "unknown" for part in location
    )[:120]


Kind = Literal["diet", "workout"]


class GenerationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    instructions: str = Field(default="", max_length=2000)
    include_current_plan: bool = False
    include_recent_evolution: bool = False


class ContextPreview(BaseModel):
    fields: list[str]
    has_current_plan: bool
    has_recent_evolution: bool


class PlanReference(BaseModel):
    id: UUID
    status: str
    source: str


class PlansState(BaseModel):
    diet: PlanReference | None
    workout: PlanReference | None


class PlansResult(PlansState):
    diet_error: str | None = None
    workout_error: str | None = None


def _context(
    db: Session, actor: User, student_id: UUID, kind: Kind, data: GenerationInput
) -> tuple[dict[str, Any], ContextPreview]:
    student = get_student(db, actor, student_id)
    if student.status != StudentStatus.ACTIVE or student.professional_id is None:
        raise HTTPException(409, "A geração exige um aluno ativo da carteira atual.")
    completed = _latest_completed(db, student.id)
    latest_snapshot = completed.snapshot if completed and completed.snapshot else {}
    age = (
        date.today().year
        - student.birth_date.year
        - (
            (date.today().month, date.today().day)
            < (student.birth_date.month, student.birth_date.day)
        )
    )

    def current(name: str) -> Any:
        if name in latest_snapshot and latest_snapshot[name] is not None:
            return latest_snapshot[name]
        original: Any = getattr(student, name, None)
        if hasattr(original, "value"):
            return original.value
        return original.isoformat() if hasattr(original, "isoformat") else original

    shared = {
        "sex": current("sex"),
        "age": age,
        "weight": current("weight"),
        "height": student.height,
        "desired_weight": current("desired_weight"),
        "goal": current("goal"),
        "goal_detail": current("goal_detail"),
        "activity_level": current("activity_level"),
        "professional_instructions": data.instructions,
    }
    if kind == "workout":
        context: dict[str, Any] = shared | {
            "training_experience": current("training_experience"),
            "trains_currently": current("trains_currently"),
            "training_history": current("training_history"),
            "training_frequency": current("training_frequency"),
            "available_training_days": current("available_training_days"),
            "preferred_training_time": current("preferred_training_time"),
            "training_duration_minutes": current("training_duration_minutes"),
            "training_location": current("training_location"),
            "available_equipment": current("available_equipment"),
            "work_routine": current("work_routine"),
            "has_injury": current("has_injury"),
            "injury_description": current("injury_description"),
            "physical_limitations": current("physical_limitations"),
            "medical_restrictions": current("medical_restrictions"),
            "reevaluation_progress": latest_snapshot.get("progress_perception"),
            "reevaluation_difficulties": latest_snapshot.get("difficulties"),
        }
    else:
        context = shared | {
            "meal_count": current("meal_count"),
            "meal_schedule": current("meal_schedule"),
            "wake_time": current("wake_time"),
            "sleep_time": current("sleep_time"),
            "work_routine": current("work_routine"),
            "cooking_skill": current("cooking_skill"),
            "food_preferences": current("food_preferences"),
            "disliked_foods": current("disliked_foods"),
            "food_restrictions": current("food_restrictions"),
            "food_allergies": current("food_allergies"),
            "weekly_food_budget": current("weekly_food_budget"),
            "food_notes": current("food_notes"),
            "medical_restrictions": current("medical_restrictions"),
            "reevaluation_progress": latest_snapshot.get("progress_perception"),
            "reevaluation_difficulties": latest_snapshot.get("difficulties"),
        }

    has_plan = False
    current_plan: DietVersion | WorkoutVersion | None = None
    if data.include_current_plan:
        if kind == "diet":
            current_plan = db.scalar(
                select(DietVersion)
                .join(Diet)
                .where(Diet.student_id == student.id, DietVersion.status == DietStatus.APPROVED)
                .order_by(DietVersion.approved_at.desc())
                .limit(1)
            )
        else:
            current_plan = db.scalar(
                select(WorkoutVersion)
                .join(Workout)
                .where(
                    Workout.student_id == student.id,
                    WorkoutVersion.status == WorkoutStatus.APPROVED,
                )
                .order_by(WorkoutVersion.approved_at.desc())
                .limit(1)
            )
        if current_plan is not None:
            context["current_plan"] = {"goal": current_plan.goal}
            has_plan = True
    has_evolution = False
    if data.include_recent_evolution:
        latest = db.scalar(
            select(Assessment)
            .where(Assessment.student_id == student.id)
            .order_by(Assessment.assessment_date.desc(), Assessment.created_at.desc())
            .limit(1)
        )
        if latest is not None:
            context["recent_evolution"] = {
                "assessment_date": latest.assessment_date.isoformat(),
                "weight_kg": latest.weight_kg,
            }
            has_evolution = True
    context = {key: value for key, value in context.items() if value is not None}
    return context, ContextPreview(
        fields=list(context), has_current_plan=has_plan, has_recent_evolution=has_evolution
    )


def preview(db: Session, actor: User, student_id: UUID, kind: Kind) -> ContextPreview:
    return _context(db, actor, student_id, kind, GenerationInput())[1]


def _latest_completed(db: Session, student_id: UUID) -> ReevaluationRequest | None:
    return db.scalar(
        select(ReevaluationRequest)
        .where(
            ReevaluationRequest.student_id == student_id,
            ReevaluationRequest.status == ReevaluationStatus.COMPLETED,
            ReevaluationRequest.snapshot.is_not(None),
        )
        .order_by(ReevaluationRequest.completed_at.desc(), ReevaluationRequest.id.desc())
        .limit(1)
    )


def _latest_version(
    db: Session, student_id: UUID, professional_id: UUID, kind: Kind
) -> DietVersion | WorkoutVersion | None:
    if kind == "diet":
        return db.scalar(
            select(DietVersion)
            .join(Diet)
            .where(
                Diet.student_id == student_id,
                Diet.professional_id == professional_id,
            )
            .order_by(DietVersion.created_at.desc(), DietVersion.id.desc())
            .limit(1)
        )
    return db.scalar(
        select(WorkoutVersion)
        .join(Workout)
        .where(
            Workout.student_id == student_id,
            Workout.professional_id == professional_id,
        )
        .order_by(WorkoutVersion.created_at.desc(), WorkoutVersion.id.desc())
        .limit(1)
    )


def _existing_version(
    db: Session, student_id: UUID, professional_id: UUID, kind: Kind
) -> DietVersion | WorkoutVersion | None:
    version = _latest_version(db, student_id, professional_id, kind)
    completed = _latest_completed(db, student_id)
    if (
        version
        and completed
        and completed.completed_at
        and completed.completed_at > version.created_at
    ):
        return None
    return version


def plans_state(db: Session, actor: User, student_id: UUID) -> PlansState:
    student = get_student(db, actor, student_id)
    if student.status != StudentStatus.ACTIVE or student.professional_id is None:
        raise HTTPException(409, "A geração exige um aluno ativo da carteira atual.")
    professional_id = student.professional_id

    def reference(kind: Kind) -> PlanReference | None:
        version = _existing_version(db, student.id, professional_id, kind)
        if version is None:
            return None
        return PlanReference(
            id=version.id, status=version.status.value, source=version.source.value
        )

    return PlansState(diet=reference("diet"), workout=reference("workout"))


def generate(
    db: Session,
    actor: User,
    student_id: UUID,
    kind: Kind,
    data: GenerationInput,
    settings: Settings,
    provider: AIProvider,
) -> DietVersion | WorkoutVersion:
    if not settings.ai_enabled or not settings.ai_api_key:
        raise HTTPException(503, "NutraMove AI não está configurado.")
    context, _ = _context(db, actor, student_id, kind, data)
    student = get_student(db, actor, student_id)
    completed_before = _latest_completed(db, student.id)
    if student.professional_id is None:
        raise HTTPException(409, "A geração exige um aluno ativo da carteira atual.")
    existing = _existing_version(db, student.id, student.professional_id, kind)
    if existing is not None:
        return existing
    db.rollback()  # Release the read transaction during the external call.
    schema_type = DietContent if kind == "diet" else WorkoutContent
    try:
        output = provider.generate_structured(
            kind=kind, context=context, schema=schema_type.model_json_schema()
        )
        try:
            validate_scope(output)
        except ValueError:
            logger.warning("AI generation rejected operation=%s category=safety_validation", kind)
            raise
        if kind == "diet":
            diet_content = DietContent.model_validate(output)
            if not diet_content.meals or any(not meal.foods for meal in diet_content.meals):
                raise ValueError("empty diet")
        else:
            workout_content = WorkoutContent.model_validate(output)
            if not 1 <= sum(not day.is_rest for day in workout_content.days) <= 6:
                logger.warning(
                    "AI generation rejected operation=workout category=schema_validation "
                    "field=days validation=missing_active_day"
                )
                raise ValueError("empty workout")
            for index, day in enumerate(workout_content.days):
                if not day.is_rest and not day.exercises:
                    logger.warning(
                        "AI generation rejected operation=workout category=schema_validation "
                        "field=days.%s.exercises validation=empty_non_rest_day",
                        index,
                    )
                    raise ValueError("empty non-rest day")
    except ProviderFailure:
        db.rollback()
        raise HTTPException(503, "Serviço de IA indisponível. Tente novamente.") from None
    except ValidationError as error:
        for issue in error.errors(include_url=False, include_input=False):
            field = _validation_field(issue["loc"])
            logger.warning(
                "AI generation rejected operation=%s category=schema_validation "
                "field=%s validation=%s",
                kind,
                field,
                issue["type"],
            )
        db.rollback()
        raise HTTPException(502, "A IA retornou uma sugestão inválida. Tente novamente.") from None
    except (ValueError, TypeError):
        db.rollback()
        raise HTTPException(502, "A IA retornou uma sugestão inválida. Tente novamente.") from None
    # Recheck the portfolio under a row lock after the potentially slow external call.
    student = get_student(db, actor, student_id, lock=True)
    if student.status != StudentStatus.ACTIVE or student.professional_id is None:
        raise HTTPException(409, "A situação do aluno mudou durante a geração.")
    completed_after = _latest_completed(db, student.id)
    if (completed_before.id if completed_before else None) != (
        completed_after.id if completed_after else None
    ):
        raise HTTPException(409, "A reavaliação mudou durante a geração. Tente novamente.")
    existing = _existing_version(db, student.id, student.professional_id, kind)
    if existing is not None:
        db.commit()
        return existing
    if kind == "diet":
        diet_plan = db.scalar(
            select(Diet)
            .where(
                Diet.student_id == student.id,
                Diet.professional_id == student.professional_id,
            )
            .order_by(Diet.created_at.desc(), Diet.id.desc())
            .limit(1)
            .with_for_update()
        )
        if diet_plan is None:
            diet_plan = Diet(
                student_id=student.id,
                professional_id=student.professional_id,
                name=diet_content.name,
            )
            db.add(diet_plan)
            db.flush()
        diet_version = diets.new_version(db, actor, diet_plan, diet_content)
        diet_version.created_at = datetime.now(UTC)
        diet_version.source = DietSource.AI_GENERATED
        diet_version.status = DietStatus.PENDING_REVIEW
        diets.commit(db)
    else:
        workout_plan = db.scalar(
            select(Workout)
            .where(
                Workout.student_id == student.id,
                Workout.professional_id == student.professional_id,
            )
            .order_by(Workout.created_at.desc(), Workout.id.desc())
            .limit(1)
            .with_for_update()
        )
        if workout_plan is None:
            workout_plan = Workout(
                student_id=student.id,
                professional_id=student.professional_id,
                name=workout_content.name,
            )
            db.add(workout_plan)
            db.flush()
        workout_version = workouts.new_version(db, actor, workout_plan, workout_content)
        workout_version.created_at = datetime.now(UTC)
        workout_version.source = WorkoutSource.AI_GENERATED
        workout_version.status = WorkoutStatus.PENDING_REVIEW
        workouts.commit(db)
        return workout_version
    return diet_version

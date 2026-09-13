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
from app.models.workout import Workout, WorkoutSource, WorkoutStatus, WorkoutVersion
from app.schemas.diet import VersionContent as DietContent
from app.schemas.workout import VersionContent as WorkoutContent
from app.services import diets, workouts
from app.services.students import get as get_student

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


def _context(
    db: Session, actor: User, student_id: UUID, kind: Kind, data: GenerationInput
) -> tuple[dict[str, Any], ContextPreview]:
    student = get_student(db, actor, student_id)
    if student.status != StudentStatus.ACTIVE or student.professional_id is None:
        raise HTTPException(409, "A geração exige um aluno ativo da carteira atual.")
    context: dict[str, Any] = {
        "goal": student.goal.value,
        "goal_detail": student.goal_detail,
        "activity_level": student.activity_level.value,
        "professional_instructions": data.instructions,
    }
    if kind == "workout":
        context.update(
            training_experience=student.training_experience.value,
            training_frequency=student.training_frequency,
            preferred_training_time=student.preferred_training_time,
        )

    else:
        context.update(
            meal_schedule=student.meal_schedule,
            food_preferences=student.food_preferences,
            food_restrictions=student.food_restrictions,
        )

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
    db.rollback()  # Release the read transaction during the external call.
    schema_type = DietContent if kind == "diet" else WorkoutContent
    try:
        output = provider.generate_structured(
            kind=kind, context=context, schema=schema_type.model_json_schema()
        )
        validate_scope(output)
        if kind == "diet":
            diet_content = DietContent.model_validate(output)
            if not diet_content.meals or any(not meal.foods for meal in diet_content.meals):
                raise ValueError("empty diet")
        else:
            workout_content = WorkoutContent.model_validate(output)
            if not workout_content.days or any(not day.exercises for day in workout_content.days):
                raise ValueError("empty workout")
    except ProviderFailure:
        db.rollback()
        raise HTTPException(503, "Serviço de IA indisponível. Tente novamente.") from None
    except (ValidationError, ValueError, TypeError):
        db.rollback()
        raise HTTPException(502, "A IA retornou uma sugestão inválida. Tente novamente.") from None
    # Recheck the portfolio under a row lock after the potentially slow external call.
    student = get_student(db, actor, student_id, lock=True)
    if student.status != StudentStatus.ACTIVE or student.professional_id is None:
        raise HTTPException(409, "A situação do aluno mudou durante a geração.")
    if kind == "diet":
        diet_plan = Diet(
            student_id=student.id, professional_id=student.professional_id, name=diet_content.name
        )
        db.add(diet_plan)
        db.flush()
        diet_version = diets.new_version(db, actor, diet_plan, diet_content)
        diet_version.source = DietSource.AI_GENERATED
        diet_version.status = DietStatus.PENDING_REVIEW
        diets.commit(db)
    else:
        workout_plan = Workout(
            student_id=student.id,
            professional_id=student.professional_id,
            name=workout_content.name,
        )
        db.add(workout_plan)
        db.flush()
        workout_version = workouts.new_version(db, actor, workout_plan, workout_content)
        workout_version.source = WorkoutSource.AI_GENERATED
        workout_version.status = WorkoutStatus.PENDING_REVIEW
        workouts.commit(db)
        return workout_version
    return diet_version

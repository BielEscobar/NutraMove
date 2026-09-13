from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.ai.generation import ContextPreview, GenerationInput, generate, preview
from app.ai.provider import AIProvider, OpenAIProvider
from app.api.dependencies import AppSettings, CurrentUser, DbSession, require_roles
from app.api.professionals import no_cache
from app.models import UserRole
from app.schemas.diet import VersionResponse as DietResponse
from app.schemas.workout import VersionResponse as WorkoutResponse

router = APIRouter(
    prefix="/professional",
    tags=["NutraMove AI"],
    dependencies=[Depends(require_roles(UserRole.PROFESSIONAL)), Depends(no_cache)],
)


def get_ai_provider(settings: AppSettings) -> AIProvider:
    return OpenAIProvider(settings)


Provider = Annotated[AIProvider, Depends(get_ai_provider)]


@router.get("/ai/config")
def config(settings: AppSettings) -> dict[str, bool]:
    return {"enabled": settings.ai_enabled and bool(settings.ai_api_key)}


@router.get("/students/{student_id}/ai/{kind}/context", response_model=ContextPreview)
def context(student_id: UUID, kind: str, db: DbSession, actor: CurrentUser) -> ContextPreview:
    if kind not in {"diet", "workout"}:
        from fastapi import HTTPException

        raise HTTPException(404, "Tipo de geração desconhecido.")
    return preview(db, actor, student_id, "diet" if kind == "diet" else "workout")


@router.post("/students/{student_id}/ai/diet", status_code=201, response_model=DietResponse)
def generate_diet(
    student_id: UUID,
    data: GenerationInput,
    db: DbSession,
    actor: CurrentUser,
    settings: AppSettings,
    provider: Provider,
) -> DietResponse:
    return DietResponse.model_validate(
        generate(db, actor, student_id, "diet", data, settings, provider)
    )


@router.post("/students/{student_id}/ai/workout", status_code=201, response_model=WorkoutResponse)
def generate_workout(
    student_id: UUID,
    data: GenerationInput,
    db: DbSession,
    actor: CurrentUser,
    settings: AppSettings,
    provider: Provider,
) -> WorkoutResponse:
    return WorkoutResponse.model_validate(
        generate(db, actor, student_id, "workout", data, settings, provider)
    )

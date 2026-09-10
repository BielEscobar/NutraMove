from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import CurrentUser, DbSession, require_roles
from app.api.professionals import no_cache
from app.models import UserRole
from app.repositories import diets
from app.schemas.diet import (
    ApprovalInput,
    DietResponse,
    StudentDiet,
    StudentDietResponse,
    VersionContent,
    VersionResponse,
    VersionSummary,
    VersionUpdate,
)
from app.services import diets as service

professional_router = APIRouter(
    prefix="/professional",
    tags=["professional diets"],
    dependencies=[Depends(require_roles(UserRole.PROFESSIONAL)), Depends(no_cache)],
)
master_router = APIRouter(
    prefix="/master",
    tags=["master diets"],
    dependencies=[Depends(require_roles(UserRole.MASTER)), Depends(no_cache)],
)
student_router = APIRouter(
    prefix="/student",
    tags=["student diet"],
    dependencies=[Depends(require_roles(UserRole.STUDENT)), Depends(no_cache)],
)


@professional_router.post(
    "/students/{student_id}/diets", status_code=201, response_model=VersionResponse
)
def create(
    student_id: UUID, data: VersionContent, db: DbSession, actor: CurrentUser
) -> VersionResponse:
    return VersionResponse.model_validate(service.create_diet(db, actor, student_id, data))


@professional_router.get("/students/{student_id}/diets", response_model=list[DietResponse])
@master_router.get("/students/{student_id}/diets", response_model=list[DietResponse])
def list_diets(student_id: UUID, db: DbSession, actor: CurrentUser) -> list[DietResponse]:
    return [DietResponse.model_validate(item) for item in diets.list_diets(db, actor, student_id)]


@professional_router.get("/diets/{diet_id}", response_model=DietResponse)
@master_router.get("/diets/{diet_id}", response_model=DietResponse)
def detail(diet_id: UUID, db: DbSession, actor: CurrentUser) -> DietResponse:
    return DietResponse.model_validate(diets.get_diet(db, actor, diet_id))


@professional_router.get("/diets/{diet_id}/versions", response_model=list[VersionSummary])
@master_router.get("/diets/{diet_id}/versions", response_model=list[VersionSummary])
def versions(diet_id: UUID, db: DbSession, actor: CurrentUser) -> list[VersionSummary]:
    return [VersionSummary.model_validate(item) for item in diets.list_versions(db, actor, diet_id)]


@professional_router.post(
    "/diets/{diet_id}/versions", status_code=201, response_model=VersionResponse
)
def create_version(
    diet_id: UUID, data: VersionContent, db: DbSession, actor: CurrentUser
) -> VersionResponse:
    return VersionResponse.model_validate(service.create_version(db, actor, diet_id, data))


@professional_router.get("/diet-versions/{version_id}", response_model=VersionResponse)
@master_router.get("/diet-versions/{version_id}", response_model=VersionResponse)
def version_detail(version_id: UUID, db: DbSession, actor: CurrentUser) -> VersionResponse:
    return VersionResponse.model_validate(diets.get_version(db, actor, version_id))


@professional_router.patch("/diet-versions/{version_id}", response_model=VersionResponse)
def edit(
    version_id: UUID, data: VersionUpdate, db: DbSession, actor: CurrentUser
) -> VersionResponse:
    return VersionResponse.model_validate(service.edit(db, actor, version_id, data))


@professional_router.post(
    "/diet-versions/{version_id}/duplicate", status_code=201, response_model=VersionResponse
)
def duplicate(version_id: UUID, db: DbSession, actor: CurrentUser) -> VersionResponse:
    return VersionResponse.model_validate(service.duplicate(db, actor, version_id))


@professional_router.post("/diet-versions/{version_id}/approve", response_model=VersionResponse)
def approve(
    version_id: UUID, data: ApprovalInput, db: DbSession, actor: CurrentUser
) -> VersionResponse:
    return VersionResponse.model_validate(
        service.approve(db, actor, version_id, data.expected_revision)
    )


@student_router.get("/diet", response_model=StudentDietResponse)
def current(db: DbSession, actor: CurrentUser) -> StudentDietResponse:
    version = diets.current_student_version(db, actor)
    return StudentDietResponse(diet=StudentDiet.model_validate(version) if version else None)

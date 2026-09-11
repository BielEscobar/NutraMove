from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import CurrentUser, DbSession, require_roles
from app.api.professionals import no_cache
from app.models import UserRole
from app.repositories import workouts
from app.schemas.workout import (
    ApprovalInput,
    StudentWorkout,
    StudentWorkoutResponse,
    VersionContent,
    VersionResponse,
    VersionSummary,
    VersionUpdate,
    WorkoutResponse,
)
from app.services import workouts as service

professional_router = APIRouter(
    prefix="/professional",
    tags=["professional workouts"],
    dependencies=[Depends(require_roles(UserRole.PROFESSIONAL)), Depends(no_cache)],
)
master_router = APIRouter(
    prefix="/master",
    tags=["master workouts"],
    dependencies=[Depends(require_roles(UserRole.MASTER)), Depends(no_cache)],
)
student_router = APIRouter(
    prefix="/student",
    tags=["student workout"],
    dependencies=[Depends(require_roles(UserRole.STUDENT)), Depends(no_cache)],
)


@professional_router.post(
    "/students/{student_id}/workouts", status_code=201, response_model=VersionResponse
)
def create(
    student_id: UUID, data: VersionContent, db: DbSession, actor: CurrentUser
) -> VersionResponse:
    return VersionResponse.model_validate(service.create_workout(db, actor, student_id, data))


@professional_router.get("/students/{student_id}/workouts", response_model=list[WorkoutResponse])
@master_router.get("/students/{student_id}/workouts", response_model=list[WorkoutResponse])
def list_workouts(student_id: UUID, db: DbSession, actor: CurrentUser) -> list[WorkoutResponse]:
    return [
        WorkoutResponse.model_validate(item)
        for item in workouts.list_workouts(db, actor, student_id)
    ]


@professional_router.get("/workouts/{workout_id}", response_model=WorkoutResponse)
@master_router.get("/workouts/{workout_id}", response_model=WorkoutResponse)
def detail(workout_id: UUID, db: DbSession, actor: CurrentUser) -> WorkoutResponse:
    return WorkoutResponse.model_validate(workouts.get_workout(db, actor, workout_id))


@professional_router.get("/workouts/{workout_id}/versions", response_model=list[VersionSummary])
@master_router.get("/workouts/{workout_id}/versions", response_model=list[VersionSummary])
def versions(workout_id: UUID, db: DbSession, actor: CurrentUser) -> list[VersionSummary]:
    return [
        VersionSummary.model_validate(item)
        for item in workouts.list_versions(db, actor, workout_id)
    ]


@professional_router.post(
    "/workouts/{workout_id}/versions", status_code=201, response_model=VersionResponse
)
def create_version(
    workout_id: UUID, data: VersionContent, db: DbSession, actor: CurrentUser
) -> VersionResponse:
    return VersionResponse.model_validate(service.create_version(db, actor, workout_id, data))


@professional_router.get("/workout-versions/{version_id}", response_model=VersionResponse)
@master_router.get("/workout-versions/{version_id}", response_model=VersionResponse)
def version_detail(version_id: UUID, db: DbSession, actor: CurrentUser) -> VersionResponse:
    return VersionResponse.model_validate(workouts.get_version(db, actor, version_id))


@professional_router.patch("/workout-versions/{version_id}", response_model=VersionResponse)
def edit(
    version_id: UUID, data: VersionUpdate, db: DbSession, actor: CurrentUser
) -> VersionResponse:
    return VersionResponse.model_validate(service.edit(db, actor, version_id, data))


@professional_router.post(
    "/workout-versions/{version_id}/duplicate", status_code=201, response_model=VersionResponse
)
def duplicate(version_id: UUID, db: DbSession, actor: CurrentUser) -> VersionResponse:
    return VersionResponse.model_validate(service.duplicate(db, actor, version_id))


@professional_router.post("/workout-versions/{version_id}/approve", response_model=VersionResponse)
def approve(
    version_id: UUID, data: ApprovalInput, db: DbSession, actor: CurrentUser
) -> VersionResponse:
    return VersionResponse.model_validate(
        service.approve(db, actor, version_id, data.expected_revision)
    )


@student_router.get("/workout", response_model=StudentWorkoutResponse)
def current(db: DbSession, actor: CurrentUser) -> StudentWorkoutResponse:
    version = workouts.current_student_version(db, actor)
    return StudentWorkoutResponse(
        workout=StudentWorkout.model_validate(version) if version else None
    )

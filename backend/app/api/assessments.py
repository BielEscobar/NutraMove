from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import CurrentUser, DbSession, require_roles
from app.api.professionals import no_cache
from app.models import UserRole
from app.repositories import assessments
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentList,
    AssessmentResponse,
    AssessmentUpdate,
    EvolutionResponse,
    Period,
    StaffAssessmentResponse,
)
from app.services import assessments as service

professional_router = APIRouter(
    prefix="/professional",
    tags=["assessments"],
    dependencies=[Depends(require_roles(UserRole.PROFESSIONAL)), Depends(no_cache)],
)
master_router = APIRouter(
    prefix="/master",
    tags=["assessments"],
    dependencies=[Depends(require_roles(UserRole.MASTER)), Depends(no_cache)],
)
student_router = APIRouter(
    prefix="/student",
    tags=["evolution"],
    dependencies=[Depends(require_roles(UserRole.STUDENT)), Depends(no_cache)],
)
Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]


@professional_router.get("/students/{student_id}/assessments")
@master_router.get("/students/{student_id}/assessments")
def listing(
    student_id: UUID, db: DbSession, actor: CurrentUser, page: Page = 1, page_size: PageSize = 20
) -> AssessmentList:
    return assessments.list_assessments(db, actor, student_id, page, page_size)


@professional_router.post("/students/{student_id}/assessments", status_code=201)
def create(
    student_id: UUID, data: AssessmentCreate, db: DbSession, actor: CurrentUser
) -> StaffAssessmentResponse:
    return StaffAssessmentResponse.model_validate(service.create(db, actor, student_id, data))


@professional_router.get("/assessments/{assessment_id}")
@master_router.get("/assessments/{assessment_id}")
def detail(assessment_id: UUID, db: DbSession, actor: CurrentUser) -> StaffAssessmentResponse:
    return StaffAssessmentResponse.model_validate(assessments.detail(db, actor, assessment_id))


@professional_router.patch("/assessments/{assessment_id}")
def edit(
    assessment_id: UUID, data: AssessmentUpdate, db: DbSession, actor: CurrentUser
) -> StaffAssessmentResponse:
    return StaffAssessmentResponse.model_validate(service.edit(db, actor, assessment_id, data))


@professional_router.get("/students/{student_id}/evolution")
@master_router.get("/students/{student_id}/evolution")
def evolution(
    student_id: UUID, db: DbSession, actor: CurrentUser, period: Period = "90d"
) -> EvolutionResponse:
    return assessments.evolution(db, actor, student_id, period)


@student_router.get("/evolution")
def own_evolution(db: DbSession, actor: CurrentUser, period: Period = "90d") -> EvolutionResponse:
    return assessments.evolution(db, actor, None, period)


@student_router.get("/assessments")
def own_list(
    db: DbSession, actor: CurrentUser, page: Page = 1, page_size: PageSize = 20
) -> AssessmentList:
    return assessments.list_assessments(db, actor, None, page, page_size)


@student_router.get("/assessments/{assessment_id}")
def own_detail(assessment_id: UUID, db: DbSession, actor: CurrentUser) -> AssessmentResponse:
    return AssessmentResponse.model_validate(assessments.detail(db, actor, assessment_id))

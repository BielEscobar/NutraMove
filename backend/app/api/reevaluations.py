from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import CurrentUser, DbSession, require_roles
from app.api.professionals import no_cache
from app.models import UserRole
from app.models.reevaluation import ReevaluationRequest
from app.repositories import reevaluations
from app.schemas.reevaluation import (
    ReevaluationBrief,
    ReevaluationComplete,
    ReevaluationCreate,
    ReevaluationFilters,
    ReevaluationList,
    ReevaluationResponse,
    StaffReevaluationBrief,
    StaffReevaluationFilters,
    StaffReevaluationList,
    StaffReevaluationResponse,
)
from app.services import reevaluations as service
from app.services.students import get

student_router = APIRouter(
    prefix="/student/reevaluation-requests",
    tags=["reevaluations"],
    dependencies=[Depends(require_roles(UserRole.STUDENT)), Depends(no_cache)],
)
professional_router = APIRouter(
    prefix="/professional/reevaluation-requests",
    tags=["reevaluations"],
    dependencies=[Depends(require_roles(UserRole.PROFESSIONAL)), Depends(no_cache)],
)
master_router = APIRouter(
    prefix="/master/reevaluation-requests",
    tags=["reevaluations"],
    dependencies=[Depends(require_roles(UserRole.MASTER)), Depends(no_cache)],
)


def staff_response(
    db: DbSession, actor: CurrentUser, record: ReevaluationRequest
) -> StaffReevaluationResponse:
    owner = get(db, actor, record.student_id)
    return StaffReevaluationResponse(
        **ReevaluationResponse.model_validate(record).model_dump(),
        student_id=owner.id,
        student_name=owner.user.name,
    )


@student_router.post("", status_code=201)
def create(data: ReevaluationCreate, db: DbSession, actor: CurrentUser) -> ReevaluationResponse:
    return ReevaluationResponse.model_validate(service.create(db, actor, data))


@student_router.get("")
def own_list(
    db: DbSession, actor: CurrentUser, filters: Annotated[ReevaluationFilters, Query()]
) -> ReevaluationList:
    rows, total = reevaluations.listing(db, actor, filters)
    return ReevaluationList(
        items=[
            ReevaluationBrief(
                id=r.id,
                category=r.category,
                reason_summary=r.reason[:160],
                status=r.status,
                created_at=r.created_at,
            )
            for r, _ in rows
        ],
        total=total,
        page=filters.page,
        page_size=filters.page_size,
    )


@professional_router.get("")
@master_router.get("")
def listing(
    db: DbSession, actor: CurrentUser, filters: Annotated[StaffReevaluationFilters, Query()]
) -> StaffReevaluationList:
    rows, total = reevaluations.listing(db, actor, filters)
    return StaffReevaluationList(
        items=[
            StaffReevaluationBrief(
                id=r.id,
                category=r.category,
                reason_summary=r.reason[:160],
                status=r.status,
                created_at=r.created_at,
                student_id=r.student_id,
                student_name=name,
            )
            for r, name in rows
        ],
        total=total,
        page=filters.page,
        page_size=filters.page_size,
    )


@student_router.get("/{request_id}")
def own_detail(request_id: UUID, db: DbSession, actor: CurrentUser) -> ReevaluationResponse:
    return ReevaluationResponse.model_validate(reevaluations.detail(db, actor, request_id))


@professional_router.get("/{request_id}")
@master_router.get("/{request_id}")
def detail(request_id: UUID, db: DbSession, actor: CurrentUser) -> StaffReevaluationResponse:
    return staff_response(db, actor, reevaluations.detail(db, actor, request_id))


@student_router.post("/{request_id}/cancel")
def own_cancel(request_id: UUID, db: DbSession, actor: CurrentUser) -> ReevaluationResponse:
    return ReevaluationResponse.model_validate(service.transition(db, actor, request_id, "cancel"))


@professional_router.post("/{request_id}/start-review")
def start_review(request_id: UUID, db: DbSession, actor: CurrentUser) -> StaffReevaluationResponse:
    return staff_response(db, actor, service.transition(db, actor, request_id, "start-review"))


@professional_router.post("/{request_id}/complete")
def complete(
    request_id: UUID, data: ReevaluationComplete, db: DbSession, actor: CurrentUser
) -> StaffReevaluationResponse:
    return staff_response(
        db, actor, service.transition(db, actor, request_id, "complete", data.professional_response)
    )


@professional_router.post("/{request_id}/cancel")
def cancel(request_id: UUID, db: DbSession, actor: CurrentUser) -> StaffReevaluationResponse:
    return staff_response(db, actor, service.transition(db, actor, request_id, "cancel"))

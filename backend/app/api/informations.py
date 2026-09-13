from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import CurrentUser, DbSession, require_roles
from app.api.professionals import no_cache
from app.models import UserRole
from app.repositories import informations
from app.schemas.information import (
    InformationBrief,
    InformationContent,
    InformationFilters,
    InformationList,
    InformationResponse,
    InformationUpdate,
    RevisionInput,
    StaffInformationBrief,
    StaffInformationFilters,
    StaffInformationList,
    StaffInformationResponse,
)
from app.services import informations as service

professional_router = APIRouter(
    prefix="/professional/informations",
    tags=["informations"],
    dependencies=[Depends(require_roles(UserRole.PROFESSIONAL)), Depends(no_cache)],
)
master_router = APIRouter(
    prefix="/master/informations",
    tags=["informations"],
    dependencies=[Depends(require_roles(UserRole.MASTER)), Depends(no_cache)],
)
student_router = APIRouter(
    prefix="/student/informations",
    tags=["informations"],
    dependencies=[Depends(require_roles(UserRole.STUDENT)), Depends(no_cache)],
)


@professional_router.get("")
@master_router.get("")
def listing(
    db: DbSession, actor: CurrentUser, filters: Annotated[StaffInformationFilters, Query()]
) -> StaffInformationList:
    items, total = informations.listing(db, actor, filters)
    return StaffInformationList(
        items=[
            StaffInformationBrief(
                id=r.id,
                title=r.title,
                summary=r.content[:200],
                category=r.category,
                published_at=r.published_at,
                student_id=r.student_id,
                status=r.status,
            )
            for r in items
        ],
        total=total,
        page=filters.page,
        page_size=filters.page_size,
    )


@student_router.get("")
def own_list(
    db: DbSession, actor: CurrentUser, filters: Annotated[InformationFilters, Query()]
) -> InformationList:
    items, total = informations.listing(db, actor, filters)
    return InformationList(
        items=[
            InformationBrief(
                id=r.id,
                title=r.title,
                summary=r.content[:200],
                category=r.category,
                published_at=r.published_at,
            )
            for r in items
        ],
        total=total,
        page=filters.page,
        page_size=filters.page_size,
    )


@professional_router.get("/{information_id}")
@master_router.get("/{information_id}")
def detail(information_id: UUID, db: DbSession, actor: CurrentUser) -> StaffInformationResponse:
    return StaffInformationResponse.model_validate(informations.detail(db, actor, information_id))


@student_router.get("/{information_id}")
def own_detail(information_id: UUID, db: DbSession, actor: CurrentUser) -> InformationResponse:
    return InformationResponse.model_validate(informations.detail(db, actor, information_id))


@professional_router.post("", status_code=201)
def create(data: InformationContent, db: DbSession, actor: CurrentUser) -> StaffInformationResponse:
    return StaffInformationResponse.model_validate(service.create(db, actor, data))


@professional_router.patch("/{information_id}")
def edit(
    information_id: UUID, data: InformationUpdate, db: DbSession, actor: CurrentUser
) -> StaffInformationResponse:
    return StaffInformationResponse.model_validate(service.edit(db, actor, information_id, data))


@professional_router.post("/{information_id}/publish")
def publish(
    information_id: UUID, data: RevisionInput, db: DbSession, actor: CurrentUser
) -> StaffInformationResponse:
    return StaffInformationResponse.model_validate(
        service.transition(db, actor, information_id, data.expected_revision, publish=True)
    )


@professional_router.post("/{information_id}/archive")
def archive(
    information_id: UUID, data: RevisionInput, db: DbSession, actor: CurrentUser
) -> StaffInformationResponse:
    return StaffInformationResponse.model_validate(
        service.transition(db, actor, information_id, data.expected_revision, publish=False)
    )

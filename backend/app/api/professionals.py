from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.api.dependencies import DbSession, require_roles
from app.models.user import UserRole
from app.repositories import professionals
from app.schemas.professional import (
    ProfessionalCreate,
    ProfessionalList,
    ProfessionalResponse,
    ProfessionalSummary,
    ProfessionalUpdate,
)
from app.services import professionals as service


def no_cache(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(
    prefix="/master/professionals",
    tags=["master"],
    dependencies=[Depends(require_roles(UserRole.MASTER)), Depends(no_cache)],
)


@router.get("", response_model=ProfessionalList)
def list_professionals(
    db: DbSession,
    q: Annotated[str, Query(max_length=120)] = "",
    is_active: bool | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ProfessionalList:
    items, total = professionals.list_professionals(db, q.strip(), is_active, page, page_size)
    return ProfessionalList(
        items=[service.to_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/summary", response_model=ProfessionalSummary)
def summary(db: DbSession) -> ProfessionalSummary:
    total, active = professionals.summary(db)
    return ProfessionalSummary(total=total, active=active, inactive=total - active)


@router.post("", status_code=201, response_model=ProfessionalResponse)
def create(data: ProfessionalCreate, db: DbSession) -> ProfessionalResponse:
    return service.to_response(service.create(db, data))


@router.get("/{professional_id}", response_model=ProfessionalResponse)
def detail(professional_id: UUID, db: DbSession) -> ProfessionalResponse:
    return service.to_response(service.get_professional(db, professional_id))


@router.patch("/{professional_id}", response_model=ProfessionalResponse)
def update(professional_id: UUID, data: ProfessionalUpdate, db: DbSession) -> ProfessionalResponse:
    return service.to_response(service.update(db, professional_id, data))


@router.post("/{professional_id}/activate", response_model=ProfessionalResponse)
def activate(professional_id: UUID, db: DbSession) -> ProfessionalResponse:
    return service.to_response(service.set_active(db, professional_id, active=True))


@router.post("/{professional_id}/deactivate", response_model=ProfessionalResponse)
def deactivate(professional_id: UUID, db: DbSession) -> ProfessionalResponse:
    return service.to_response(service.set_active(db, professional_id, active=False))

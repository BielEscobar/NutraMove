from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import AppSettings, CurrentUser, DbSession, require_roles
from app.api.professionals import no_cache
from app.models import UserRole
from app.repositories import hydration
from app.schemas.hydration import (
    HydrationDay,
    HydrationHistory,
    HydrationSummary,
    WaterCreate,
    WaterResponse,
)
from app.services import hydration as service
from app.services.students import get

student_router = APIRouter(
    prefix="/student",
    tags=["hydration"],
    dependencies=[Depends(require_roles(UserRole.STUDENT)), Depends(no_cache)],
)
professional_router = APIRouter(
    prefix="/professional",
    tags=["hydration"],
    dependencies=[Depends(require_roles(UserRole.PROFESSIONAL)), Depends(no_cache)],
)
master_router = APIRouter(
    prefix="/master",
    tags=["hydration"],
    dependencies=[Depends(require_roles(UserRole.MASTER)), Depends(no_cache)],
)
Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
Days = Annotated[int, Query(ge=1, le=30)]


def validate_days(days: int) -> int:
    from fastapi import HTTPException

    if days not in (1, 7, 30):
        raise HTTPException(422, "Escolha 1, 7 ou 30 dias.")
    return days


@student_router.post("/water-records", status_code=201)
def create(data: WaterCreate, db: DbSession, actor: CurrentUser) -> WaterResponse:
    return WaterResponse.model_validate(service.create(db, actor, data))


@student_router.get("/hydration/summary")
def summary(db: DbSession, actor: CurrentUser, settings: AppSettings) -> HydrationSummary:
    return service.summary(db, actor, settings.business_timezone)


@student_router.get("/hydration")
def own_day(
    db: DbSession,
    actor: CurrentUser,
    settings: AppSettings,
    page: Page = 1,
    page_size: PageSize = 20,
) -> HydrationDay:
    return service.daily(db, actor, settings.business_timezone, None, page, page_size)


@professional_router.get("/students/{student_id}/hydration")
@master_router.get("/students/{student_id}/hydration")
def day(
    student_id: UUID,
    db: DbSession,
    actor: CurrentUser,
    settings: AppSettings,
    page: Page = 1,
    page_size: PageSize = 20,
) -> HydrationDay:
    return service.daily(db, actor, settings.business_timezone, student_id, page, page_size)


@student_router.get("/hydration/history")
def own_history(
    db: DbSession, actor: CurrentUser, settings: AppSettings, days: Days = 7
) -> HydrationHistory:
    owner = get(db, actor)
    return hydration.history(db, owner.id, settings.business_timezone, validate_days(days))


@professional_router.get("/students/{student_id}/hydration/history")
@master_router.get("/students/{student_id}/hydration/history")
def history(
    student_id: UUID, db: DbSession, actor: CurrentUser, settings: AppSettings, days: Days = 7
) -> HydrationHistory:
    owner = get(db, actor, student_id)
    return hydration.history(db, owner.id, settings.business_timezone, validate_days(days))

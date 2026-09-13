from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import CurrentUser, DbSession, require_roles
from app.api.professionals import no_cache
from app.models import UserRole
from app.repositories import audit_logs
from app.schemas.audit_log import (
    AuditFilters,
    AuditList,
    AuditResponse,
    StudentTransfer,
    TransferResponse,
)
from app.services.transfers import transfer

router = APIRouter(
    prefix="/master",
    tags=["master audit"],
    dependencies=[Depends(require_roles(UserRole.MASTER)), Depends(no_cache)],
)


@router.post("/students/{student_id}/transfer")
def transfer_student(
    student_id: UUID, data: StudentTransfer, db: DbSession, actor: CurrentUser
) -> TransferResponse:
    return transfer(db, actor, student_id, data)


@router.get("/audit-logs")
def listing(db: DbSession, filters: Annotated[AuditFilters, Query()]) -> AuditList:
    return audit_logs.listing(db, filters)


@router.get("/audit-logs/{audit_id}")
def detail(audit_id: UUID, db: DbSession) -> AuditResponse:
    return audit_logs.detail(db, audit_id)

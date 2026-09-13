from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.audit_log import AuditAction


class StudentTransfer(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    new_professional_id: UUID
    expected_professional_id: UUID | None
    reason: str = Field(min_length=5, max_length=500)


class TransferResponse(BaseModel):
    student_id: UUID
    old_professional_id: UUID | None
    new_professional_id: UUID
    audit_log_id: UUID
    transferred_at: datetime


class AuditFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: AuditAction | None = None
    resource_id: UUID | None = None
    actor_user_id: UUID | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class AuditResponse(BaseModel):
    id: UUID
    actor_user_id: UUID
    actor_name: str
    action: AuditAction
    resource_type: str
    resource_id: UUID
    old_professional_id: UUID | None
    old_professional_name: str | None
    new_professional_id: UUID
    new_professional_name: str
    reason: str
    created_at: datetime


class AuditList(BaseModel):
    items: list[AuditResponse]
    total: int
    page: int
    page_size: int

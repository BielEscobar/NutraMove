from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.reevaluation import ReevaluationCategory, ReevaluationStatus


class ReevaluationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    category: ReevaluationCategory
    reason: str = Field(min_length=10, max_length=2000)


class ReevaluationComplete(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    professional_response: str = Field(min_length=1, max_length=2000)


class ReevaluationFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: ReevaluationStatus | None = None
    category: ReevaluationCategory | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class StaffReevaluationFilters(ReevaluationFilters):
    student_id: UUID | None = None


class ReevaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    category: ReevaluationCategory
    reason: str
    status: ReevaluationStatus
    professional_response: str | None
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None


class StaffReevaluationResponse(ReevaluationResponse):
    student_id: UUID
    student_name: str


class ReevaluationBrief(BaseModel):
    id: UUID
    category: ReevaluationCategory
    reason_summary: str
    status: ReevaluationStatus
    created_at: datetime


class StaffReevaluationBrief(ReevaluationBrief):
    student_id: UUID
    student_name: str


class ReevaluationList(BaseModel):
    items: list[ReevaluationBrief]
    total: int
    page: int
    page_size: int


class StaffReevaluationList(BaseModel):
    items: list[StaffReevaluationBrief]
    total: int
    page: int
    page_size: int

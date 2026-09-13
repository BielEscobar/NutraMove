from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.information import InformationCategory, InformationStatus


class InformationContent(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=3, max_length=160)
    content: str = Field(min_length=10, max_length=10000)
    category: InformationCategory
    student_id: UUID | None = None


class RevisionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(strict=True, ge=1)


class InformationUpdate(InformationContent, RevisionInput):
    pass


class InformationFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: InformationCategory | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class StaffInformationFilters(InformationFilters):
    status: InformationStatus | None = None
    student_id: UUID | None = None
    general_only: bool = False


class InformationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    content: str
    category: InformationCategory
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class StaffInformationResponse(InformationResponse):
    student_id: UUID | None
    status: InformationStatus
    edit_revision: int


class InformationBrief(BaseModel):
    id: UUID
    title: str
    summary: str
    category: InformationCategory
    published_at: datetime | None


class StaffInformationBrief(InformationBrief):
    student_id: UUID | None
    status: InformationStatus


class InformationList(BaseModel):
    items: list[InformationBrief]
    total: int
    page: int
    page_size: int


class StaffInformationList(BaseModel):
    items: list[StaffInformationBrief]
    total: int
    page: int
    page_size: int

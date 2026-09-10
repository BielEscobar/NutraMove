from datetime import date, datetime
from datetime import time as TimeValue
from decimal import Decimal
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.diet import DietSource, DietStatus

Name = Annotated[str, Field(min_length=1, max_length=160)]
Quantity = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=3, allow_inf_nan=False)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, from_attributes=True)


class SubstitutionInput(InputModel):
    name: Name
    quantity: Quantity | None = None
    unit: str | None = Field(default=None, min_length=1, max_length=40)
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def quantity_unit_pair(self) -> Self:
        if (self.quantity is None) != (self.unit is None):
            raise ValueError("Provide both quantity and unit, or neither.")
        return self


class FoodInput(InputModel):
    name: Name
    quantity: Quantity
    unit: str = Field(min_length=1, max_length=40)
    notes: str | None = Field(default=None, max_length=1000)
    substitutions: list[SubstitutionInput] = Field(default_factory=list, max_length=20)


class MealInput(InputModel):
    name: Name
    time: TimeValue | None = None
    foods: list[FoodInput] = Field(default_factory=list, max_length=50)

    @field_validator("time")
    @classmethod
    def local_time(cls, value: TimeValue | None) -> TimeValue | None:
        if value and value.tzinfo is not None:
            raise ValueError("Use local time without timezone.")
        return value


class VersionContent(InputModel):
    name: Name
    goal: str | None = Field(default=None, max_length=500)
    start_date: date | None = None
    next_review_date: date | None = None
    notes: str | None = Field(default=None, max_length=4000)
    meals: list[MealInput] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def chronological_dates(self) -> Self:
        if self.start_date and self.next_review_date and self.next_review_date < self.start_date:
            raise ValueError("Review date cannot precede start date.")
        return self


class VersionUpdate(VersionContent):
    expected_revision: int = Field(ge=1)


class ApprovalInput(InputModel):
    expected_revision: int = Field(ge=1)


class VersionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    diet_id: UUID
    version_number: int
    edit_revision: int
    name: str
    status: DietStatus
    source: DietSource
    approved_at: datetime | None
    created_at: datetime


class VersionResponse(VersionContent):
    id: UUID
    diet_id: UUID
    version_number: int
    edit_revision: int
    status: DietStatus
    source: DietSource
    created_by_user_id: UUID
    approved_by_user_id: UUID | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DietResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    student_id: UUID
    name: str
    created_at: datetime


class StudentDiet(VersionContent):
    version_number: int
    approved_at: datetime


class StudentDietResponse(BaseModel):
    diet: StudentDiet | None

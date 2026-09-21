from datetime import date, datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

from app.models.workout import WorkoutSource, WorkoutStatus

Name = Annotated[str, Field(min_length=1, max_length=160)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, from_attributes=True)


class ExerciseInput(InputModel):
    name: Name
    muscle_group: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    instructions: str | None = Field(default=None, max_length=2000)
    sets: int | None = Field(default=None, ge=1, le=100, strict=True)
    repetitions: str | None = Field(default=None, max_length=160)
    load: str | None = Field(default=None, max_length=160)
    duration: str | None = Field(default=None, max_length=160)
    rest_seconds: int | None = Field(default=None, ge=0, le=86400, strict=True)
    notes: str | None = Field(default=None, max_length=2000)


class DayInput(InputModel):
    name: Name
    description: str | None = Field(default=None, max_length=2000)
    is_rest: bool = Field(
        default=False,
        strict=True,
        validation_alias=AliasChoices("isRest", "is_rest"),
        serialization_alias="isRest",
    )
    exercises: list[ExerciseInput] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def rest_has_no_exercises(self) -> Self:
        if self.is_rest and self.exercises:
            raise ValueError("A rest day cannot contain exercises.")
        return self


class VersionContent(InputModel):
    name: Name
    goal: str | None = Field(default=None, max_length=500)
    start_date: date | None = None
    next_review_date: date | None = None
    notes: str | None = Field(default=None, max_length=4000)
    frequency_per_week: int | None = Field(default=None, ge=1, le=7, strict=True)
    days: list[DayInput] = Field(default_factory=list, max_length=30)

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
    workout_id: UUID
    version_number: int
    edit_revision: int
    name: str
    status: WorkoutStatus
    source: WorkoutSource
    approved_at: datetime | None
    created_at: datetime


class VersionResponse(VersionContent):
    id: UUID
    workout_id: UUID
    version_number: int
    edit_revision: int
    status: WorkoutStatus
    source: WorkoutSource
    created_by_user_id: UUID
    approved_by_user_id: UUID | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WorkoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    student_id: UUID
    name: str
    created_at: datetime


class StudentWorkout(VersionContent):
    version_number: int
    approved_at: datetime


class StudentWorkoutResponse(BaseModel):
    workout: StudentWorkout | None

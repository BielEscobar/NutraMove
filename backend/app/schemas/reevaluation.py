from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.reevaluation import ReevaluationCategory, ReevaluationStatus
from app.models.student import (
    ActivityLevel,
    CookingSkill,
    Goal,
    TrainingExperience,
    TrainingLocation,
)


class ReevaluationSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    weight: float = Field(gt=0, allow_inf_nan=False)
    desired_weight: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    goal: Goal
    goal_detail: str | None = Field(default=None, max_length=500)
    activity_level: ActivityLevel
    training_frequency: int = Field(ge=0, le=7, strict=True)
    available_training_days: str = Field(min_length=1, max_length=500)
    progress_perception: str = Field(min_length=1, max_length=2000)
    difficulties: str = Field(min_length=1, max_length=2000)
    observations: str = Field(min_length=1, max_length=2000)
    work_routine: str | None = Field(default=None, max_length=1000)
    wake_time: time | None = None
    sleep_time: time | None = None
    trains_currently: bool | None = None
    training_location: TrainingLocation | None = None
    available_equipment: str | None = Field(default=None, max_length=1000)
    training_experience: TrainingExperience | None = None
    training_history: str | None = Field(default=None, max_length=1000)
    training_duration_minutes: int | None = Field(default=None, ge=10, le=360, strict=True)
    preferred_training_time: str | None = Field(default=None, max_length=120)
    has_injury: bool | None = None
    injury_description: str | None = Field(default=None, max_length=2000)
    physical_limitations: str | None = Field(default=None, max_length=2000)
    medical_restrictions: str | None = Field(default=None, max_length=2000)
    meal_count: int | None = Field(default=None, ge=1, le=12, strict=True)
    meal_schedule: str | None = Field(default=None, max_length=1000)
    cooking_skill: CookingSkill | None = None
    food_preferences: str | None = Field(default=None, max_length=1000)
    disliked_foods: str | None = Field(default=None, max_length=1000)
    food_restrictions: str | None = Field(default=None, max_length=1000)
    food_allergies: str | None = Field(default=None, max_length=1000)
    weekly_food_budget: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    food_notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def conditions(self) -> "ReevaluationSnapshot":
        if self.goal == Goal.OTHER and not self.goal_detail:
            raise ValueError("Describe the other goal.")
        if self.has_injury and not self.injury_description:
            raise ValueError("Describe the injury.")
        return self


class ReevaluationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    category: ReevaluationCategory
    reason: str = Field(min_length=10, max_length=2000)
    snapshot: ReevaluationSnapshot | None = None


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
    snapshot: ReevaluationSnapshot | None
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

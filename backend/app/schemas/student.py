from datetime import date, datetime, time
from typing import Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

from app.models.student import (
    ActivityLevel,
    CookingSkill,
    Goal,
    Sex,
    StudentStatus,
    TrainingExperience,
    TrainingLocation,
)


class StudentProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, from_attributes=True)
    birth_date: date
    sex: Sex | None = None
    phone: str | None = Field(default=None, max_length=40)
    weight: float = Field(gt=0, allow_inf_nan=False)
    height: float = Field(gt=0, allow_inf_nan=False)
    desired_weight: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    goal: Goal
    goal_detail: str | None = Field(default=None, max_length=500)
    activity_level: ActivityLevel
    training_experience: TrainingExperience
    training_frequency: int = Field(ge=0, le=7, strict=True)
    preferred_training_time: str | None = Field(default=None, max_length=120)
    wake_time: time | None = None
    sleep_time: time | None = None
    trains_currently: bool | None = None
    training_history: str | None = Field(default=None, max_length=1000)
    training_location: TrainingLocation | None = None
    available_equipment: str | None = Field(default=None, max_length=1000)
    available_training_days: str | None = Field(default=None, max_length=500)
    training_duration_minutes: int | None = Field(default=None, ge=10, le=360, strict=True)
    work_routine: str | None = Field(default=None, max_length=1000)
    meal_schedule: str | None = Field(default=None, max_length=1000)
    meal_count: int | None = Field(default=None, ge=1, le=12, strict=True)
    cooking_skill: CookingSkill | None = None
    approximate_water_intake: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    food_preferences: str | None = Field(default=None, max_length=1000)
    disliked_foods: str | None = Field(default=None, max_length=1000)
    food_restrictions: str | None = Field(default=None, max_length=1000)
    food_allergies: str | None = Field(default=None, max_length=1000)
    weekly_food_budget: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    food_notes: str | None = Field(default=None, max_length=2000)
    has_injury: bool | None = None
    injury_description: str | None = Field(default=None, max_length=2000)
    physical_limitations: str | None = Field(default=None, max_length=2000)
    medical_restrictions: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("birth_date")
    @classmethod
    def past_birth_date(cls, value: date) -> date:
        if value >= date.today():
            raise ValueError("Birth date must be in the past.")
        return value

    @field_validator(
        "phone",
        "goal_detail",
        "preferred_training_time",
        "training_history",
        "training_location",
        "available_equipment",
        "available_training_days",
        "work_routine",
        "meal_schedule",
        "food_preferences",
        "disliked_foods",
        "food_restrictions",
        "food_allergies",
        "food_notes",
        "injury_description",
        "physical_limitations",
        "medical_restrictions",
        "notes",
        mode="before",
    )
    @classmethod
    def optional_text(cls, value: object) -> object | None:
        return value or None

    @model_validator(mode="after")
    def conditional_fields(self) -> Self:
        if self.goal == Goal.OTHER and not self.goal_detail:
            raise ValueError("Describe the other goal.")
        if self.goal != Goal.OTHER and self.goal_detail is not None:
            raise ValueError("Goal detail is only used for OTHER.")
        if self.has_injury and not self.injury_description:
            raise ValueError("Describe the injury when has_injury is true.")
        if not self.has_injury:
            self.injury_description = None
        return self


class StudentCreate(StudentProfile):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: SecretStr = Field(min_length=12, max_length=128)
    password_confirmation: SecretStr = Field(min_length=12, max_length=128)
    professional_id: UUID | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()

    @model_validator(mode="after")
    def matching_passwords(self) -> Self:
        if self.password.get_secret_value() != self.password_confirmation.get_secret_value():
            raise ValueError("Passwords must match.")
        return self


class StudentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    birth_date: date | None = None
    sex: Sex | None = None
    phone: str | None = Field(default=None, max_length=40)
    weight: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    height: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    desired_weight: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    goal: Goal | None = None
    goal_detail: str | None = Field(default=None, max_length=500)
    activity_level: ActivityLevel | None = None
    training_experience: TrainingExperience | None = None
    training_frequency: int | None = Field(default=None, ge=0, le=7, strict=True)
    preferred_training_time: str | None = Field(default=None, max_length=120)
    wake_time: time | None = None
    sleep_time: time | None = None
    trains_currently: bool | None = None
    training_history: str | None = Field(default=None, max_length=1000)
    training_location: TrainingLocation | None = None
    available_equipment: str | None = Field(default=None, max_length=1000)
    available_training_days: str | None = Field(default=None, max_length=500)
    training_duration_minutes: int | None = Field(default=None, ge=10, le=360, strict=True)
    work_routine: str | None = Field(default=None, max_length=1000)
    meal_schedule: str | None = Field(default=None, max_length=1000)
    meal_count: int | None = Field(default=None, ge=1, le=12, strict=True)
    cooking_skill: CookingSkill | None = None
    approximate_water_intake: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    food_preferences: str | None = Field(default=None, max_length=1000)
    disliked_foods: str | None = Field(default=None, max_length=1000)
    food_restrictions: str | None = Field(default=None, max_length=1000)
    food_allergies: str | None = Field(default=None, max_length=1000)
    weekly_food_budget: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    food_notes: str | None = Field(default=None, max_length=2000)
    has_injury: bool | None = None
    injury_description: str | None = Field(default=None, max_length=2000)
    physical_limitations: str | None = Field(default=None, max_length=2000)
    medical_restrictions: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)
    water_goal: float | None = Field(default=None, ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def nonempty(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Provide at least one field.")
        return self


class StudentBrief(BaseModel):
    id: UUID
    name: str
    email: str
    goal: Goal
    status: StudentStatus
    professional_id: UUID | None
    professional_name: str | None


class StudentResponse(StudentProfile):
    id: UUID
    name: str
    email: str
    professional_id: UUID | None
    professional_name: str | None
    status: StudentStatus
    is_active: bool
    water_goal: float | None
    created_at: datetime
    updated_at: datetime


class StudentList(BaseModel):
    items: list[StudentBrief]
    total: int
    page: int
    page_size: int


class StudentFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    q: str = Field(default="", max_length=120)
    status: StudentStatus | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class MasterStudentFilters(StudentFilters):
    professional_id: UUID | None = None
    unassigned: bool = False


class StudentRegistrationResponse(BaseModel):
    status: StudentStatus

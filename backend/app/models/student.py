# ruff: noqa: E501
from datetime import date, datetime, time
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Time,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.professional import Professional
from app.models.user import User


class StudentStatus(StrEnum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    REJECTED = "REJECTED"


class Goal(StrEnum):
    WEIGHT_LOSS = "WEIGHT_LOSS"
    MUSCLE_GAIN = "MUSCLE_GAIN"
    MAINTENANCE = "MAINTENANCE"
    FITNESS = "FITNESS"
    BODY_RECOMPOSITION = "BODY_RECOMPOSITION"
    DEFINITION = "DEFINITION"
    OTHER = "OTHER"


class ActivityLevel(StrEnum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


class TrainingExperience(StrEnum):
    NONE = "NONE"
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class Sex(StrEnum):
    FEMALE = "FEMALE"
    MALE = "MALE"
    OTHER = "OTHER"
    NOT_INFORMED = "NOT_INFORMED"


class TrainingLocation(StrEnum):
    GYM = "GYM"
    HOME = "HOME"
    CONDOMINIUM = "CONDOMINIUM"
    OTHER = "OTHER"


class CookingSkill(StrEnum):
    EASY = "EASY"
    MODERATE = "MODERATE"
    ADVANCED = "ADVANCED"


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        CheckConstraint("weight > 0 AND weight < 'Infinity'::float8", name="ck_students_weight"),
        CheckConstraint("height > 0 AND height < 'Infinity'::float8", name="ck_students_height"),
        CheckConstraint("training_frequency BETWEEN 0 AND 7", name="ck_students_frequency"),
        CheckConstraint(
            "desired_weight IS NULL OR (desired_weight > 0 AND desired_weight < 'Infinity'::float8)",
            name="ck_students_desired_weight",
        ),
        CheckConstraint(
            "meal_count IS NULL OR meal_count BETWEEN 1 AND 12", name="ck_students_meal_count"
        ),
        CheckConstraint(
            "training_duration_minutes IS NULL OR training_duration_minutes BETWEEN 10 AND 360",
            name="ck_students_training_duration",
        ),
        CheckConstraint(
            "(has_injury IS NOT TRUE) OR (injury_description IS NOT NULL AND "
            "length(trim(injury_description)) > 0)",
            name="ck_students_injury_description",
        ),
        CheckConstraint(
            "water_goal IS NULL OR (water_goal >= 0 AND water_goal < 'Infinity'::float8)",
            name="ck_students_water_goal",
        ),
        CheckConstraint(
            "approximate_water_intake IS NULL OR (approximate_water_intake >= 0 "
            "AND approximate_water_intake < 'Infinity'::float8)",
            name="ck_students_water_intake",
        ),
        CheckConstraint(
            "(goal = 'OTHER' AND goal_detail IS NOT NULL AND length(trim(goal_detail)) > 0) "
            "OR (goal <> 'OTHER' AND goal_detail IS NULL)",
            name="ck_students_goal_detail",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), unique=True)
    professional_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("professionals.id", ondelete="RESTRICT"), index=True
    )
    birth_date: Mapped[date] = mapped_column(Date)
    sex: Mapped[Sex | None] = mapped_column(
        Enum(Sex, name="student_sex", native_enum=False, create_constraint=True)
    )
    phone: Mapped[str | None] = mapped_column(String(40))
    weight: Mapped[float] = mapped_column(Float)
    height: Mapped[float] = mapped_column(Float)
    desired_weight: Mapped[float | None] = mapped_column(Float)
    goal: Mapped[Goal] = mapped_column(
        Enum(Goal, name="student_goal", native_enum=False, create_constraint=True)
    )
    goal_detail: Mapped[str | None] = mapped_column(String(500))
    activity_level: Mapped[ActivityLevel] = mapped_column(
        Enum(
            ActivityLevel, name="student_activity_level", native_enum=False, create_constraint=True
        )
    )
    training_experience: Mapped[TrainingExperience] = mapped_column(
        Enum(
            TrainingExperience,
            name="student_training_experience",
            native_enum=False,
            create_constraint=True,
        )
    )
    training_frequency: Mapped[int] = mapped_column(Integer)
    preferred_training_time: Mapped[str | None] = mapped_column(String(120))
    wake_time: Mapped[time | None] = mapped_column(Time)
    sleep_time: Mapped[time | None] = mapped_column(Time)
    trains_currently: Mapped[bool | None] = mapped_column(Boolean)
    training_history: Mapped[str | None] = mapped_column(String(1000))
    training_location: Mapped[TrainingLocation | None] = mapped_column(
        Enum(
            TrainingLocation,
            name="student_training_location",
            native_enum=False,
            create_constraint=True,
        )
    )
    available_equipment: Mapped[str | None] = mapped_column(String(1000))
    available_training_days: Mapped[str | None] = mapped_column(String(500))
    training_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    work_routine: Mapped[str | None] = mapped_column(String(1000))
    meal_schedule: Mapped[str | None] = mapped_column(String(1000))
    meal_count: Mapped[int | None] = mapped_column(Integer)
    cooking_skill: Mapped[CookingSkill | None] = mapped_column(
        Enum(CookingSkill, name="student_cooking_skill", native_enum=False, create_constraint=True)
    )
    approximate_water_intake: Mapped[float | None] = mapped_column(Float)
    food_preferences: Mapped[str | None] = mapped_column(String(1000))
    disliked_foods: Mapped[str | None] = mapped_column(String(1000))
    food_restrictions: Mapped[str | None] = mapped_column(String(1000))
    food_allergies: Mapped[str | None] = mapped_column(String(1000))
    weekly_food_budget: Mapped[float | None] = mapped_column(Float)
    food_notes: Mapped[str | None] = mapped_column(String(2000))
    has_injury: Mapped[bool | None] = mapped_column(Boolean)
    injury_description: Mapped[str | None] = mapped_column(String(2000))
    physical_limitations: Mapped[str | None] = mapped_column(String(2000))
    medical_restrictions: Mapped[str | None] = mapped_column(String(2000))
    notes: Mapped[str | None] = mapped_column(String(2000))
    water_goal: Mapped[float | None] = mapped_column(Float)
    status: Mapped[StudentStatus] = mapped_column(
        Enum(StudentStatus, name="student_status", native_enum=False, create_constraint=True)
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    user: Mapped[User] = relationship()
    professional: Mapped[Professional | None] = relationship()

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
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


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        CheckConstraint("weight > 0 AND weight < 'Infinity'::float8", name="ck_students_weight"),
        CheckConstraint("height > 0 AND height < 'Infinity'::float8", name="ck_students_height"),
        CheckConstraint("training_frequency BETWEEN 0 AND 7", name="ck_students_frequency"),
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
    phone: Mapped[str | None] = mapped_column(String(40))
    weight: Mapped[float] = mapped_column(Float)
    height: Mapped[float] = mapped_column(Float)
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
    work_routine: Mapped[str | None] = mapped_column(String(1000))
    meal_schedule: Mapped[str | None] = mapped_column(String(1000))
    approximate_water_intake: Mapped[float | None] = mapped_column(Float)
    food_preferences: Mapped[str | None] = mapped_column(String(1000))
    food_restrictions: Mapped[str | None] = mapped_column(String(1000))
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

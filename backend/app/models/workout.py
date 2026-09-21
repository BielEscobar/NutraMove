from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WorkoutStatus(StrEnum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    ARCHIVED = "ARCHIVED"


class WorkoutSource(StrEnum):
    MANUAL = "MANUAL"
    AI_GENERATED = "AI_GENERATED"


class Workout(Base):
    __tablename__ = "workouts"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(
        ForeignKey("students.id", ondelete="RESTRICT"), index=True
    )
    professional_id: Mapped[UUID] = mapped_column(
        ForeignKey("professionals.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WorkoutVersion(Base):
    __tablename__ = "workout_versions"
    __table_args__ = (
        CheckConstraint("frequency_per_week BETWEEN 1 AND 7", name="ck_workout_frequency"),
        UniqueConstraint("workout_id", "version_number", name="uq_workout_version_number"),
        CheckConstraint(
            "version_number > 0 AND edit_revision > 0", name="ck_workout_version_numbers"
        ),
        CheckConstraint(
            "next_review_date IS NULL OR start_date IS NULL OR next_review_date >= start_date",
            name="ck_workout_version_dates",
        ),
        CheckConstraint(
            "(approved_by_user_id IS NULL) = (approved_at IS NULL)", name="ck_workout_approval_pair"
        ),
        CheckConstraint(
            "status <> 'APPROVED' OR approved_at IS NOT NULL", name="ck_workout_approval_required"
        ),
        CheckConstraint(
            "status NOT IN ('DRAFT', 'PENDING_REVIEW') OR approved_at IS NULL",
            name="ck_workout_draft_approval",
        ),
        Index(
            "uq_workout_approved",
            "workout_id",
            unique=True,
            postgresql_where=text("status = 'APPROVED'"),
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workout_id: Mapped[UUID] = mapped_column(
        ForeignKey("workouts.id", ondelete="RESTRICT"), index=True
    )
    version_number: Mapped[int]
    edit_revision: Mapped[int] = mapped_column(default=1, server_default="1")
    name: Mapped[str] = mapped_column(String(160))
    goal: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[WorkoutStatus] = mapped_column(
        Enum(WorkoutStatus, name="workout_status", native_enum=False, create_constraint=True)
    )
    source: Mapped[WorkoutSource] = mapped_column(
        Enum(WorkoutSource, name="workout_source", native_enum=False, create_constraint=True)
    )
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    start_date: Mapped[date | None]
    next_review_date: Mapped[date | None]
    notes: Mapped[str | None] = mapped_column(String(4000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    frequency_per_week: Mapped[int | None]
    days: Mapped[list[WorkoutDay]] = relationship(
        cascade="all, delete-orphan", order_by="WorkoutDay.position"
    )


class WorkoutDay(Base):
    __tablename__ = "workout_days"
    __table_args__ = (
        UniqueConstraint("workout_version_id", "position"),
        CheckConstraint("position >= 0", name="ck_workout_day_position"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workout_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("workout_versions.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(String(2000))
    is_rest: Mapped[bool] = mapped_column(default=False, server_default="false")
    position: Mapped[int]
    exercises: Mapped[list[WorkoutExercise]] = relationship(
        cascade="all, delete-orphan", order_by="WorkoutExercise.position"
    )


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"
    __table_args__ = (
        UniqueConstraint("workout_day_id", "position"),
        CheckConstraint("position >= 0", name="ck_workout_exercise_position"),
        CheckConstraint("sets BETWEEN 1 AND 100", name="ck_workout_exercise_sets"),
        CheckConstraint("rest_seconds BETWEEN 0 AND 86400", name="ck_workout_exercise_rest"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workout_day_id: Mapped[UUID] = mapped_column(
        ForeignKey("workout_days.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    muscle_group: Mapped[str | None] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(String(2000))
    instructions: Mapped[str | None] = mapped_column(String(2000))
    sets: Mapped[int | None]
    repetitions: Mapped[str | None] = mapped_column(String(160))
    load: Mapped[str | None] = mapped_column(String(160))
    duration: Mapped[str | None] = mapped_column(String(160))
    rest_seconds: Mapped[int | None]
    notes: Mapped[str | None] = mapped_column(String(2000))
    position: Mapped[int]

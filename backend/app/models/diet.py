from __future__ import annotations

from datetime import date, datetime
from datetime import time as TimeValue
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DietStatus(StrEnum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    ARCHIVED = "ARCHIVED"


class DietSource(StrEnum):
    MANUAL = "MANUAL"
    AI_GENERATED = "AI_GENERATED"


class Diet(Base):
    __tablename__ = "diets"
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


class DietVersion(Base):
    __tablename__ = "diet_versions"
    __table_args__ = (
        UniqueConstraint("diet_id", "version_number", name="uq_diet_version_number"),
        CheckConstraint("version_number > 0 AND edit_revision > 0", name="ck_diet_version_numbers"),
        CheckConstraint(
            "next_review_date IS NULL OR start_date IS NULL OR next_review_date >= start_date",
            name="ck_diet_version_dates",
        ),
        CheckConstraint(
            "(approved_by_user_id IS NULL) = (approved_at IS NULL)", name="ck_diet_approval_pair"
        ),
        CheckConstraint(
            "status <> 'APPROVED' OR approved_at IS NOT NULL", name="ck_diet_approval_required"
        ),
        CheckConstraint(
            "status NOT IN ('DRAFT', 'PENDING_REVIEW') OR approved_at IS NULL",
            name="ck_diet_draft_approval",
        ),
        Index(
            "uq_diet_approved", "diet_id", unique=True, postgresql_where=text("status = 'APPROVED'")
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    diet_id: Mapped[UUID] = mapped_column(ForeignKey("diets.id", ondelete="RESTRICT"), index=True)
    version_number: Mapped[int]
    edit_revision: Mapped[int] = mapped_column(default=1, server_default="1")
    name: Mapped[str] = mapped_column(String(160))
    goal: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[DietStatus] = mapped_column(
        Enum(DietStatus, name="diet_status", native_enum=False, create_constraint=True)
    )
    source: Mapped[DietSource] = mapped_column(
        Enum(DietSource, name="diet_source", native_enum=False, create_constraint=True)
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
    meals: Mapped[list[Meal]] = relationship(cascade="all, delete-orphan", order_by="Meal.position")


class Meal(Base):
    __tablename__ = "diet_meals"
    __table_args__ = (
        UniqueConstraint("diet_version_id", "position"),
        CheckConstraint("position >= 0", name="ck_meal_position"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    diet_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("diet_versions.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    time: Mapped[TimeValue | None]
    position: Mapped[int]
    foods: Mapped[list[Food]] = relationship(cascade="all, delete-orphan", order_by="Food.position")


class Food(Base):
    __tablename__ = "diet_foods"
    __table_args__ = (
        UniqueConstraint("meal_id", "position"),
        CheckConstraint("position >= 0", name="ck_food_position"),
        CheckConstraint("quantity > 0 AND quantity < 'Infinity'::numeric", name="ck_food_quantity"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    meal_id: Mapped[UUID] = mapped_column(
        ForeignKey("diet_meals.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    unit: Mapped[str] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(String(1000))
    position: Mapped[int]
    substitutions: Mapped[list[FoodSubstitution]] = relationship(
        cascade="all, delete-orphan", order_by="FoodSubstitution.position"
    )


class FoodSubstitution(Base):
    __tablename__ = "diet_food_substitutions"
    __table_args__ = (
        UniqueConstraint("food_id", "position"),
        CheckConstraint("position >= 0", name="ck_substitution_position"),
        CheckConstraint(
            "quantity IS NULL OR (quantity > 0 AND quantity < 'Infinity'::numeric)",
            name="ck_substitution_quantity",
        ),
        CheckConstraint("(quantity IS NULL) = (unit IS NULL)", name="ck_substitution_unit"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    food_id: Mapped[UUID] = mapped_column(
        ForeignKey("diet_foods.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    unit: Mapped[str | None] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(String(1000))
    position: Mapped[int]

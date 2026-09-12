from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MeasurementType(StrEnum):
    ARM = "ARM"
    CHEST = "CHEST"
    WAIST = "WAIST"
    ABDOMEN = "ABDOMEN"
    HIP = "HIP"
    THIGH = "THIGH"
    CALF = "CALF"


class MeasurementSide(StrEnum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class Assessment(Base):
    __tablename__ = "assessments"
    __table_args__ = (
        CheckConstraint(
            "weight_kg IS NULL OR (weight_kg > 0 AND weight_kg < 'Infinity'::float8)",
            name="ck_assessment_weight",
        ),
        CheckConstraint(
            "height_cm IS NULL OR (height_cm > 0 AND height_cm < 'Infinity'::float8)",
            name="ck_assessment_height",
        ),
        CheckConstraint("edit_revision > 0", name="ck_assessment_revision"),
        Index("ix_assessment_student_date", "student_id", "assessment_date", "created_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id", ondelete="RESTRICT"))
    professional_id: Mapped[UUID] = mapped_column(
        ForeignKey("professionals.id", ondelete="RESTRICT"), index=True
    )
    assessment_date: Mapped[date]
    weight_kg: Mapped[float | None]
    height_cm: Mapped[float | None]
    notes: Mapped[str | None] = mapped_column(String(4000))
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    updated_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    edit_revision: Mapped[int] = mapped_column(default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    measurements: Mapped[list["Measurement"]] = relationship(
        cascade="all, delete-orphan", order_by="(Measurement.measurement_type, Measurement.side)"
    )


class Measurement(Base):
    __tablename__ = "measurements"
    __table_args__ = (
        CheckConstraint(
            "value_cm > 0 AND value_cm < 'Infinity'::float8", name="ck_measurement_value"
        ),
        CheckConstraint(
            "side IS NULL OR measurement_type IN ('ARM','THIGH','CALF')", name="ck_measurement_side"
        ),
        Index(
            "uq_measurement_kind",
            "assessment_id",
            "measurement_type",
            "side",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), index=True
    )
    measurement_type: Mapped[MeasurementType] = mapped_column(
        Enum(MeasurementType, name="measurement_type", native_enum=False, create_constraint=True)
    )
    side: Mapped[MeasurementSide | None] = mapped_column(
        Enum(MeasurementSide, name="measurement_side", native_enum=False, create_constraint=True)
    )
    value_cm: Mapped[float]
    notes: Mapped[str | None] = mapped_column(String(1000))

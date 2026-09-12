from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WaterRecord(Base):
    __tablename__ = "water_records"
    __table_args__ = (
        CheckConstraint("amount_ml BETWEEN 1 AND 10000", name="ck_water_amount"),
        Index("ix_water_student_consumed", "student_id", "consumed_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id", ondelete="RESTRICT"))
    amount_ml: Mapped[int]
    consumed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

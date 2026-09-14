from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RateLimitWindow(Base):
    __tablename__ = "rate_limit_windows"
    __table_args__ = (
        CheckConstraint("attempts > 0", name="ck_rate_limit_attempts"),
        Index("ix_rate_limit_updated", "updated_at"),
    )

    key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

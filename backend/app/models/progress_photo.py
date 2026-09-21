from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PhotoPosition(StrEnum):
    FRONT = "FRONT"
    SIDE = "SIDE"


class PhotoSetSource(StrEnum):
    INITIAL = "INITIAL"
    REEVALUATION = "REEVALUATION"


class ProgressPhotoSet(Base):
    __tablename__ = "progress_photo_sets"
    __table_args__ = (Index("ix_photo_sets_student_created", "student_id", "created_at"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id", ondelete="RESTRICT"))
    reevaluation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("reevaluation_requests.id", ondelete="RESTRICT"), unique=True
    )
    source: Mapped[PhotoSetSource] = mapped_column(
        Enum(PhotoSetSource, name="photo_set_source", native_enum=False, create_constraint=True)
    )
    context: Mapped[str | None] = mapped_column(String(500))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    photos: Mapped[list["ProgressPhoto"]] = relationship(
        back_populates="photo_set", cascade="all, delete-orphan", lazy="selectin"
    )


class ProgressPhoto(Base):
    __tablename__ = "progress_photos"
    __table_args__ = (UniqueConstraint("photo_set_id", "position", name="uq_photo_set_position"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    photo_set_id: Mapped[UUID] = mapped_column(
        ForeignKey("progress_photo_sets.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[PhotoPosition] = mapped_column(
        Enum(PhotoPosition, name="photo_position", native_enum=False, create_constraint=True)
    )
    storage_key: Mapped[str] = mapped_column(String(120), unique=True)
    mime_type: Mapped[str] = mapped_column(String(40))
    byte_size: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    photo_set: Mapped[ProgressPhotoSet] = relationship(back_populates="photos")

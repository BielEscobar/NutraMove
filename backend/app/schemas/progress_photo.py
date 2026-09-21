from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.progress_photo import PhotoPosition, PhotoSetSource


class ProgressPhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    position: PhotoPosition
    mime_type: str
    byte_size: int


class ProgressPhotoSetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source: PhotoSetSource
    context: str | None
    captured_at: datetime
    photos: list[ProgressPhotoResponse]

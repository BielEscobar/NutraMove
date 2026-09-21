from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.api.dependencies import AppSettings, CurrentUser, DbSession, require_roles
from app.api.professionals import no_cache
from app.models import UserRole
from app.models.progress_photo import ProgressPhotoSet
from app.schemas.progress_photo import ProgressPhotoSetResponse
from app.services import progress_photos

student_router = APIRouter(
    prefix="/student/progress-photos",
    tags=["progress photos"],
    dependencies=[Depends(require_roles(UserRole.STUDENT)), Depends(no_cache)],
)
professional_router = APIRouter(
    prefix="/professional/students/{student_id}/progress-photos",
    tags=["progress photos"],
    dependencies=[Depends(require_roles(UserRole.PROFESSIONAL)), Depends(no_cache)],
)


def response(items: Sequence[ProgressPhotoSet]) -> list[ProgressPhotoSetResponse]:
    return [ProgressPhotoSetResponse.model_validate(item) for item in items]


@student_router.get("")
def own_sets(db: DbSession, actor: CurrentUser) -> list[ProgressPhotoSetResponse]:
    return response(progress_photos.sets_for(db, actor))


@professional_router.get("")
def student_sets(
    student_id: UUID, db: DbSession, actor: CurrentUser
) -> list[ProgressPhotoSetResponse]:
    return response(progress_photos.sets_for(db, actor, student_id))


@student_router.get("/{photo_id}/content", response_class=FileResponse)
def own_content(
    photo_id: UUID, db: DbSession, actor: CurrentUser, settings: AppSettings
) -> FileResponse:
    selected_photo = progress_photos.photo_for(db, actor, photo_id)
    return FileResponse(
        progress_photos.path_for(selected_photo, settings),
        media_type=selected_photo.mime_type,
        headers={"Content-Disposition": "inline"},
    )


@professional_router.get("/{photo_id}/content", response_class=FileResponse)
def student_content(
    student_id: UUID, photo_id: UUID, db: DbSession, actor: CurrentUser, settings: AppSettings
) -> FileResponse:
    allowed = {
        photo.id
        for photo_set in progress_photos.sets_for(db, actor, student_id)
        for photo in photo_set.photos
    }
    if photo_id not in allowed:
        from fastapi import HTTPException

        raise HTTPException(404, "Foto não encontrada.")
    selected_photo = progress_photos.photo_for(db, actor, photo_id)
    return FileResponse(
        progress_photos.path_for(selected_photo, settings),
        media_type=selected_photo.mime_type,
        headers={"Content-Disposition": "inline"},
    )

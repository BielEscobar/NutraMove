from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.models import Student, User
from app.models.progress_photo import PhotoPosition, PhotoSetSource, ProgressPhoto, ProgressPhotoSet
from app.repositories.students import scoped_query

_ALLOWED = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/webp": (b"RIFF",),
}
_EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def _validate(data: bytes, upload: UploadFile, settings: Settings) -> str:
    mime = upload.content_type or ""
    if mime not in _ALLOWED or not data or len(data) > settings.max_photo_bytes:
        raise HTTPException(422, "Foto inválida. Use JPEG, PNG ou WebP dentro do limite permitido.")
    if mime == "image/webp":
        valid = data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    else:
        valid = any(data.startswith(signature) for signature in _ALLOWED[mime])
    suffix = Path(upload.filename or "").suffix.lower()
    allowed_suffixes = {".jpg", ".jpeg"} if mime == "image/jpeg" else {_EXTENSIONS[mime]}
    if not valid or suffix not in allowed_suffixes:
        raise HTTPException(422, "O conteúdo da foto não corresponde ao formato informado.")
    return mime


async def prepare(upload: UploadFile, settings: Settings) -> tuple[bytes, str]:
    data = await upload.read(settings.max_photo_bytes + 1)
    return data, _validate(data, upload, settings)


def add_set(
    db: Session,
    settings: Settings,
    student_id: UUID,
    source: PhotoSetSource,
    front: tuple[bytes, str],
    side: tuple[bytes, str],
    *,
    reevaluation_id: UUID | None = None,
    context: str | None = None,
) -> tuple[ProgressPhotoSet, list[Path]]:
    record = ProgressPhotoSet(
        student_id=student_id,
        reevaluation_id=reevaluation_id,
        source=source,
        context=context,
        captured_at=datetime.now(UTC),
    )
    written: list[Path] = []
    root = settings.private_upload_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    try:
        for position, prepared in ((PhotoPosition.FRONT, front), (PhotoPosition.SIDE, side)):
            data, mime = prepared
            key = f"{uuid4().hex}{_EXTENSIONS[mime]}"
            path = (root / key).resolve()
            if path.parent != root:
                raise HTTPException(500, "Falha ao preparar armazenamento privado.")
            written.append(path)
            path.write_bytes(data)
            record.photos.append(
                ProgressPhoto(
                    position=position, storage_key=key, mime_type=mime, byte_size=len(data)
                )
            )
        db.add(record)
        db.flush()
    except Exception:
        cleanup(written)
        raise
    return record, written


def cleanup(paths: list[Path]) -> None:
    for path in paths:
        path.unlink(missing_ok=True)


def sets_for(db: Session, actor: User, student_id: UUID | None = None) -> list[ProgressPhotoSet]:
    scoped = scoped_query(db, actor)
    if student_id is not None:
        from app.services.students import get as get_student

        get_student(db, actor, student_id)
        scoped = scoped.where(Student.id == student_id)
    query = (
        select(ProgressPhotoSet)
        .where(ProgressPhotoSet.student_id.in_(scoped.with_only_columns(Student.id)))
        .options(selectinload(ProgressPhotoSet.photos))
        .order_by(ProgressPhotoSet.captured_at.desc(), ProgressPhotoSet.id.desc())
    )
    return list(db.scalars(query))


def photo_for(db: Session, actor: User, photo_id: UUID) -> ProgressPhoto:
    scoped = scoped_query(db, actor).with_only_columns(Student.id)
    photo = db.scalar(
        select(ProgressPhoto)
        .join(ProgressPhotoSet)
        .where(ProgressPhoto.id == photo_id, ProgressPhotoSet.student_id.in_(scoped))
    )
    if photo is None:
        raise HTTPException(404, "Foto não encontrada.")
    return photo


def path_for(photo: ProgressPhoto, settings: Settings) -> Path:
    root = settings.private_upload_dir.resolve()
    path = (root / photo.storage_key).resolve()
    if path.parent != root or not path.is_file():
        raise HTTPException(404, "Foto não encontrada.")
    return path

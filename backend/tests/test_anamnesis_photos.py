from datetime import date
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.prompts import PROMPT_VERSION, prompt_for
from app.core.config import get_settings
from app.models import Student, User
from app.models.progress_photo import PhotoSetSource, ProgressPhoto, ProgressPhotoSet
from app.schemas.student import StudentProfile
from app.services import progress_photos
from tests.conftest import PASSWORD
from tests.test_assessments import Family
from tests.test_assessments import family as family_fixture
from tests.test_assessments import login as login_user

family = family_fixture


def profile(**changes: object) -> dict[str, object]:
    return {
        "birth_date": date(2000, 1, 1),
        "weight": 70,
        "height": 170,
        "goal": "FITNESS",
        "activity_level": "MODERATE",
        "training_experience": "BEGINNER",
        "training_frequency": 3,
    } | changes


def test_expanded_anamnesis_and_conditional_validation() -> None:
    parsed = StudentProfile.model_validate(
        profile(
            sex="FEMALE",
            desired_weight=65,
            wake_time="06:30",
            sleep_time="22:30",
            training_location="GYM",
            available_equipment="halteres",
            available_training_days="segunda, quarta e sexta",
            meal_count=4,
            cooking_skill="EASY",
            food_allergies="nenhuma",
            has_injury=False,
        )
    )
    assert parsed.meal_count == 4
    assert parsed.injury_description is None
    with pytest.raises(ValidationError):
        StudentProfile.model_validate(profile(has_injury=True))
    with pytest.raises(ValidationError):
        StudentProfile.model_validate(profile(goal="OTHER"))


def test_prompt_v2_keeps_assistive_safety_and_methodology() -> None:
    assert PROMPT_VERSION == "v2"
    diet = prompt_for("diet")
    workout = prompt_for("workout")
    assert "publicada automaticamente" in diet
    assert "exatamente" in diet and "op" in diet
    assert "seis dias" in workout
    assert "diagnostique" in workout


ORIGIN = {"Origin": "http://localhost:3000"}
JPEG = b"\xff\xd8\xff" + b"synthetic-image"


def registration(email: str) -> dict[str, object]:
    return {
        "name": "Synthetic Student",
        "email": email,
        "password": PASSWORD,
        "password_confirmation": PASSWORD,
        "birth_date": "2000-01-01",
        "weight": 70,
        "height": 170,
        "goal": "FITNESS",
        "activity_level": "MODERATE",
        "training_experience": "BEGINNER",
        "training_frequency": 3,
        "has_injury": False,
        "food_allergies": "nenhuma",
        "food_restrictions": "nenhuma",
    }


def upload(client: TestClient, email: str, *, front: bytes = JPEG) -> Response:
    import json

    return client.post(
        "/students/register-with-photos",
        headers=ORIGIN,
        data={"data": json.dumps(registration(email))},
        files={
            "front": ("front.jpg", front, "image/jpeg"),
            "side": ("side.jpg", JPEG, "image/jpeg"),
        },
    )


def test_private_photo_registration_history_and_isolation(
    client: TestClient, db: Session, app: FastAPI, tmp_path: Path
) -> None:
    settings = app.dependency_overrides[get_settings]()
    settings.private_upload_dir = tmp_path
    assert upload(client, "photo-a@example.com").status_code == 201
    assert upload(client, "photo-b@example.com").status_code == 201
    assert db.scalar(select(func.count()).select_from(ProgressPhotoSet)) == 2
    assert db.scalar(select(func.count()).select_from(ProgressPhoto)) == 4
    users = list(db.scalars(select(User).where(User.email.like("photo-%")).order_by(User.email)))
    client.post("/auth/login", headers=ORIGIN, json={"email": users[0].email, "password": PASSWORD})
    own = client.get("/student/progress-photos")
    assert own.status_code == 200 and len(own.json()) == 1
    own_photo = own.json()[0]["photos"][0]
    assert "storage_key" not in own_photo and "path" not in own_photo and "url" not in own_photo
    content = client.get(f"/student/progress-photos/{own_photo['id']}/content")
    assert content.status_code == 200 and content.content == JPEG
    other_photo = db.scalar(
        select(ProgressPhoto)
        .join(ProgressPhotoSet)
        .join(Student)
        .where(Student.user_id == users[1].id)
    )
    assert other_photo is not None
    assert client.get(f"/student/progress-photos/{other_photo.id}/content").status_code == 404


def test_malformed_photo_is_rejected_atomically(
    client: TestClient, db: Session, app: FastAPI, tmp_path: Path
) -> None:
    app.dependency_overrides[get_settings]().private_upload_dir = tmp_path
    result = upload(client, "bad-photo@example.com", front=b"not-an-image")
    assert result.status_code == 422
    assert db.scalar(select(User).where(User.email == "bad-photo@example.com")) is None
    assert list(tmp_path.iterdir()) == []


def test_invalid_side_after_valid_front_is_rejected_atomically(
    client: TestClient, db: Session, app: FastAPI, tmp_path: Path
) -> None:
    app.dependency_overrides[get_settings]().private_upload_dir = tmp_path
    import json

    result = client.post(
        "/students/register-with-photos",
        headers=ORIGIN,
        data={"data": json.dumps(registration("bad-side@example.com"))},
        files={
            "front": ("front.jpg", JPEG, "image/jpeg"),
            "side": ("side.jpg", b"not-an-image", "image/jpeg"),
        },
    )
    assert result.status_code == 422
    assert db.scalar(select(User).where(User.email == "bad-side@example.com")) is None
    assert list(tmp_path.iterdir()) == []


def test_second_file_write_failure_cleans_first_file(
    db: Session, app: FastAPI, tmp_path: Path, family: Family, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = app.dependency_overrides[get_settings]()
    settings.private_upload_dir = tmp_path
    original_write = Path.write_bytes
    writes = 0

    def fail_second(path: Path, data: bytes) -> int:
        nonlocal writes
        writes += 1
        if writes == 2:
            raise OSError("synthetic disk failure")
        return original_write(path, data)

    monkeypatch.setattr(Path, "write_bytes", fail_second)
    with pytest.raises(OSError, match="synthetic disk failure"):
        progress_photos.add_set(
            db,
            settings,
            family.student_a.id,
            source=PhotoSetSource.INITIAL,
            front=(JPEG, "image/jpeg"),
            side=(JPEG, "image/jpeg"),
        )
    db.rollback()
    assert list(tmp_path.iterdir()) == []
    assert db.scalar(select(func.count()).select_from(ProgressPhotoSet)) == 0


def test_photo_access_follows_portfolio_transfer(
    client: TestClient, db: Session, app: FastAPI, tmp_path: Path, family: Family
) -> None:
    settings = app.dependency_overrides[get_settings]()
    settings.private_upload_dir = tmp_path
    photo_set, _ = progress_photos.add_set(
        db,
        settings,
        family.student_a.id,
        source=PhotoSetSource.INITIAL,
        front=(JPEG, "image/jpeg"),
        side=(JPEG, "image/jpeg"),
    )
    db.commit()
    photo_id = photo_set.photos[0].id
    list_path = f"/professional/students/{family.student_a.id}/progress-photos"
    content_path = f"{list_path}/{photo_id}/content"

    login_user(client, family.a.user)
    assert client.get(list_path).status_code == 200
    assert client.get(content_path).status_code == 200
    login_user(client, family.b.user)
    assert client.get(list_path).status_code == 404
    assert client.get(content_path).status_code == 404

    login_user(client, family.master)
    moved = client.post(
        f"/master/students/{family.student_a.id}/transfer",
        headers=ORIGIN,
        json={
            "expected_professional_id": str(family.a.id),
            "new_professional_id": str(family.b.id),
            "reason": "Teste sintético de autorização de fotos",
        },
    )
    assert moved.status_code == 200, moved.text
    login_user(client, family.a.user)
    assert client.get(list_path).status_code == 404
    assert client.get(content_path).status_code == 404
    login_user(client, family.b.user)
    listing = client.get(list_path)
    assert listing.status_code == 200
    assert "storage_key" not in listing.text and str(tmp_path) not in listing.text
    assert client.get(content_path).status_code == 200
    login_user(client, family.student_a.user)
    assert client.get(f"/student/progress-photos/{photo_id}/content").status_code == 200

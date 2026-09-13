from datetime import date
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.ai import get_ai_provider
from app.core.config import get_settings
from app.core.security import hash_password
from app.models import Professional, Student, StudentStatus, User, UserRole
from app.models.diet import Diet
from app.models.student import ActivityLevel, Goal, TrainingExperience
from app.models.workout import Workout

ORIGIN = {"Origin": "http://localhost:3000"}
PASSWORD = "test-only-password-2026"


class FakeProvider:
    def __init__(self) -> None:
        self.contexts: list[dict[str, Any]] = []
        self.output: object = {}
        self.fail = False

    def generate_structured(
        self, *, kind: str, context: dict[str, Any], schema: dict[str, Any]
    ) -> object:
        self.contexts.append(context)
        if self.fail:
            raise ValueError("provider failed")
        return self.output


@pytest.fixture
def setup_ai(
    db: Session, app: FastAPI
) -> tuple[Professional, Professional, Student, Student, FakeProvider]:
    settings = app.dependency_overrides[get_settings]()
    settings.ai_enabled = True
    settings.ai_api_key = SecretStr("test-only")
    fake = FakeProvider()
    app.dependency_overrides[get_ai_provider] = lambda: fake
    owners = [
        Professional(
            user=User(
                name=f"Owner {index}",
                email=f"owner{index}@example.com",
                role=UserRole.PROFESSIONAL,
                password_hash=hash_password(PASSWORD),
            )
        )
        for index in (1, 2)
    ]
    db.add_all(owners)
    db.flush()
    students = [
        Student(
            user=User(
                name=f"Student {index}",
                email=f"student{index}@example.com",
                role=UserRole.STUDENT,
                password_hash=hash_password(PASSWORD),
            ),
            professional_id=owner.id,
            status=StudentStatus.ACTIVE,
            birth_date=date(1990, 1, 1),
            weight=70,
            height=175,
            goal=Goal.FITNESS,
            activity_level=ActivityLevel.MODERATE,
            training_experience=TrainingExperience.BEGINNER,
            training_frequency=3,
        )
        for index, owner in enumerate(owners, 1)
    ]
    db.add_all(students)
    db.commit()
    return owners[0], owners[1], students[0], students[1], fake


def login(client: TestClient, email: str) -> None:
    client.cookies.clear()
    response = client.post(
        "/auth/login", headers=ORIGIN, json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text


@pytest.mark.parametrize("kind", ["diet", "workout"])
def test_generation_workflow(
    client: TestClient,
    db: Session,
    setup_ai: tuple[Professional, Professional, Student, Student, FakeProvider],
    kind: str,
) -> None:
    owner, other, student, foreign, fake = setup_ai
    fake.output = (
        {
            "name": "Sugestão neutra",
            "meals": [
                {
                    "name": "Refeição",
                    "foods": [{"name": "Alimento", "quantity": "1", "unit": "porção"}],
                }
            ],
        }
        if kind == "diet"
        else {
            "name": "Sugestão neutra",
            "frequency_per_week": 1,
            "days": [{"name": "Dia A", "exercises": [{"name": "Movimento"}]}],
        }
    )
    login(client, owner.user.email)
    path = f"/professional/students/{student.id}/ai/{kind}"
    result = client.post(path, headers=ORIGIN, json={"instructions": " Revisar com calma "})
    assert result.status_code == 201, result.text
    body = result.json()
    assert body["source"] == "AI_GENERATED"
    assert body["status"] == "PENDING_REVIEW"
    assert body["version_number"] == 1
    assert fake.contexts[0]["professional_instructions"] == "Revisar com calma"
    assert (
        "email" not in fake.contexts[0]
        and "name" not in fake.contexts[0]
        and "student_id" not in fake.contexts[0]
    )
    assert (
        client.post(
            f"/professional/students/{foreign.id}/ai/{kind}", headers=ORIGIN, json={}
        ).status_code
        == 404
    )
    login(client, student.user.email)
    assert client.get(f"/student/{kind}").json()[kind] is None
    assert client.get("/notifications/unread-count").json()["count"] == 0
    assert client.post(path, headers=ORIGIN, json={}).status_code == 403
    login(client, owner.user.email)
    editor_path = f"/professional/{kind}-versions/{body['id']}"
    edited = client.patch(editor_path, headers=ORIGIN, json={**fake.output, "expected_revision": 1})
    assert edited.status_code == 200, edited.text
    assert edited.json()["source"] == "AI_GENERATED"
    approved = client.post(editor_path + "/approve", headers=ORIGIN, json={"expected_revision": 2})
    assert approved.status_code == 200, approved.text
    login(client, student.user.email)
    assert client.get(f"/student/{kind}").json()[kind]["name"] == "Sugestão neutra"
    assert client.get("/notifications/unread-count").json()["count"] == 1


@pytest.mark.parametrize("kind", ["diet", "workout"])
def test_invalid_output_leaves_no_plan(
    client: TestClient,
    db: Session,
    setup_ai: tuple[Professional, Professional, Student, Student, FakeProvider],
    kind: str,
) -> None:
    owner, _, student, _, fake = setup_ai
    fake.output = {"name": "Incompleto", "unexpected": "no"}
    login(client, owner.user.email)
    response = client.post(
        f"/professional/students/{student.id}/ai/{kind}", headers=ORIGIN, json={}
    )
    assert response.status_code == 502, response.text
    model = Diet if kind == "diet" else Workout
    assert db.scalars(select(model).where(model.student_id == student.id)).all() == []


def test_transfer_uses_current_owner(
    client: TestClient,
    db: Session,
    setup_ai: tuple[Professional, Professional, Student, Student, FakeProvider],
) -> None:
    old, new, student, _, fake = setup_ai
    fake.output = {
        "name": "Treino sintético",
        "days": [{"name": "Dia", "exercises": [{"name": "Movimento"}]}],
    }
    student.professional_id = new.id
    db.commit()
    path = f"/professional/students/{student.id}/ai/workout"
    login(client, old.user.email)
    assert client.post(path, headers=ORIGIN, json={}).status_code == 404
    login(client, new.user.email)
    result = client.post(path, headers=ORIGIN, json={})
    assert result.status_code == 201, result.text
    plan = db.scalar(select(Workout).where(Workout.student_id == student.id))
    assert plan is not None and plan.professional_id == new.id


def test_disabled_and_anonymous(
    client: TestClient,
    app: FastAPI,
    setup_ai: tuple[Professional, Professional, Student, Student, FakeProvider],
) -> None:
    owner, _, student, _, _ = setup_ai
    path = f"/professional/students/{student.id}/ai/diet"
    assert client.post(path, headers=ORIGIN, json={}).status_code == 401
    login(client, owner.user.email)
    settings = app.dependency_overrides[get_settings]()
    settings.ai_enabled = False
    assert client.get("/professional/ai/config").json() == {"enabled": False}
    assert client.post(path, headers=ORIGIN, json={}).status_code == 503


def test_medical_output_rejected() -> None:
    from app.ai.safety import validate_scope

    with pytest.raises(ValueError):
        validate_scope({"notes": "Prescrever hormônio para o aluno"})
    validate_scope({"notes": "Revisar com o profissional"})

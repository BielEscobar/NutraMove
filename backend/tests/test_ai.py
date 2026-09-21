import json
import logging
from collections.abc import Iterator
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.ai.generation import GenerationInput, _context
from app.ai.provider import ProviderFailure
from app.api.ai import get_ai_provider
from app.core.config import get_settings
from app.core.rate_limit import consume
from app.core.security import hash_password
from app.db.session import get_db
from app.models import Professional, Student, StudentStatus, User, UserRole
from app.models.diet import Diet, DietStatus, DietVersion
from app.models.reevaluation import ReevaluationCategory, ReevaluationRequest, ReevaluationStatus
from app.models.student import ActivityLevel, Goal, TrainingExperience
from app.models.workout import Workout, WorkoutVersion
from app.schemas.workout import VersionContent as WorkoutContent

ORIGIN = {"Origin": "http://localhost:3000"}
PASSWORD = "test-only-password-2026"


class FakeProvider:
    def __init__(self) -> None:
        self.contexts: list[dict[str, Any]] = []
        self.kinds: list[str] = []
        self.output: object = {}
        self.outputs: dict[str, object] = {}
        self.fail = False
        self.fail_kinds: set[str] = set()

    def generate_structured(
        self, *, kind: str, context: dict[str, Any], schema: dict[str, Any]
    ) -> object:
        self.kinds.append(kind)
        self.contexts.append(context)
        if kind in self.fail_kinds:
            raise ProviderFailure
        if self.fail:
            raise ValueError("provider failed")
        return self.outputs.get(kind, self.output)


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


def test_workout_generation_survives_new_sessions_and_approves(
    app: FastAPI, auth_engine: Engine
) -> None:
    settings = app.dependency_overrides[get_settings]()
    settings.ai_enabled = True
    settings.ai_api_key = SecretStr("test-only")
    fake = FakeProvider()
    fake.output = {
        "name": "Treino sintético",
        "frequency_per_week": 3,
        "days": [
            {
                "name": f"Dia {index}",
                "isRest": False,
                "exercises": [{"name": f"Movimento {exercise}"} for exercise in range(3)],
            }
            for index in range(3)
        ],
    }
    app.dependency_overrides[get_ai_provider] = lambda: fake

    def fresh_db() -> Iterator[Session]:
        with Session(auth_engine) as session:
            yield session

    app.dependency_overrides[get_db] = fresh_db
    with Session(auth_engine) as session:
        owner = Professional(
            user=User(
                name="Synthetic Owner",
                email="fresh-owner@example.com",
                role=UserRole.PROFESSIONAL,
                password_hash=hash_password(PASSWORD),
            )
        )
        session.add(owner)
        session.flush()
        student = Student(
            user=User(
                name="Synthetic Student",
                email="fresh-student@example.com",
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
        session.add(student)
        session.commit()
        student_id = student.id
    with TestClient(app, raise_server_exceptions=False) as client:
        login(client, "fresh-owner@example.com")
        result = client.post(
            f"/professional/students/{student_id}/ai/workout", headers=ORIGIN, json={}
        )
        assert result.status_code == 201, result.text
        version_id = UUID(result.json()["id"])
        with Session(auth_engine) as session:
            persisted = session.get(WorkoutVersion, version_id)
            assert persisted is not None
            assert len(persisted.days) == 3
            assert all(not day.is_rest and len(day.exercises) == 3 for day in persisted.days)
        detail = client.get(f"/professional/workout-versions/{version_id}")
        assert detail.status_code == 200
        assert all(not day["isRest"] and day["exercises"] for day in detail.json()["days"])
        approved = client.post(
            f"/professional/workout-versions/{version_id}/approve",
            headers=ORIGIN,
            json={"expected_revision": detail.json()["edit_revision"]},
        )
        assert approved.status_code == 200, approved.text
        login(client, "fresh-student@example.com")
        visible = client.get("/student/workout")
        assert visible.status_code == 200
        assert visible.json()["workout"]["name"] == "Treino sintético"
        assert len(visible.json()["workout"]["days"]) == 3


@pytest.mark.parametrize("removed_kind", ["diet", "workout"])
def test_combined_generation_recreates_only_deleted_kind(
    client: TestClient,
    setup_ai: tuple[Professional, Professional, Student, Student, FakeProvider],
    removed_kind: str,
) -> None:
    owner, _, student, _, fake = setup_ai
    fake.outputs = {"diet": DIET_OUTPUT, "workout": WORKOUT_OUTPUT}
    login(client, owner.user.email)
    url = f"/professional/students/{student.id}/ai/plans"
    first = client.post(url, headers=ORIGIN, json={})
    assert first.status_code == 200, first.text
    original = first.json()
    deleted_id = original[removed_kind]["id"]
    assert (
        client.delete(
            f"/professional/{removed_kind}-versions/{deleted_id}", headers=ORIGIN
        ).status_code
        == 204
    )
    second = client.post(url, headers=ORIGIN, json={})
    assert second.status_code == 200, second.text
    assert second.json()[removed_kind]["id"] != deleted_id
    other = "diet" if removed_kind == "workout" else "workout"
    assert second.json()[other]["id"] == original[other]["id"]


DIET_OUTPUT = {
    "name": "Sugestão alimentar",
    "meals": [
        {
            "name": "Refeição",
            "foods": [{"name": "Alimento", "quantity": "1", "unit": "porção"}],
        }
    ],
}
WORKOUT_OUTPUT = {
    "name": "Sugestão de treino",
    "frequency_per_week": 1,
    "days": [{"name": "Dia A", "exercises": [{"name": "Movimento"}]}],
}

WORKOUT_WITH_REST = {
    "name": "Treino sintético com descanso",
    "frequency_per_week": 2,
    "days": [
        {
            "name": "Segunda: treino",
            "isRest": False,
            "exercises": [
                {
                    "name": "Agachamento",
                    "muscle_group": "Pernas",
                    "sets": 3,
                    "repetitions": "12",
                    "rest_seconds": 60,
                }
            ],
        },
        {"name": "Recuperação", "description": "Folga", "isRest": True, "exercises": []},
    ],
}


def test_workout_ai_schema_exposes_structural_rest_flag() -> None:
    schema = WorkoutContent.model_json_schema()
    day_schema = schema["$defs"]["DayInput"]
    assert "isRest" in day_schema["properties"]
    assert day_schema["properties"]["isRest"]["type"] == "boolean"


@pytest.mark.parametrize("active_days", [4, 5, 6])
def test_ai_workout_accepts_active_days_without_explicit_rest(
    client: TestClient,
    setup_ai: tuple[Professional, Professional, Student, Student, FakeProvider],
    active_days: int,
) -> None:
    owner, _, student, _, fake = setup_ai
    student.training_frequency = active_days
    student.available_training_days = "dias disponíveis sintéticos"
    fake.output = {
        "name": "Treino com descanso implícito",
        "frequency_per_week": active_days,
        "days": [
            {"name": f"Dia {index}", "isRest": False, "exercises": [{"name": "Movimento"}]}
            for index in range(active_days)
        ],
    }
    login(client, owner.user.email)
    result = client.post(f"/professional/students/{student.id}/ai/workout", headers=ORIGIN, json={})
    assert result.status_code == 201, result.text
    assert result.json()["status"] == "PENDING_REVIEW"
    assert len(result.json()["days"]) == active_days
    assert all(not day["isRest"] for day in result.json()["days"])
    approved = client.post(
        f"/professional/workout-versions/{result.json()['id']}/approve",
        headers=ORIGIN,
        json={"expected_revision": 1},
    )
    assert approved.status_code == 200, approved.text
    login(client, student.user.email)
    assert len(client.get("/student/workout").json()["workout"]["days"]) == active_days


def test_ai_workout_rejects_seven_active_days(
    client: TestClient,
    setup_ai: tuple[Professional, Professional, Student, Student, FakeProvider],
) -> None:
    owner, _, student, _, fake = setup_ai
    student.training_frequency = 7
    fake.output = {
        "name": "Treino excessivo",
        "days": [
            {"name": f"Dia {index}", "isRest": False, "exercises": [{"name": "Movimento"}]}
            for index in range(7)
        ],
    }
    login(client, owner.user.email)
    result = client.post(f"/professional/students/{student.id}/ai/workout", headers=ORIGIN, json={})
    assert result.status_code == 502


def test_ai_workout_accepts_rest_day_without_auto_approval(
    client: TestClient,
    db: Session,
    setup_ai: tuple[Professional, Professional, Student, Student, FakeProvider],
) -> None:
    owner, _, student, _, fake = setup_ai
    fake.output = WORKOUT_WITH_REST
    login(client, owner.user.email)
    result = client.post(f"/professional/students/{student.id}/ai/workout", headers=ORIGIN, json={})
    assert result.status_code == 201, result.text
    assert result.json()["source"] == "AI_GENERATED"
    assert result.json()["status"] == "PENDING_REVIEW"
    detail = client.get(f"/professional/workout-versions/{result.json()['id']}")
    assert detail.status_code == 200
    assert detail.json()["days"][1]["exercises"] == []
    assert detail.json()["days"][1]["isRest"] is True
    version = db.get(WorkoutVersion, UUID(result.json()["id"]))
    assert version is not None and version.days[1].is_rest is True
    assert (
        client.get(f"/professional/workout-versions/{result.json()['id']}").json()["edit_revision"]
        == 1
    )
    login(client, student.user.email)
    assert client.get("/student/workout").json()["workout"] is None
    login(client, owner.user.email)
    approved = client.post(
        f"/professional/workout-versions/{result.json()['id']}/approve",
        headers=ORIGIN,
        json={"expected_revision": 1},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["source"] == "AI_GENERATED"
    assert approved.json()["status"] == "APPROVED"
    login(client, student.user.email)
    visible = client.get("/student/workout").json()["workout"]
    assert visible["name"] == WORKOUT_WITH_REST["name"]
    assert visible["days"][1]["exercises"] == []
    assert visible["days"][1]["isRest"] is True


def test_ai_workout_schema_rejection_logs_field_without_content(
    client: TestClient,
    db: Session,
    setup_ai: tuple[Professional, Professional, Student, Student, FakeProvider],
    caplog: pytest.LogCaptureFixture,
) -> None:
    owner, _, student, _, fake = setup_ai
    fake.output = {
        **WORKOUT_WITH_REST,
        "days": [
            {
                "name": "Treino",
                "exercises": [{"name": "Movimento", "reps": "synthetic-secret-marker"}],
            }
        ],
    }
    login(client, owner.user.email)
    with caplog.at_level(logging.WARNING, logger="app.ai.generation"):
        result = client.post(
            f"/professional/students/{student.id}/ai/workout", headers=ORIGIN, json={}
        )
    assert result.status_code == 502
    assert "schema_validation" in caplog.text
    assert "days.0.exercises.0.reps" in caplog.text
    assert "synthetic-secret-marker" not in caplog.text
    assert db.scalars(select(Workout).where(Workout.student_id == student.id)).all() == []


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


def test_completed_reevaluation_snapshot_replaces_initial_ai_context(
    db: Session,
    setup_ai: tuple[Professional, Professional, Student, Student, FakeProvider],
) -> None:
    owner, _, student, _, _ = setup_ai
    student.work_routine = "initial routine sentinel"
    student.available_equipment = "initial equipment sentinel"
    student.weekly_food_budget = 111
    snapshot = {
        "weight": 82,
        "desired_weight": 76,
        "goal": "BODY_RECOMPOSITION",
        "activity_level": "HIGH",
        "training_frequency": 4,
        "available_training_days": "segunda, terça, quinta e sábado",
        "progress_perception": "synthetic progress",
        "difficulties": "synthetic difficulties",
        "observations": "synthetic observations",
        "work_routine": "updated routine sentinel",
        "available_equipment": "updated equipment sentinel",
        "weekly_food_budget": 222,
    }
    db.add(
        ReevaluationRequest(
            student_id=student.id,
            professional_id=owner.id,
            category=ReevaluationCategory.EVOLUTION,
            reason="Synthetic completed reevaluation",
            status=ReevaluationStatus.COMPLETED,
            snapshot=snapshot,
            professional_response="Synthetic response",
            completed_at=datetime.now(UTC),
        )
    )
    db.add(
        ReevaluationRequest(
            student_id=student.id,
            professional_id=owner.id,
            category=ReevaluationCategory.EVOLUTION,
            reason="Synthetic pending reevaluation",
            status=ReevaluationStatus.PENDING,
            snapshot={**snapshot, "weight": 99, "work_routine": "pending sentinel"},
        )
    )
    db.commit()

    diet, _ = _context(db, owner.user, student.id, "diet", GenerationInput())
    workout, _ = _context(db, owner.user, student.id, "workout", GenerationInput())
    assert diet["weight"] == 82 and diet["work_routine"] == "updated routine sentinel"
    assert diet["weekly_food_budget"] == 222
    assert workout["weight"] == 82
    assert workout["work_routine"] == "updated routine sentinel"
    assert workout["available_equipment"] == "updated equipment sentinel"
    serialized = json.dumps({"diet": diet, "workout": workout})
    assert not {"name", "email", "phone", "student_id", "user_id"}.intersection(diet)
    assert not {"name", "email", "phone", "student_id", "user_id"}.intersection(workout)
    assert "initial routine sentinel" not in serialized
    assert "initial equipment sentinel" not in serialized
    assert "pending sentinel" not in serialized and "99" not in serialized
    for forbidden in (
        student.user.name,
        student.user.email,
        str(student.id),
        "photo_url",
        "storage_key",
        "base64",
    ):
        assert forbidden not in serialized


def test_completed_reevaluation_creates_new_ai_versions_without_changing_history(
    client: TestClient,
    db: Session,
    setup_ai: tuple[Professional, Professional, Student, Student, FakeProvider],
) -> None:
    owner, _, student, _, fake = setup_ai
    student.weight = 80
    student.training_frequency = 5
    student.available_training_days = "segunda a sexta"
    student.training_history = "histórico inicial preservado"
    student.weekly_food_budget = 200
    db.commit()
    fake.outputs = {"diet": DIET_OUTPUT, "workout": WORKOUT_OUTPUT}
    plans_path = f"/professional/students/{student.id}/ai/plans"
    login(client, owner.user.email)
    first = client.post(plans_path, headers=ORIGIN, json={})
    assert first.status_code == 200, first.text
    old = first.json()
    assert fake.contexts[0]["weight"] == 80
    assert fake.contexts[1]["training_frequency"] == 5
    for kind in ("diet", "workout"):
        approved = client.post(
            f"/professional/{kind}-versions/{old[kind]['id']}/approve",
            headers=ORIGIN,
            json={"expected_revision": 1},
        )
        assert approved.status_code == 200, approved.text
    snapshot = {
        "weight": 76,
        "goal": "DEFINITION",
        "activity_level": "HIGH",
        "training_frequency": 4,
        "available_training_days": "segunda, terça, quinta e sábado",
        "progress_perception": "Progresso sintético",
        "difficulties": "Dificuldade sintética",
        "observations": "Observação sintética",
        "training_location": "HOME",
        "available_equipment": "halteres e elásticos",
        "weekly_food_budget": 150,
        "wake_time": "06:00:00",
    }
    login(client, student.user.email)
    created = client.post(
        "/student/reevaluation-requests",
        headers=ORIGIN,
        json={"category": "EVOLUTION", "reason": "Atualizar plano sintético", "snapshot": snapshot},
    )
    assert created.status_code == 201, created.text
    request_id = created.json()["id"]
    login(client, owner.user.email)
    for status in ("PENDING", "IN_REVIEW"):
        diet_context, _ = _context(db, owner.user, student.id, "diet", GenerationInput())
        workout_context, _ = _context(db, owner.user, student.id, "workout", GenerationInput())
        assert diet_context["weight"] == 80 and diet_context["weekly_food_budget"] == 200
        assert workout_context["training_frequency"] == 5
        assert client.get(plans_path).json()["diet"]["id"] == old["diet"]["id"]
        if status == "PENDING":
            review = client.post(
                f"/professional/reevaluation-requests/{request_id}/start-review",
                headers=ORIGIN,
            )
            assert review.status_code == 200, review.text
    completed = client.post(
        f"/professional/reevaluation-requests/{request_id}/complete",
        headers=ORIGIN,
        json={"professional_response": "Revisão sintética concluída."},
    )
    assert completed.status_code == 200, completed.text
    assert client.get(plans_path).json() == {"diet": None, "workout": None}
    fake.contexts.clear()
    fake.outputs = {
        "diet": {**DIET_OUTPUT, "name": "Dieta B"},
        "workout": {**WORKOUT_OUTPUT, "name": "Treino B"},
    }
    second = client.post(plans_path, headers=ORIGIN, json={})
    assert second.status_code == 200, second.text
    new = second.json()
    assert new["diet_error"] is None and new["workout_error"] is None, new
    for kind in ("diet", "workout"):
        assert new[kind]["id"] != old[kind]["id"]
        assert new[kind]["status"] == "PENDING_REVIEW"
        old_detail = client.get(f"/professional/{kind}-versions/{old[kind]['id']}").json()
        new_detail = client.get(f"/professional/{kind}-versions/{new[kind]['id']}").json()
        assert old_detail["status"] == "APPROVED"
        assert old_detail["version_number"] == 1
        assert new_detail["version_number"] == 2
        assert new_detail["source"] == "AI_GENERATED"
    diet_context, workout_context = fake.contexts
    assert diet_context["weight"] == 76 and diet_context["goal"] == "DEFINITION"
    assert diet_context["weekly_food_budget"] == 150
    assert diet_context["wake_time"] == "06:00:00"
    assert workout_context["training_frequency"] == 4
    assert workout_context["training_location"] == "HOME"
    assert workout_context["available_equipment"] == "halteres e elásticos"
    assert workout_context["training_history"] == "histórico inicial preservado"
    assert all("photo" not in str(context).lower() for context in fake.contexts)
    login(client, student.user.email)
    assert client.get("/student/diet").json()["diet"]["name"] == DIET_OUTPUT["name"]
    login(client, owner.user.email)
    for kind in ("diet", "workout"):
        approved = client.post(
            f"/professional/{kind}-versions/{new[kind]['id']}/approve",
            headers=ORIGIN,
            json={"expected_revision": 1},
        )
        assert approved.status_code == 200, approved.text
        assert (
            client.get(f"/professional/{kind}-versions/{old[kind]['id']}").json()["status"]
            == "ARCHIVED"
        )
    login(client, student.user.email)
    assert client.get("/student/diet").json()["diet"]["name"] == "Dieta B"
    assert client.get("/student/workout").json()["workout"]["name"] == "Treino B"


def test_combined_generation_is_idempotent_and_private(
    client: TestClient,
    db: Session,
    setup_ai: tuple[Professional, Professional, Student, Student, FakeProvider],
) -> None:
    owner, _, student, _, fake = setup_ai
    fake.outputs = {"diet": DIET_OUTPUT, "workout": WORKOUT_WITH_REST}
    path = f"/professional/students/{student.id}/ai/plans"
    login(client, owner.user.email)
    first = client.post(path, headers=ORIGIN, json={})
    assert first.status_code == 200, first.text
    body = first.json()
    for kind in ("diet", "workout"):
        assert body[kind]["source"] == "AI_GENERATED"
        assert body[kind]["status"] == "PENDING_REVIEW"
        assert body[f"{kind}_error"] is None
        detail = client.get(f"/professional/{kind}-versions/{body[kind]['id']}")
        assert detail.status_code == 200
    assert len(fake.contexts) == 2
    assert all(
        not {"name", "email", "phone", "student_id", "user_id"}.intersection(context)
        for context in fake.contexts
    )
    second = client.post(path, headers=ORIGIN, json={})
    assert second.status_code == 200
    assert second.json()["diet"]["id"] == body["diet"]["id"]
    assert second.json()["workout"]["id"] == body["workout"]["id"]
    assert len(fake.contexts) == 2
    assert len(db.scalars(select(Diet).where(Diet.student_id == student.id)).all()) == 1
    assert len(db.scalars(select(Workout).where(Workout.student_id == student.id)).all()) == 1
    login(client, student.user.email)
    assert client.get("/student/diet").json()["diet"] is None
    assert client.get("/student/workout").json()["workout"] is None
    assert client.get("/notifications/unread-count").json()["count"] == 0


def test_combined_generation_permissions_and_active_status(
    client: TestClient,
    db: Session,
    setup_ai: tuple[Professional, Professional, Student, Student, FakeProvider],
) -> None:
    owner, other, student, _, fake = setup_ai
    fake.outputs = {"diet": DIET_OUTPUT, "workout": WORKOUT_OUTPUT}
    path = f"/professional/students/{student.id}/ai/plans"
    assert client.post(path, headers=ORIGIN, json={}).status_code == 401
    login(client, other.user.email)
    assert client.post(path, headers=ORIGIN, json={}).status_code == 404
    login(client, student.user.email)
    assert client.post(path, headers=ORIGIN, json={}).status_code == 403
    master = User(
        name="Master",
        email="master-ai@example.com",
        role=UserRole.MASTER,
        password_hash=hash_password(PASSWORD),
    )
    db.add(master)
    db.commit()
    login(client, master.email)
    assert client.post(path, headers=ORIGIN, json={}).status_code == 403
    student.status = StudentStatus.PENDING_APPROVAL
    db.commit()
    login(client, owner.user.email)
    assert client.post(path, headers=ORIGIN, json={}).status_code == 409
    assert not fake.contexts


def test_plans_state_uses_database_independently_of_ai_configuration(
    client: TestClient,
    db: Session,
    app: FastAPI,
    setup_ai: tuple[Professional, Professional, Student, Student, FakeProvider],
) -> None:
    owner, other, student, other_student, fake = setup_ai
    settings = app.dependency_overrides[get_settings]()
    path = f"/professional/students/{student.id}/ai/plans"

    login(client, owner.user.email)
    for enabled in (False, True):
        settings.ai_enabled = enabled
        empty = client.get(path)
        assert empty.status_code == 200, empty.text
        assert empty.json() == {"diet": None, "workout": None}

    diet = client.post(
        f"/professional/students/{student.id}/diets", headers=ORIGIN, json=DIET_OUTPUT
    )
    assert diet.status_code == 201, diet.text
    diet_id = diet.json()["id"]
    diet_version = client.get(f"/professional/diet-versions/{diet_id}").json()
    assert (
        client.patch(
            f"/professional/diet-versions/{diet_id}",
            headers=ORIGIN,
            json={**DIET_OUTPUT, "expected_revision": diet_version["edit_revision"]},
        ).status_code
        == 200
    )
    state = client.get(path)
    assert state.status_code == 200, state.text
    assert state.json()["diet"]["status"] == "DRAFT"
    assert state.json()["workout"] is None

    db_diet = db.get(DietVersion, diet_id)
    assert db_diet is not None
    db_diet.status = DietStatus.PENDING_REVIEW
    db.commit()
    assert client.get(path).json()["diet"]["status"] == "PENDING_REVIEW"
    approved_diet = client.post(
        f"/professional/diet-versions/{diet_id}/approve",
        headers=ORIGIN,
        json={"expected_revision": db_diet.edit_revision},
    )
    assert approved_diet.status_code == 200, approved_diet.text
    assert client.get(path).json()["diet"]["status"] == "APPROVED"

    login(client, other.user.email)
    workout = client.post(
        f"/professional/students/{other_student.id}/workouts",
        headers=ORIGIN,
        json=WORKOUT_OUTPUT,
    )
    assert workout.status_code == 201, workout.text
    workout_only = client.get(f"/professional/students/{other_student.id}/ai/plans")
    assert workout_only.status_code == 200, workout_only.text
    assert workout_only.json()["diet"] is None
    assert workout_only.json()["workout"]["status"] == "DRAFT"
    assert client.get(path).status_code == 404

    login(client, owner.user.email)
    workout = client.post(
        f"/professional/students/{student.id}/workouts",
        headers=ORIGIN,
        json=WORKOUT_OUTPUT,
    )
    assert workout.status_code == 201, workout.text
    both = client.get(path)
    assert both.status_code == 200, both.text
    assert both.json()["diet"]["status"] == "APPROVED"
    assert both.json()["workout"]["status"] == "DRAFT"
    assert fake.kinds == []


def test_combined_generation_preserves_existing_and_generates_missing(
    client: TestClient,
    db: Session,
    setup_ai: tuple[Professional, Professional, Student, Student, FakeProvider],
) -> None:
    owner, _, student, _, fake = setup_ai
    login(client, owner.user.email)
    existing = client.post(
        f"/professional/students/{student.id}/diets", headers=ORIGIN, json=DIET_OUTPUT
    )
    assert existing.status_code == 201
    fake.outputs = {"workout": WORKOUT_OUTPUT}
    result = client.post(f"/professional/students/{student.id}/ai/plans", headers=ORIGIN, json={})
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["diet"]["id"] == existing.json()["id"]
    assert body["diet"]["source"] == "MANUAL"
    assert body["workout"]["source"] == "AI_GENERATED"
    assert fake.kinds == ["workout"]
    assert len(db.scalars(select(Diet).where(Diet.student_id == student.id)).all()) == 1


@pytest.mark.parametrize("failed_kind", ["diet", "workout"])
def test_combined_generation_keeps_partial_success_and_retries_missing(
    client: TestClient,
    db: Session,
    setup_ai: tuple[Professional, Professional, Student, Student, FakeProvider],
    failed_kind: str,
) -> None:
    owner, _, student, _, fake = setup_ai
    fake.outputs = {"diet": DIET_OUTPUT, "workout": WORKOUT_WITH_REST}
    fake.fail_kinds = {failed_kind}
    path = f"/professional/students/{student.id}/ai/plans"
    login(client, owner.user.email)
    first = client.post(path, headers=ORIGIN, json={})
    assert first.status_code == 200, first.text
    other_kind = "workout" if failed_kind == "diet" else "diet"
    assert first.json()[failed_kind] is None
    assert first.json()[f"{failed_kind}_error"] == "Serviço de IA indisponível. Tente novamente."
    preserved_id = first.json()[other_kind]["id"]
    fake.fail_kinds.clear()
    second = client.post(path, headers=ORIGIN, json={})
    assert second.status_code == 200, second.text
    assert second.json()[failed_kind] is not None
    assert second.json()[other_kind]["id"] == preserved_id
    assert len(db.scalars(select(Diet).where(Diet.student_id == student.id)).all()) == 1
    assert len(db.scalars(select(Workout).where(Workout.student_id == student.id)).all()) == 1


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
    assert (
        client.post(
            f"/professional/students/{student.id}/ai/plans", headers=ORIGIN, json={}
        ).status_code
        == 503
    )
    manual = client.post(
        f"/professional/students/{student.id}/diets", headers=ORIGIN, json=DIET_OUTPUT
    )
    assert manual.status_code == 201
    assert manual.json()["source"] == "MANUAL"


def test_medical_output_rejected() -> None:
    from app.ai.safety import validate_scope

    with pytest.raises(ValueError):
        validate_scope({"notes": "Prescrever hormônio para o aluno"})
    validate_scope({"notes": "Revisar com o profissional"})


def test_ai_rate_limit(
    client: TestClient,
    db: Session,
    app: FastAPI,
    setup_ai: tuple[Professional, Professional, Student, Student, FakeProvider],
) -> None:
    owner, _, student, _, fake = setup_ai
    settings = app.dependency_overrides[get_settings]()
    for _ in range(10):
        consume(db, settings, "ai", str(owner.user_id), limit=10, period_seconds=3600)
    login(client, owner.user.email)
    response = client.post(f"/professional/students/{student.id}/ai/diet", headers=ORIGIN, json={})
    assert response.status_code == 429
    assert not fake.contexts

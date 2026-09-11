from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, delete, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Professional,
    Student,
    StudentStatus,
    User,
    UserRole,
    Workout,
    WorkoutExercise,
    WorkoutVersion,
)
from app.models.student import ActivityLevel, Goal, TrainingExperience
from app.models.workout import WorkoutSource, WorkoutStatus
from app.schemas.workout import VersionContent
from app.services import workouts as service

ORIGIN = {"Origin": "http://localhost:3000"}
PASSWORD = "test-only-password-2026"


@dataclass
class Family:
    master: User
    a: Professional
    b: Professional
    student_a: Student
    student_b: Student


def make_student(owner: Professional, email: str, password_hash: str) -> Student:
    return Student(
        user=User(name=email, email=email, role=UserRole.STUDENT, password_hash=password_hash),
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


@pytest.fixture
def family(db: Session, user: User) -> Family:
    professionals = [
        Professional(
            user=User(
                name=label,
                email=f"{label}@example.com",
                role=UserRole.PROFESSIONAL,
                password_hash=user.password_hash,
            )
        )
        for label in ("a", "b")
    ]
    db.add_all(professionals)
    db.flush()
    a, b = professionals
    sa = make_student(a, "student-a@example.com", user.password_hash)
    sb = make_student(b, "student-b@example.com", user.password_hash)
    db.add_all([sa, sb])
    db.commit()
    return Family(user, a, b, sa, sb)


@pytest.fixture
def content() -> dict[str, object]:
    return {
        "name": "Plano manual",
        "goal": "Objetivo informado",
        "start_date": "2026-09-10",
        "next_review_date": "2026-10-10",
        "frequency_per_week": 3,
        "notes": "Observacao",
        "days": [
            {
                "name": "Upper",
                "description": "Dia livre",
                "exercises": [
                    {
                        "name": "Supino",
                        "muscle_group": "Peito",
                        "description": "Banco",
                        "instructions": "Movimento controlado",
                        "sets": 4,
                        "repetitions": "8-12",
                        "load": "RPE 8",
                        "duration": "30 segundos",
                        "rest_seconds": 90,
                        "notes": "Nota",
                    }
                ],
            }
        ],
    }


def login(client: TestClient, user: User) -> None:
    client.cookies.clear()
    assert (
        client.post(
            "/auth/login", headers=ORIGIN, json={"email": user.email, "password": PASSWORD}
        ).status_code
        == 200
    )


@pytest.fixture
def draft(client: TestClient, family: Family, content: dict[str, object]) -> dict[str, object]:
    login(client, family.a.user)
    result = client.post(
        f"/professional/students/{family.student_a.id}/workouts", headers=ORIGIN, json=content
    )
    assert result.status_code == 201, result.text
    data: dict[str, object] = result.json()
    return data


def test_creation_and_tree(
    client: TestClient, family: Family, draft: dict[str, object], db: Session
) -> None:
    assert draft["source"] == "MANUAL" and draft["status"] == "DRAFT"
    assert draft["version_number"] == 1 and draft["edit_revision"] == 1
    version = db.get(WorkoutVersion, UUID(str(draft["id"])))
    assert version and version.created_by_user_id == family.a.user_id
    exercise = version.days[0].exercises[0]
    assert exercise.sets == 4 and exercise.repetitions == "8-12"
    assert exercise.load == "RPE 8" and exercise.rest_seconds == 90
    assert exercise.duration == "30 segundos" and exercise.instructions == "Movimento controlado"
    assert version.frequency_per_week == 3 and version.days[0].description == "Dia livre"
    assert version.days[0].position == 0
    assert (
        client.get(f"/professional/students/{family.student_a.id}/workouts").json()[0]["id"]
        == draft["workout_id"]
    )
    assert (
        client.get(f"/professional/workouts/{draft['workout_id']}/versions").json()[0]["id"]
        == draft["id"]
    )
    assert "password" not in str(draft) and "token" not in str(draft)


@pytest.mark.parametrize(
    "field,value",
    [
        ("source", "AI_GENERATED"),
        ("status", "APPROVED"),
        ("professional_id", str(uuid4())),
        ("student_id", str(uuid4())),
        ("created_by_user_id", str(uuid4())),
        ("approved_at", "2026-01-01"),
    ],
)
def test_injected_create_fields(
    client: TestClient, family: Family, content: dict[str, object], field: str, value: str
) -> None:
    login(client, family.a.user)
    content[field] = value
    assert (
        client.post(
            f"/professional/students/{family.student_a.id}/workouts", headers=ORIGIN, json=content
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/professional/students/{student}/workouts"),
        ("POST", "/professional/students/{student}/workouts"),
        ("GET", "/professional/workouts/{workout}"),
        ("GET", "/professional/workouts/{workout}/versions"),
        ("POST", "/professional/workouts/{workout}/versions"),
        ("GET", "/professional/workout-versions/{version}"),
        ("PATCH", "/professional/workout-versions/{version}"),
        ("POST", "/professional/workout-versions/{version}/duplicate"),
        ("POST", "/professional/workout-versions/{version}/approve"),
    ],
)
def test_bola_all_routes(
    client: TestClient,
    family: Family,
    draft: dict[str, object],
    content: dict[str, object],
    method: str,
    path: str,
) -> None:
    login(client, family.b.user)
    url = path.format(student=family.student_a.id, workout=draft["workout_id"], version=draft["id"])
    body: dict[str, object] = (
        {"expected_revision": 1}
        if path.endswith("/approve")
        else content | ({"expected_revision": 1} if method == "PATCH" else {})
    )
    assert (
        client.request(
            method, url, headers=ORIGIN, json=body if method != "GET" else None
        ).status_code
        == 404
    )


def test_composed_edit_atomic(
    client: TestClient, draft: dict[str, object], content: dict[str, object], db: Session
) -> None:
    path = f"/professional/workout-versions/{draft['id']}"
    original = client.get(path).json()

    def fail(*args: object) -> None:
        raise IntegrityError("test", {}, Exception("test-only"))

    event.listen(WorkoutExercise, "before_insert", fail)
    try:
        response = client.patch(
            path, headers=ORIGIN, json=content | {"name": "Changed", "expected_revision": 1}
        )
        assert response.status_code == 409
    finally:
        event.remove(WorkoutExercise, "before_insert", fail)
    assert client.get(path).json() == original
    result = client.patch(
        path, headers=ORIGIN, json=content | {"name": "Changed", "expected_revision": 1}
    )
    assert result.status_code == 200
    assert result.json()["edit_revision"] == 2
    assert (
        client.patch(path, headers=ORIGIN, json=content | {"expected_revision": 1}).status_code
        == 409
    )
    assert (
        client.post(path + "/approve", headers=ORIGIN, json={"expected_revision": 1}).status_code
        == 409
    )


def test_creation_atomic(
    client: TestClient, family: Family, content: dict[str, object], db: Session
) -> None:
    login(client, family.a.user)

    def fail(*args: object) -> None:
        raise IntegrityError("test", {}, Exception("test-only"))

    event.listen(WorkoutExercise, "before_insert", fail)
    try:
        assert (
            client.post(
                f"/professional/students/{family.student_a.id}/workouts",
                headers=ORIGIN,
                json=content,
            ).status_code
            == 409
        )
    finally:
        event.remove(WorkoutExercise, "before_insert", fail)
    assert db.scalar(select(Workout)) is None


def test_publish_duplicate_history(
    client: TestClient,
    family: Family,
    draft: dict[str, object],
    content: dict[str, object],
    db: Session,
) -> None:
    path = f"/professional/workout-versions/{draft['id']}"
    approved = client.post(path + "/approve", headers=ORIGIN, json={"expected_revision": 1})
    assert approved.status_code == 200
    original = approved.json()
    assert original["approved_by_user_id"] == str(family.a.user_id) and original["approved_at"]
    assert (
        client.patch(path, headers=ORIGIN, json=content | {"expected_revision": 2}).status_code
        == 409
    )
    duplicate = client.post(path + "/duplicate", headers=ORIGIN)
    assert duplicate.status_code == 201
    copied = duplicate.json()
    assert copied["status"] == "DRAFT" and copied["source"] == "MANUAL"
    assert copied["version_number"] == 2 and copied["workout_id"] == draft["workout_id"]
    assert copied["approved_at"] is None and copied["approved_by_user_id"] is None
    assert copied["days"] == original["days"] and copied["start_date"] == original["start_date"]
    first = db.get(WorkoutVersion, UUID(str(draft["id"])))
    second = db.get(WorkoutVersion, UUID(copied["id"]))
    assert first and second and first.days[0].id != second.days[0].id
    assert (
        client.post(
            f"/professional/workout-versions/{copied['id']}/approve",
            headers=ORIGIN,
            json={"expected_revision": 1},
        ).status_code
        == 200
    )
    archived = client.get(path).json()
    assert archived["status"] == "ARCHIVED" and archived["approved_at"] == original["approved_at"]
    assert archived["days"] == original["days"]
    assert (
        client.patch(path, headers=ORIGIN, json=content | {"expected_revision": 2}).status_code
        == 409
    )
    fresh = client.post(
        f"/professional/workouts/{draft['workout_id']}/versions", headers=ORIGIN, json=content
    )
    assert fresh.status_code == 201 and fresh.json()["version_number"] == 3
    login(client, family.student_a.user)
    visible = client.get(
        "/student/workout", params={"student_id": str(family.student_b.id)}
    ).json()["workout"]
    assert (
        visible["version_number"] == 2
        and "source" not in visible
        and "created_by_user_id" not in visible
    )


@pytest.mark.parametrize(
    "status,source",
    [
        (WorkoutStatus.DRAFT, WorkoutSource.MANUAL),
        (WorkoutStatus.PENDING_REVIEW, WorkoutSource.MANUAL),
        (WorkoutStatus.PENDING_REVIEW, WorkoutSource.AI_GENERATED),
        (WorkoutStatus.DRAFT, WorkoutSource.AI_GENERATED),
        (WorkoutStatus.ARCHIVED, WorkoutSource.MANUAL),
    ],
)
def test_student_never_sees_unpublished(
    client: TestClient,
    family: Family,
    draft: dict[str, object],
    db: Session,
    status: WorkoutStatus,
    source: WorkoutSource,
) -> None:
    version = db.get(WorkoutVersion, UUID(str(draft["id"])))
    assert version
    version.status = status
    version.source = source
    db.commit()
    login(client, family.student_a.user)
    assert client.get("/student/workout").json() == {"workout": None}
    assert client.get(f"/professional/workout-versions/{draft['id']}").status_code == 403


def test_student_current_across_plans(
    client: TestClient, family: Family, draft: dict[str, object], content: dict[str, object]
) -> None:
    assert (
        client.post(
            f"/professional/workout-versions/{draft['id']}/approve",
            headers=ORIGIN,
            json={"expected_revision": 1},
        ).status_code
        == 200
    )
    new = client.post(
        f"/professional/students/{family.student_a.id}/workouts",
        headers=ORIGIN,
        json=content | {"name": "New plan"},
    ).json()
    assert (
        client.post(
            f"/professional/workout-versions/{new['id']}/approve",
            headers=ORIGIN,
            json={"expected_revision": 1},
        ).status_code
        == 200
    )
    assert (
        client.get(f"/professional/workout-versions/{draft['id']}").json()["status"] == "ARCHIVED"
    )
    login(client, family.student_b.user)
    assert client.get(
        "/student/workout", params={"student_id": str(family.student_a.id)}
    ).json() == {"workout": None}
    login(client, family.student_a.user)
    assert client.get("/student/workout").json()["workout"]["name"] == "New plan"


def test_review_approval_and_pending_student(
    client: TestClient, family: Family, draft: dict[str, object], db: Session
) -> None:
    version = db.get(WorkoutVersion, UUID(str(draft["id"])))
    assert version
    version.status = WorkoutStatus.PENDING_REVIEW
    version.source = WorkoutSource.AI_GENERATED
    db.commit()
    assert (
        client.post(
            f"/professional/workout-versions/{draft['id']}/approve",
            headers=ORIGIN,
            json={"expected_revision": 1},
        ).status_code
        == 200
    )
    family.student_a.status = StudentStatus.PENDING_APPROVAL
    db.commit()
    login(client, family.student_a.user)
    assert client.get("/student/workout").json() == {"workout": None}


def test_invalid_content_and_publication(
    client: TestClient,
    family: Family,
    draft: dict[str, object],
    content: dict[str, object],
    db: Session,
) -> None:
    path = f"/professional/workout-versions/{draft['id']}"
    invalid_changes: list[dict[str, object]] = [
        {"name": " "},
        {"next_review_date": "2025-01-01"},
        {"frequency_per_week": 8},
        {"days": [{"name": "A", "exercises": [{"name": "E", "sets": 0}]}]},
        {"days": [{"name": "A", "exercises": [{"name": "E", "rest_seconds": -1}]}]},
        {"days": [{"name": "A", "exercises": [{"name": "E", "sets": True}]}]},
    ]
    for changed in invalid_changes:
        assert (
            client.patch(
                path, headers=ORIGIN, json=content | changed | {"expected_revision": 1}
            ).status_code
            == 422
        )
    family.student_a.status = StudentStatus.PENDING_APPROVAL
    db.commit()
    assert (
        client.post(path + "/approve", headers=ORIGIN, json={"expected_revision": 1}).status_code
        == 409
    )
    family.student_a.status = StudentStatus.ACTIVE
    db.commit()
    assert (
        client.patch(
            path, headers=ORIGIN, json=content | {"days": [], "expected_revision": 1}
        ).status_code
        == 200
    )
    assert (
        client.post(path + "/approve", headers=ORIGIN, json={"expected_revision": 2}).status_code
        == 422
    )


@pytest.mark.parametrize(
    "suffix,method", [("", "PATCH"), ("/duplicate", "POST"), ("/approve", "POST")]
)
def test_csrf_and_roles(
    client: TestClient,
    family: Family,
    draft: dict[str, object],
    content: dict[str, object],
    suffix: str,
    method: str,
) -> None:
    path = f"/professional/workout-versions/{draft['id']}{suffix}"
    body = (
        {"expected_revision": 1}
        if suffix == "/approve"
        else content | ({"expected_revision": 1} if method == "PATCH" else {})
    )
    for headers in ({}, {"Origin": "https://untrusted.example"}):
        assert client.request(method, path, headers=headers, json=body).status_code == 403
    client.cookies.clear()
    assert client.request(method, path, headers=ORIGIN, json=body).status_code == 401
    for actor in (family.master, family.student_a.user):
        login(client, actor)
        assert client.request(method, path, headers=ORIGIN, json=body).status_code == 403


def test_master_read_only(client: TestClient, family: Family, draft: dict[str, object]) -> None:
    login(client, family.master)
    for path in [
        f"/master/students/{family.student_a.id}/workouts",
        f"/master/workouts/{draft['workout_id']}",
        f"/master/workouts/{draft['workout_id']}/versions",
        f"/master/workout-versions/{draft['id']}",
    ]:
        assert client.get(path).status_code == 200
    assert (
        client.post(
            f"/master/workout-versions/{draft['id']}/approve",
            headers=ORIGIN,
            json={"expected_revision": 1},
        ).status_code
        == 404
    )


def test_concurrent_version_numbers(auth_engine: Engine) -> None:
    # Independent committed fixtures inside the disposable module schema, visible to both workers.
    from app.core.security import hash_password

    with Session(auth_engine) as db:
        owner = Professional(
            user=User(
                name="Concurrent",
                email="concurrent@example.com",
                role=UserRole.PROFESSIONAL,
                password_hash=hash_password(PASSWORD),
            )
        )
        db.add(owner)
        db.flush()
        student = make_student(owner, "concurrent-student@example.com", owner.user.password_hash)
        db.add(student)
        db.commit()
        version = service.create_workout(
            db, owner.user, student.id, VersionContent(name="Concurrent plan")
        )
        version_id, workout_id, student_id, owner_id, owner_user_id, student_user_id = (
            version.id,
            version.workout_id,
            student.id,
            owner.id,
            owner.user_id,
            student.user_id,
        )
    barrier = Barrier(2)

    def worker() -> int:
        with Session(auth_engine) as db:
            actor = db.get(User, owner_user_id)
            assert actor
            barrier.wait(timeout=10)
            return service.duplicate(db, actor, version_id).version_number

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(worker)
            b = pool.submit(worker)
            assert sorted([a.result(timeout=20), b.result(timeout=20)]) == [2, 3]
        with Session(auth_engine) as db:
            assert list(
                db.scalars(
                    select(WorkoutVersion.version_number)
                    .where(WorkoutVersion.workout_id == workout_id)
                    .order_by(WorkoutVersion.version_number)
                )
            ) == [1, 2, 3]
    finally:
        with Session(auth_engine) as db:
            db.execute(delete(WorkoutVersion).where(WorkoutVersion.workout_id == workout_id))
            db.execute(delete(Workout).where(Workout.id == workout_id))
            db.execute(delete(Student).where(Student.id == student_id))
            db.execute(delete(Professional).where(Professional.id == owner_id))
            db.execute(delete(User).where(User.id.in_([owner_user_id, student_user_id])))
            db.commit()


@pytest.mark.parametrize(
    "repetitions,load,duration",
    [
        ("10", "20 kg", None),
        ("8-12", "Peso corporal", None),
        ("falha", "Elastico medio", None),
        ("12 por lado", "Carga confortavel", None),
        (None, None, "30 segundos"),
    ],
)
def test_flexible_prescription(
    client: TestClient,
    family: Family,
    repetitions: str | None,
    load: str | None,
    duration: str | None,
) -> None:
    login(client, family.a.user)
    response = client.post(
        f"/professional/students/{family.student_a.id}/workouts",
        headers=ORIGIN,
        json={
            "name": "Plano",
            "days": [
                {
                    "name": "Mobilidade",
                    "exercises": [
                        {
                            "name": "Livre",
                            "repetitions": repetitions,
                            "load": load,
                            "duration": duration,
                        }
                    ],
                }
            ],
        },
    )
    assert response.status_code == 201
    exercise = response.json()["days"][0]["exercises"][0]
    assert (exercise["repetitions"], exercise["load"], exercise["duration"]) == (
        repetitions,
        load,
        duration,
    )


@pytest.mark.parametrize("level", ["day", "exercise"])
def test_child_ids_cannot_be_injected(
    client: TestClient, family: Family, draft: dict[str, object], db: Session, level: str
) -> None:
    version = db.get(WorkoutVersion, UUID(str(draft["id"])))
    assert version
    foreign_id = version.days[0].id if level == "day" else version.days[0].exercises[0].id
    login(client, family.b.user)
    data = VersionContent.model_validate(
        {"name": "Own", "days": [{"name": "Day", "exercises": [{"name": "Exercise"}]}]}
    ).model_dump()
    if level == "day":
        data["days"][0]["id"] = str(foreign_id)
    else:
        data["days"][0]["exercises"][0]["id"] = str(foreign_id)
    response = client.post(
        f"/professional/students/{family.student_b.id}/workouts", headers=ORIGIN, json=data
    )
    assert response.status_code == 422
    # Children have no independent routes: all reading/editing resolves the scoped version.
    for method in ("GET", "PATCH"):
        response = client.request(
            method, f"/professional/workout-{level}s/{foreign_id}", headers=ORIGIN
        )
        assert response.status_code == 404
    assert version.days[0].name == "Upper"


@pytest.mark.parametrize("resource", ["workouts", "workout-versions"])
def test_missing_resource(client: TestClient, family: Family, resource: str) -> None:
    login(client, family.a.user)
    assert client.get(f"/professional/{resource}/{uuid4()}").status_code == 404


def test_reordering_and_snapshot_edit(
    client: TestClient, family: Family, draft: dict[str, object], db: Session
) -> None:
    path = f"/professional/workout-versions/{draft['id']}"
    original = client.post(path + "/approve", headers=ORIGIN, json={"expected_revision": 1}).json()
    copy = client.post(path + "/duplicate", headers=ORIGIN).json()
    data = {key: copy[key] for key in VersionContent.model_fields}
    data["days"] = [
        {"name": "Lower", "exercises": [{"name": "Agachamento"}, {"name": "Leg press"}]},
        {"name": "Upper", "exercises": [{"name": "Rosca", "repetitions": "falha"}]},
    ]
    new_path = f"/professional/workout-versions/{copy['id']}"
    updated = client.patch(new_path, headers=ORIGIN, json=data | {"expected_revision": 1})
    assert updated.status_code == 200
    assert client.get(path).json() == original
    version = db.get(WorkoutVersion, UUID(copy["id"]))
    assert version
    assert [(day.name, day.position) for day in version.days] == [("Lower", 0), ("Upper", 1)]
    assert [(exercise.name, exercise.position) for exercise in version.days[0].exercises] == [
        ("Agachamento", 0),
        ("Leg press", 1),
    ]
    assert (
        client.post(
            new_path + "/approve", headers=ORIGIN, json={"expected_revision": 2}
        ).status_code
        == 200
    )
    login(client, family.student_a.user)
    visible = client.get("/student/workout").json()["workout"]
    assert visible["days"] == updated.json()["days"]
    assert not {"id", "user_id", "approved_by_user_id", "source"}.intersection(visible)


def test_publication_rollback(client: TestClient, draft: dict[str, object], db: Session) -> None:
    path = f"/professional/workout-versions/{draft['id']}"
    assert (
        client.post(path + "/approve", headers=ORIGIN, json={"expected_revision": 1}).status_code
        == 200
    )
    copy = client.post(path + "/duplicate", headers=ORIGIN).json()

    def fail(*args: object) -> None:
        raise IntegrityError("test", {}, Exception("test-only"))

    event.listen(WorkoutVersion, "before_update", fail)
    try:
        assert (
            client.post(
                f"/professional/workout-versions/{copy['id']}/approve",
                headers=ORIGIN,
                json={"expected_revision": 1},
            ).status_code
            == 409
        )
    finally:
        event.remove(WorkoutVersion, "before_update", fail)
    assert client.get(path).json()["status"] == "APPROVED"
    assert client.get(f"/professional/workout-versions/{copy['id']}").json()["status"] == "DRAFT"

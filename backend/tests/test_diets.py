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
    Diet,
    DietVersion,
    Food,
    Meal,
    Professional,
    Student,
    StudentStatus,
    User,
    UserRole,
)
from app.models.diet import DietSource, DietStatus
from app.models.student import ActivityLevel, Goal, TrainingExperience
from app.schemas.diet import VersionContent
from app.services import diets as service

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
        "notes": "Observacao",
        "meals": [
            {
                "name": "Refeicao livre",
                "time": "08:00",
                "foods": [
                    {
                        "name": "Alimento",
                        "quantity": "150.125",
                        "unit": "g",
                        "notes": "Nota",
                        "substitutions": [
                            {
                                "name": "Alternativa",
                                "quantity": "100",
                                "unit": "g",
                                "notes": "Orientacao",
                            },
                            {"name": "Outra alternativa"},
                        ],
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
        f"/professional/students/{family.student_a.id}/diets", headers=ORIGIN, json=content
    )
    assert result.status_code == 201, result.text
    data: dict[str, object] = result.json()
    return data


def test_creation_and_tree(
    client: TestClient, family: Family, draft: dict[str, object], db: Session
) -> None:
    assert draft["source"] == "MANUAL" and draft["status"] == "DRAFT"
    assert draft["version_number"] == 1 and draft["edit_revision"] == 1
    version = db.get(DietVersion, UUID(str(draft["id"])))
    assert version and version.created_by_user_id == family.a.user_id
    assert version.meals[0].foods[0].substitutions[1].quantity is None
    assert version.meals[0].position == 0
    assert (
        client.get(f"/professional/students/{family.student_a.id}/diets").json()[0]["id"]
        == draft["diet_id"]
    )
    assert (
        client.get(f"/professional/diets/{draft['diet_id']}/versions").json()[0]["id"]
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
            f"/professional/students/{family.student_a.id}/diets", headers=ORIGIN, json=content
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/professional/students/{student}/diets"),
        ("POST", "/professional/students/{student}/diets"),
        ("GET", "/professional/diets/{diet}"),
        ("GET", "/professional/diets/{diet}/versions"),
        ("POST", "/professional/diets/{diet}/versions"),
        ("GET", "/professional/diet-versions/{version}"),
        ("PATCH", "/professional/diet-versions/{version}"),
        ("POST", "/professional/diet-versions/{version}/duplicate"),
        ("POST", "/professional/diet-versions/{version}/approve"),
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
    url = path.format(student=family.student_a.id, diet=draft["diet_id"], version=draft["id"])
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
    path = f"/professional/diet-versions/{draft['id']}"
    original = client.get(path).json()

    def fail(*args: object) -> None:
        raise IntegrityError("test", {}, Exception("test-only"))

    event.listen(Meal, "before_insert", fail)
    try:
        response = client.patch(
            path, headers=ORIGIN, json=content | {"name": "Changed", "expected_revision": 1}
        )
        assert response.status_code == 409
    finally:
        event.remove(Meal, "before_insert", fail)
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

    event.listen(Food, "before_insert", fail)
    try:
        assert (
            client.post(
                f"/professional/students/{family.student_a.id}/diets", headers=ORIGIN, json=content
            ).status_code
            == 409
        )
    finally:
        event.remove(Food, "before_insert", fail)
    assert db.scalar(select(Diet)) is None


def test_publish_duplicate_history(
    client: TestClient,
    family: Family,
    draft: dict[str, object],
    content: dict[str, object],
    db: Session,
) -> None:
    path = f"/professional/diet-versions/{draft['id']}"
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
    assert copied["version_number"] == 2 and copied["diet_id"] == draft["diet_id"]
    assert copied["approved_at"] is None and copied["approved_by_user_id"] is None
    assert copied["meals"] == original["meals"] and copied["start_date"] == original["start_date"]
    first = db.get(DietVersion, UUID(str(draft["id"])))
    second = db.get(DietVersion, UUID(copied["id"]))
    assert first and second and first.meals[0].id != second.meals[0].id
    assert (
        client.post(
            f"/professional/diet-versions/{copied['id']}/approve",
            headers=ORIGIN,
            json={"expected_revision": 1},
        ).status_code
        == 200
    )
    archived = client.get(path).json()
    assert archived["status"] == "ARCHIVED" and archived["approved_at"] == original["approved_at"]
    assert archived["meals"] == original["meals"]
    assert (
        client.patch(path, headers=ORIGIN, json=content | {"expected_revision": 2}).status_code
        == 409
    )
    fresh = client.post(
        f"/professional/diets/{draft['diet_id']}/versions", headers=ORIGIN, json=content
    )
    assert fresh.status_code == 201 and fresh.json()["version_number"] == 3
    login(client, family.student_a.user)
    visible = client.get("/student/diet", params={"student_id": str(family.student_b.id)}).json()[
        "diet"
    ]
    assert (
        visible["version_number"] == 2
        and "source" not in visible
        and "created_by_user_id" not in visible
    )


@pytest.mark.parametrize(
    "status,source",
    [
        (DietStatus.DRAFT, DietSource.MANUAL),
        (DietStatus.PENDING_REVIEW, DietSource.MANUAL),
        (DietStatus.PENDING_REVIEW, DietSource.AI_GENERATED),
        (DietStatus.DRAFT, DietSource.AI_GENERATED),
        (DietStatus.ARCHIVED, DietSource.MANUAL),
    ],
)
def test_student_never_sees_unpublished(
    client: TestClient,
    family: Family,
    draft: dict[str, object],
    db: Session,
    status: DietStatus,
    source: DietSource,
) -> None:
    version = db.get(DietVersion, UUID(str(draft["id"])))
    assert version
    version.status = status
    version.source = source
    db.commit()
    login(client, family.student_a.user)
    assert client.get("/student/diet").json() == {"diet": None}
    assert client.get(f"/professional/diet-versions/{draft['id']}").status_code == 403


def test_student_current_across_plans(
    client: TestClient, family: Family, draft: dict[str, object], content: dict[str, object]
) -> None:
    assert (
        client.post(
            f"/professional/diet-versions/{draft['id']}/approve",
            headers=ORIGIN,
            json={"expected_revision": 1},
        ).status_code
        == 200
    )
    new = client.post(
        f"/professional/students/{family.student_a.id}/diets",
        headers=ORIGIN,
        json=content | {"name": "New plan"},
    ).json()
    assert (
        client.post(
            f"/professional/diet-versions/{new['id']}/approve",
            headers=ORIGIN,
            json={"expected_revision": 1},
        ).status_code
        == 200
    )
    assert client.get(f"/professional/diet-versions/{draft['id']}").json()["status"] == "ARCHIVED"
    login(client, family.student_b.user)
    assert client.get("/student/diet", params={"student_id": str(family.student_a.id)}).json() == {
        "diet": None
    }
    login(client, family.student_a.user)
    assert client.get("/student/diet").json()["diet"]["name"] == "New plan"


def test_review_approval_and_pending_student(
    client: TestClient, family: Family, draft: dict[str, object], db: Session
) -> None:
    version = db.get(DietVersion, UUID(str(draft["id"])))
    assert version
    version.status = DietStatus.PENDING_REVIEW
    version.source = DietSource.AI_GENERATED
    db.commit()
    assert (
        client.post(
            f"/professional/diet-versions/{draft['id']}/approve",
            headers=ORIGIN,
            json={"expected_revision": 1},
        ).status_code
        == 200
    )
    family.student_a.status = StudentStatus.PENDING_APPROVAL
    db.commit()
    login(client, family.student_a.user)
    assert client.get("/student/diet").json() == {"diet": None}


def test_invalid_content_and_publication(
    client: TestClient,
    family: Family,
    draft: dict[str, object],
    content: dict[str, object],
    db: Session,
) -> None:
    path = f"/professional/diet-versions/{draft['id']}"
    invalid_changes: list[dict[str, object]] = [
        {"name": " "},
        {"next_review_date": "2025-01-01"},
        {"meals": [{"name": "M", "foods": [{"name": "F", "quantity": 0, "unit": "g"}]}]},
        {
            "meals": [
                {
                    "name": "M",
                    "foods": [
                        {
                            "name": "F",
                            "quantity": 1,
                            "unit": "g",
                            "substitutions": [{"name": "S", "quantity": 1}],
                        }
                    ],
                }
            ]
        },
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
            path, headers=ORIGIN, json=content | {"meals": [], "expected_revision": 1}
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
    path = f"/professional/diet-versions/{draft['id']}{suffix}"
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
        f"/master/students/{family.student_a.id}/diets",
        f"/master/diets/{draft['diet_id']}",
        f"/master/diets/{draft['diet_id']}/versions",
        f"/master/diet-versions/{draft['id']}",
    ]:
        assert client.get(path).status_code == 200
    assert (
        client.post(
            f"/master/diet-versions/{draft['id']}/approve",
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
        version = service.create_diet(
            db, owner.user, student.id, VersionContent(name="Concurrent plan")
        )
        version_id, diet_id, student_id, owner_id, owner_user_id, student_user_id = (
            version.id,
            version.diet_id,
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
                    select(DietVersion.version_number)
                    .where(DietVersion.diet_id == diet_id)
                    .order_by(DietVersion.version_number)
                )
            ) == [1, 2, 3]
    finally:
        with Session(auth_engine) as db:
            db.execute(delete(DietVersion).where(DietVersion.diet_id == diet_id))
            db.execute(delete(Diet).where(Diet.id == diet_id))
            db.execute(delete(Student).where(Student.id == student_id))
            db.execute(delete(Professional).where(Professional.id == owner_id))
            db.execute(delete(User).where(User.id.in_([owner_user_id, student_user_id])))
            db.commit()

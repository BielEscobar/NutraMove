from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Professional,
    Student,
    StudentStatus,
    User,
    UserRole,
)
from app.models.assessment import Assessment
from app.models.student import ActivityLevel, Goal, TrainingExperience
from app.repositories.assessments import period_start

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


def login(client: TestClient, user: User) -> None:
    client.cookies.clear()
    assert (
        client.post(
            "/auth/login", headers=ORIGIN, json={"email": user.email, "password": PASSWORD}
        ).status_code
        == 200
    )


@pytest.fixture
def content() -> dict[str, object]:
    return {
        "assessment_date": (date.today() - timedelta(days=1)).isoformat(),
        "weight_kg": 80,
        "height_cm": 200,
        "notes": "Test-only observation",
        "measurements": [
            {"measurement_type": "ARM", "side": "LEFT", "value_cm": 30},
            {"measurement_type": "ARM", "side": "RIGHT", "value_cm": 31},
            {"measurement_type": "WAIST", "value_cm": 85},
        ],
    }


@pytest.fixture
def record(client: TestClient, family: Family, content: dict[str, object]) -> dict[str, object]:
    login(client, family.a.user)
    result = client.post(
        f"/professional/students/{family.student_a.id}/assessments", headers=ORIGIN, json=content
    )
    assert result.status_code == 201, result.text
    data: dict[str, object] = result.json()
    return data


def test_creation(
    client: TestClient, family: Family, record: dict[str, object], db: Session
) -> None:
    assert record["bmi"] == 20
    assert record["created_by_user_id"] == str(family.a.user_id)
    assert str(record["created_at"])[:10] != record["assessment_date"]
    assert family.student_a.weight == 80
    entity = db.get(Assessment, UUID(str(record["id"])))
    assert entity and len(entity.measurements) == 3
    assert "bmi" not in Assessment.__table__.columns
    assert "password_hash" not in str(record) and "token" not in str(record)
    assert (
        client.get(f"/professional/students/{family.student_a.id}/assessments").json()["total"] == 1
    )


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/professional/students/{student}/assessments"),
        ("POST", "/professional/students/{student}/assessments"),
        ("GET", "/professional/students/{student}/evolution"),
        ("GET", "/professional/assessments/{record}"),
        ("PATCH", "/professional/assessments/{record}"),
    ],
)
def test_bola(
    client: TestClient,
    family: Family,
    record: dict[str, object],
    content: dict[str, object],
    method: str,
    path: str,
) -> None:
    login(client, family.b.user)
    data = content.copy()
    if method == "PATCH":
        data.pop("assessment_date")
        data["expected_revision"] = 1
    response = client.request(
        method,
        path.format(student=family.student_a.id, record=record["id"]),
        headers=ORIGIN,
        json=data if method != "GET" else None,
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "field", ["student_id", "professional_id", "created_by_user_id", "updated_by_user_id", "role"]
)
def test_injected_fields(
    client: TestClient,
    family: Family,
    record: dict[str, object],
    content: dict[str, object],
    field: str,
) -> None:
    assert (
        client.post(
            f"/professional/students/{family.student_a.id}/assessments",
            headers=ORIGIN,
            json=content | {field: str(uuid4())},
        ).status_code
        == 422
    )
    data = {k: v for k, v in content.items() if k != "assessment_date"}
    assert (
        client.patch(
            f"/professional/assessments/{record['id']}",
            headers=ORIGIN,
            json=data | {"expected_revision": 1, field: str(uuid4())},
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "change",
    [
        {"weight_kg": 0},
        {"height_cm": -1},
        {"weight_kg": "NaN"},
        {"height_cm": 1e-100},
        {"assessment_date": (date.today() + timedelta(days=1)).isoformat()},
        {"measurements": [{"measurement_type": "FREE", "value_cm": 30}]},
        {"measurements": [{"measurement_type": "WAIST", "side": "LEFT", "value_cm": 30}]},
        {"measurements": [{"measurement_type": "ARM", "side": "LEFT", "value_cm": 0}]},
        {
            "measurements": [
                {"measurement_type": "ARM", "value_cm": 30},
                {"measurement_type": "ARM", "value_cm": 31},
            ]
        },
        {
            "measurements": [
                {"measurement_type": "ARM", "value_cm": 30},
                {"measurement_type": "ARM", "side": "LEFT", "value_cm": 31},
            ]
        },
    ],
)
def test_invalid(
    client: TestClient,
    family: Family,
    record: dict[str, object],
    content: dict[str, object],
    change: dict[str, object],
) -> None:
    assert (
        client.post(
            f"/professional/students/{family.student_a.id}/assessments",
            headers=ORIGIN,
            json=content | change,
        ).status_code
        == 422
    )


def test_current_weight_and_corrections(
    client: TestClient,
    family: Family,
    record: dict[str, object],
    content: dict[str, object],
    db: Session,
) -> None:
    path = f"/professional/students/{family.student_a.id}/assessments"
    newest = client.post(
        path,
        headers=ORIGIN,
        json=content | {"assessment_date": date.today().isoformat(), "weight_kg": 82},
    ).json()
    retro = client.post(
        path,
        headers=ORIGIN,
        json=content
        | {"assessment_date": (date.today() - timedelta(days=30)).isoformat(), "weight_kg": 85},
    ).json()
    assert family.student_a.weight == 82
    data = {k: v for k, v in content.items() if k != "assessment_date"}
    old = client.patch(
        f"/professional/assessments/{record['id']}",
        headers=ORIGIN,
        json=data | {"weight_kg": 79, "expected_revision": 1},
    )
    assert old.status_code == 200 and family.student_a.weight == 82
    assert old.json()["assessment_date"] == record["assessment_date"]
    assert (
        old.json()["created_at"] == record["created_at"]
        and old.json()["updated_at"] != record["updated_at"]
    )
    assert old.json()["edit_revision"] == 2
    target = f"/professional/assessments/{newest['id']}"
    assert (
        client.patch(
            target, headers=ORIGIN, json=data | {"weight_kg": 81, "expected_revision": 1}
        ).status_code
        == 200
    )
    assert family.student_a.weight == 81
    assert (
        client.patch(target, headers=ORIGIN, json=data | {"expected_revision": 1}).status_code
        == 409
    )
    assert (
        client.patch(
            target,
            headers=ORIGIN,
            json=data | {"assessment_date": date.today().isoformat(), "expected_revision": 2},
        ).status_code
        == 422
    )
    assert (
        client.patch(
            target, headers=ORIGIN, json=data | {"weight_kg": None, "expected_revision": 2}
        ).status_code
        == 422
    )
    assert (
        client.patch(
            f"/professional/students/{family.student_a.id}", headers=ORIGIN, json={"weight": 99}
        ).status_code
        == 409
    )
    evolution = client.get(
        f"/professional/students/{family.student_a.id}/evolution?period=all"
    ).json()
    assert [p["value"] for p in evolution["weight_history"]] == [85, 79, 81]
    assert evolution["current"]["weight_kg"] == 81 and evolution["current"]["bmi"] == 20.25
    assert client.get(f"/professional/assessments/{retro['id']}").json()["weight_kg"] == 85


@pytest.mark.parametrize("operation", ["create", "edit"])
def test_atomic(
    client: TestClient,
    family: Family,
    record: dict[str, object],
    content: dict[str, object],
    db: Session,
    operation: str,
) -> None:
    before = client.get(f"/professional/assessments/{record['id']}").json()

    def fail(*args: object) -> None:
        raise IntegrityError("test", {}, Exception("test-only"))

    # Failure when the synchronized User profile flushes, after assessment children have flushed.
    event.listen(Student, "before_update", fail)
    try:
        if operation == "create":
            response = client.post(
                f"/professional/students/{family.student_a.id}/assessments",
                headers=ORIGIN,
                json=content | {"weight_kg": 90, "assessment_date": date.today().isoformat()},
            )
        else:
            data = {k: v for k, v in content.items() if k != "assessment_date"}
            response = client.patch(
                f"/professional/assessments/{record['id']}",
                headers=ORIGIN,
                json=data | {"weight_kg": 90, "expected_revision": 1},
            )
        assert response.status_code == 409
    finally:
        event.remove(Student, "before_update", fail)
    assert family.student_a.weight == 80
    assert client.get(f"/professional/assessments/{record['id']}").json() == before
    assert len(list(db.scalars(select(Assessment)))) == 1


@pytest.mark.parametrize("period", ["7d", "30d", "90d", "6m", "1y", "all"])
def test_periods(
    client: TestClient,
    family: Family,
    record: dict[str, object],
    content: dict[str, object],
    period: str,
) -> None:
    from typing import cast

    from app.schemas.assessment import Period

    start = period_start(cast(Period, period), date.today())
    if start:
        for day in [start - timedelta(days=1), start]:
            assert (
                client.post(
                    f"/professional/students/{family.student_a.id}/assessments",
                    headers=ORIGIN,
                    json=content | {"assessment_date": day.isoformat()},
                ).status_code
                == 201
            )
    data = client.get(
        f"/professional/students/{family.student_a.id}/evolution?period={period}"
    ).json()
    assert len(data["weight_history"]) == (2 if start else 1)
    if start:
        assert all(p["date"] >= start.isoformat() for p in data["weight_history"])
    assert len(data["bmi_history"]) == len(data["weight_history"])
    assert len(data["measurements"]) == 3
    assert "notes" not in str(data)


def test_empty_and_bmi_snapshot(client: TestClient, family: Family, db: Session) -> None:
    login(client, family.a.user)
    path = f"/professional/students/{family.student_a.id}"
    empty = client.get(path + "/evolution").json()
    assert (
        empty["current"] is None and empty["weight_history"] == [] and empty["measurements"] == []
    )
    assert (
        client.post(
            path + "/assessments",
            headers=ORIGIN,
            json={"assessment_date": date.today().isoformat()},
        ).status_code
        == 422
    )
    response = client.post(
        path + "/assessments",
        headers=ORIGIN,
        json={"assessment_date": date.today().isoformat(), "weight_kg": 80},
    )
    assert response.status_code == 201 and response.json()["bmi"] is None
    family.student_a.height = 180
    db.commit()
    assert client.get(f"/professional/assessments/{response.json()['id']}").json()["bmi"] is None


def test_roles_origin_student_master(
    client: TestClient, family: Family, record: dict[str, object], content: dict[str, object]
) -> None:
    create_path = f"/professional/students/{family.student_a.id}/assessments"
    edit_path = f"/professional/assessments/{record['id']}"
    data = {k: v for k, v in content.items() if k != "assessment_date"} | {"expected_revision": 1}
    for headers in ({}, {"Origin": "https://untrusted.example"}):
        assert client.post(create_path, headers=headers, json=content).status_code == 403
        assert client.patch(edit_path, headers=headers, json=data).status_code == 403
    client.cookies.clear()
    assert client.get(edit_path).status_code == 401
    assert client.post(create_path, headers=ORIGIN, json=content).status_code == 401
    for actor in [family.master, family.student_a.user]:
        login(client, actor)
        assert client.post(create_path, headers=ORIGIN, json=content).status_code == 403
        assert client.patch(edit_path, headers=ORIGIN, json=data).status_code == 403
    own = client.get("/student/evolution", params={"student_id": str(family.student_b.id)}).json()
    assert own["current"]["weight_kg"] == 80
    own_detail = client.get(f"/student/assessments/{record['id']}").json()
    assert not {
        "created_by_user_id",
        "updated_by_user_id",
        "student_id",
        "edit_revision",
    }.intersection(own_detail)
    assert client.get("/student/assessments").json()["total"] == 1
    login(client, family.student_b.user)
    assert client.get(f"/student/assessments/{record['id']}").status_code == 404
    assert (
        client.get("/student/evolution", params={"student_id": str(family.student_a.id)}).json()[
            "current"
        ]
        is None
    )
    login(client, family.master)
    for path in [
        f"/master/students/{family.student_a.id}/assessments",
        f"/master/students/{family.student_a.id}/evolution",
        f"/master/assessments/{record['id']}",
    ]:
        assert client.get(path).status_code == 200
    assert client.patch(
        f"/master/assessments/{record['id']}", headers=ORIGIN, json=data
    ).status_code in {404, 405}


def test_same_date_stable_order(
    client: TestClient,
    family: Family,
    record: dict[str, object],
    content: dict[str, object],
    db: Session,
) -> None:
    other = client.post(
        f"/professional/students/{family.student_a.id}/assessments",
        headers=ORIGIN,
        json=content | {"weight_kg": 83},
    ).json()
    rows = list(
        db.scalars(
            select(Assessment).order_by(
                Assessment.assessment_date.desc(),
                Assessment.created_at.desc(),
                Assessment.id.desc(),
            )
        )
    )
    assert family.student_a.weight == rows[0].weight_kg
    path = f"/professional/students/{family.student_a.id}/assessments?page_size=1"
    assert client.get(path).json()["items"][0]["id"] == str(rows[0].id)
    assert client.get(path + "&page=2").json()["items"][0]["id"] == str(rows[1].id)
    assert {str(row.id) for row in rows} == {record["id"], other["id"]}

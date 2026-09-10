from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Professional, Student, StudentStatus, User, UserRole
from app.models.student import ActivityLevel, Goal, TrainingExperience

ORIGIN = {"Origin": "http://localhost:3000"}
PASSWORD = "test-only-password-2026"


@pytest.fixture
def dashboard_users(db: Session, user: User) -> tuple[User, User, User, User]:
    encoded = hash_password(PASSWORD)
    profiles = [
        Professional(
            user=User(
                name=name,
                email=f"{name}@example.com",
                password_hash=encoded,
                role=UserRole.PROFESSIONAL,
            )
        )
        for name in ("alpha", "beta")
    ]
    db.add_all(profiles)
    db.flush()
    first: User | None = None
    for index, owner in enumerate([profiles[0].id, profiles[1].id, None]):
        for status in StudentStatus:
            student_user = User(
                name=f"Student {index} {status}",
                email=f"s{index}-{status}@example.com".lower(),
                password_hash=encoded,
                role=UserRole.STUDENT,
                is_active=status != StudentStatus.INACTIVE,
            )
            student = Student(
                user=student_user,
                professional_id=owner,
                birth_date=date(1990, 1, 1),
                weight=70,
                height=175,
                goal=Goal.FITNESS,
                activity_level=ActivityLevel.MODERATE,
                training_experience=TrainingExperience.BEGINNER,
                training_frequency=3,
                status=status,
                notes="private-notes",
                food_restrictions="private-restrictions",
            )
            db.add(student)
            if first is None:
                first = student_user
    db.commit()
    assert first is not None
    return user, profiles[0].user, profiles[1].user, first


def login(client: TestClient, user: User) -> None:
    client.cookies.clear()
    assert (
        client.post(
            "/auth/login", headers=ORIGIN, json={"email": user.email, "password": PASSWORD}
        ).status_code
        == 200
    )


@pytest.mark.parametrize(
    "path", ["/master/dashboard", "/professional/dashboard", "/student/dashboard"]
)
def test_anonymous(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("index", [0, 1, 3])
@pytest.mark.parametrize(
    "path,allowed",
    [("/master/dashboard", 0), ("/professional/dashboard", 1), ("/student/dashboard", 3)],
)
def test_roles(
    client: TestClient,
    dashboard_users: tuple[User, User, User, User],
    index: int,
    path: str,
    allowed: int,
) -> None:
    login(client, dashboard_users[index])
    assert client.get(path).status_code == (200 if index == allowed else 403)


def test_master_metrics(
    client: TestClient, dashboard_users: tuple[User, User, User, User], db: Session
) -> None:
    login(client, dashboard_users[0])
    dashboard_users[2].is_active = False
    db.commit()
    response = client.get("/master/dashboard")
    assert response.json() == {
        "professionals_total": 2,
        "professionals_active": 1,
        "students_unassigned": 4,
        "students": {"total": 12, "active": 3, "pending": 3, "inactive": 3, "rejected": 3},
    }
    assert response.headers["cache-control"] == "no-store"


def test_professional_isolation(
    client: TestClient, dashboard_users: tuple[User, User, User, User]
) -> None:
    for index, label in [(1, "Student 0"), (2, "Student 1")]:
        login(client, dashboard_users[index])
        expected = client.get("/professional/dashboard").json()
        assert expected["students"] == {
            "total": 4,
            "active": 1,
            "pending": 1,
            "inactive": 1,
            "rejected": 1,
        }
        assert len(expected["recent_students"]) == 4
        assert all(item["name"].startswith(label) for item in expected["recent_students"])
        manipulated = client.get(
            "/professional/dashboard",
            params={
                "professional_id": str(dashboard_users[2].id),
                "user_id": str(uuid4()),
                "role": "MASTER",
            },
        )
        assert manipulated.json() == expected
        assert "private-" not in manipulated.text and "password" not in manipulated.text


def test_student_scope_and_minimal_response(
    client: TestClient, dashboard_users: tuple[User, User, User, User]
) -> None:
    login(client, dashboard_users[3])
    response = client.get(
        "/student/dashboard",
        params={"student_id": str(uuid4()), "user_id": str(dashboard_users[0].id)},
    )
    data = response.json()
    assert data["name"] == dashboard_users[3].name
    assert data["professional_name"] == "alpha"
    assert data["weight"] == 70 and data["height"] == 175
    assert set(data) == {
        "name",
        "status",
        "goal",
        "goal_detail",
        "weight",
        "height",
        "professional_name",
    }
    assert "private-" not in response.text and "password_hash" not in response.text


def test_empty_master(client: TestClient, user: User) -> None:
    login(client, user)
    result = client.get("/master/dashboard").json()
    assert result["professionals_total"] == 0
    assert result["students"] == {
        "total": 0,
        "active": 0,
        "pending": 0,
        "inactive": 0,
        "rejected": 0,
    }


def test_professional_without_profile(client: TestClient, user: User, db: Session) -> None:
    user.role = UserRole.PROFESSIONAL
    db.commit()
    login(client, user)
    assert client.get("/professional/dashboard").status_code == 403


def test_missing_student_profile(client: TestClient, user: User, db: Session) -> None:
    user.role = UserRole.STUDENT
    db.commit()
    login(client, user)
    assert client.get("/student/dashboard").status_code == 404


def test_queries_are_bounded(
    client: TestClient, dashboard_users: tuple[User, User, User, User], db: Session
) -> None:
    login(client, dashboard_users[1])
    statements: list[str] = []

    def capture(
        conn: object,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        many: bool,
    ) -> None:
        statements.append(statement)

    connection = db.connection()
    event.listen(connection, "before_cursor_execute", capture)
    try:
        assert client.get("/professional/dashboard").status_code == 200
    finally:
        event.remove(connection, "before_cursor_execute", capture)
    selects = [sql for sql in statements if sql.lstrip().upper().startswith("SELECT")]
    assert len(selects) <= 5
    assert any("count(" in sql for sql in selects)
    assert any("LIMIT" in sql for sql in selects)

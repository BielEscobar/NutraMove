from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import AuthSession, Professional, Student, StudentStatus, User, UserRole
from app.models.student import ActivityLevel, Goal, TrainingExperience

PASSWORD = "test-only-password-2026"
ORIGIN = {"Origin": "http://localhost:3000"}


@pytest.fixture(scope="module")
def encoded_password() -> str:
    return hash_password(PASSWORD)


@pytest.fixture
def actors(
    db: Session, user: User, encoded_password: str
) -> tuple[User, Professional, Professional]:
    professionals = []
    for label in ("a", "b"):
        professional = Professional(
            user=User(
                name=label,
                email=f"{label}@example.com",
                password_hash=encoded_password,
                role=UserRole.PROFESSIONAL,
            )
        )
        db.add(professional)
        professionals.append(professional)
    db.commit()
    return user, professionals[0], professionals[1]


@pytest.fixture
def roster(
    db: Session, actors: tuple[User, Professional, Professional], encoded_password: str
) -> list[Student]:
    items = []
    for index, professional in enumerate([actors[1], actors[2], None]):
        student = Student(
            user=User(
                name=f"Student {index}",
                email=f"student{index}@example.com",
                password_hash=encoded_password,
                role=UserRole.STUDENT,
            ),
            professional_id=professional.id if professional else None,
            birth_date=date(1990, 1, 1),
            weight=75,
            height=175,
            goal=Goal.FITNESS,
            activity_level=ActivityLevel.MODERATE,
            training_experience=TrainingExperience.BEGINNER,
            training_frequency=3,
            status=StudentStatus.PENDING_APPROVAL,
        )
        db.add(student)
        items.append(student)
    db.commit()
    return items


def login(client: TestClient, user: User) -> None:
    client.cookies.clear()
    assert (
        client.post(
            "/auth/login", headers=ORIGIN, json={"email": user.email, "password": PASSWORD}
        ).status_code
        == 200
    )


@pytest.fixture
def payload() -> dict[str, object]:
    return dict(
        name="New Student",
        email="NEW@example.com",
        password=PASSWORD,
        password_confirmation=PASSWORD,
        birth_date="2000-01-01",
        weight=70,
        height=170,
        goal="FITNESS",
        activity_level="LOW",
        training_experience="NONE",
        training_frequency=0,
    )


def test_registration(
    client: TestClient,
    db: Session,
    payload: dict[str, object],
    actors: tuple[User, Professional, Professional],
) -> None:
    payload["professional_id"] = str(actors[1].id)
    result = client.post("/students/register", headers=ORIGIN, json=payload)
    assert result.status_code == 201
    assert result.json() == {"status": "PENDING_APPROVAL"}
    student = db.scalar(select(Student))
    assert student and student.professional_id == actors[1].id
    assert student.user.role == UserRole.STUDENT and student.user.is_active
    assert student.user.email == "new@example.com"
    assert verify_password(PASSWORD, student.user.password_hash)
    assert student.user.password_hash != PASSWORD
    assert result.headers["cache-control"] == "no-store"
    login(client, student.user)
    assert client.get("/students/me").json()["status"] == "PENDING_APPROVAL"


def test_unassigned_and_duplicate(
    client: TestClient, db: Session, payload: dict[str, object]
) -> None:
    assert client.post("/students/register", headers=ORIGIN, json=payload).status_code == 201
    student = db.scalar(select(Student))
    assert student and student.professional_id is None
    assert client.post("/students/register", headers=ORIGIN, json=payload).status_code == 409


def test_atomicity(client: TestClient, db: Session, payload: dict[str, object]) -> None:
    def fail(*args: object) -> None:
        raise IntegrityError("test insert failure", {}, Exception("test"))

    event.listen(Student, "before_insert", fail)
    try:
        assert client.post("/students/register", headers=ORIGIN, json=payload).status_code == 409
    finally:
        event.remove(Student, "before_insert", fail)
    assert db.scalar(select(User).where(User.email == "new@example.com")) is None
    assert db.scalar(select(func.count()).select_from(Student)) == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("role", "MASTER"),
        ("user_id", str(uuid4())),
        ("status", "ACTIVE"),
        ("password_hash", "fake"),
        ("water_goal", 2),
        ("name", "  "),
        ("birth_date", "2999-01-01"),
        ("weight", 0),
        ("weight", "NaN"),
        ("height", -1),
        ("training_frequency", 8),
        ("training_frequency", 1.5),
        ("goal", "OTHER"),
        ("goal", "unknown"),
        ("goal_detail", "unexpected"),
        ("email", "invalid"),
        ("password_confirmation", "different-password"),
        ("notes", "x" * 2001),
        ("approximate_water_intake", -1),
    ],
)
def test_registration_validation(
    client: TestClient, db: Session, payload: dict[str, object], field: str, value: object
) -> None:
    payload[field] = value
    result = client.post("/students/register", headers=ORIGIN, json=payload)
    assert result.status_code == 422
    assert PASSWORD not in result.text


def test_other_goal(client: TestClient, db: Session, payload: dict[str, object]) -> None:
    payload.update(goal="OTHER", goal_detail="  Personal objective  ")
    assert client.post("/students/register", headers=ORIGIN, json=payload).status_code == 201
    student = db.scalar(select(Student))
    assert student and student.goal_detail == "Personal objective"


@pytest.mark.parametrize("kind", ["missing", "inactive", "wrong_role"])
def test_invalid_assignment(
    client: TestClient,
    db: Session,
    payload: dict[str, object],
    actors: tuple[User, Professional, Professional],
    kind: str,
) -> None:
    professional = actors[1]
    if kind == "inactive":
        professional.user.is_active = False
    if kind == "wrong_role":
        professional.user.role = UserRole.MASTER
    db.commit()
    payload["professional_id"] = str(uuid4() if kind == "missing" else professional.id)
    assert client.post("/students/register", headers=ORIGIN, json=payload).status_code == 422


@pytest.mark.parametrize(
    "action,source,target",
    [
        ("approve", "PENDING_APPROVAL", "ACTIVE"),
        ("reject", "PENDING_APPROVAL", "REJECTED"),
        ("activate", "INACTIVE", "ACTIVE"),
        ("deactivate", "ACTIVE", "INACTIVE"),
    ],
)
@pytest.mark.parametrize("role", ["master", "professional"])
def test_actions(
    client: TestClient,
    db: Session,
    actors: tuple[User, Professional, Professional],
    roster: list[Student],
    action: str,
    source: str,
    target: str,
    role: str,
) -> None:
    student = roster[0]
    student.status = StudentStatus(source)
    student.user.is_active = source != "INACTIVE"
    db.commit()
    login(client, actors[0] if role == "master" else actors[1].user)
    result = client.post(f"/{role}/students/{student.id}/{action}", headers=ORIGIN)
    assert result.status_code == 200
    assert result.json()["status"] == target
    assert result.json()["is_active"] == (target != "INACTIVE")
    assert result.json()["professional_id"] == str(actors[1].id)


@pytest.mark.parametrize(
    "method,suffix",
    [
        ("GET", ""),
        ("PATCH", ""),
        ("POST", "/approve"),
        ("POST", "/reject"),
        ("POST", "/activate"),
        ("POST", "/deactivate"),
    ],
)
def test_bola_every_operation(
    client: TestClient,
    actors: tuple[User, Professional, Professional],
    roster: list[Student],
    method: str,
    suffix: str,
) -> None:
    for own, other in [(1, 1), (2, 0)]:
        login(client, (actors[1], actors[2])[own - 1].user)
        result = client.request(
            method,
            f"/professional/students/{roster[other].id}{suffix}",
            headers=ORIGIN,
            json={"weight": 80} if method == "PATCH" else None,
        )
        assert result.status_code == 404
        assert (
            result.json()
            == client.request(
                method,
                f"/professional/students/{uuid4()}{suffix}",
                headers=ORIGIN,
                json={"weight": 80} if method == "PATCH" else None,
            ).json()
        )


def test_scoped_lists_search_and_filters(
    client: TestClient, actors: tuple[User, Professional, Professional], roster: list[Student]
) -> None:
    for index in (0, 1):
        login(client, (actors[1], actors[2])[index].user)
        path = "/professional/students"
        assert [item["id"] for item in client.get(path).json()["items"]] == [str(roster[index].id)]
        assert client.get(path, params={"q": roster[1 - index].user.email}).json()["total"] == 0
        assert client.get(path, params={"q": roster[index].user.email}).json()["total"] == 1
        assert client.get(path, params={"q": "%"}).json()["total"] == 0
        assert client.get(path, params={"professional_id": str(actors[2].id)}).status_code == 422
    login(client, actors[0])
    path = "/master/students"
    assert client.get(path).json()["total"] == 3
    assert client.get(path, params={"professional_id": str(actors[1].id)}).json()["total"] == 1
    assert client.get(path, params={"unassigned": "true"}).json()["items"][0]["id"] == str(
        roster[2].id
    )
    assert client.get(path, params={"status": "ACTIVE"}).json()["total"] == 0
    assert client.get(path, params={"status": "PENDING_APPROVAL"}).json()["total"] == 3
    assert len(client.get(path, params={"page_size": 1, "page": 2}).json()["items"]) == 1


def test_student_me_and_privacy(
    client: TestClient, roster: list[Student], actors: tuple[User, Professional, Professional]
) -> None:
    login(client, roster[0].user)
    result = client.get("/students/me")
    assert result.status_code == 200 and result.json()["id"] == str(roster[0].id)
    assert client.get(f"/students/{roster[1].id}").status_code == 404
    assert client.get("/students/me", params={"student_id": str(roster[1].id)}).json()["id"] == str(
        roster[0].id
    )
    for prefix in ("master", "professional"):
        assert client.get(f"/{prefix}/students/{roster[1].id}").status_code == 403
    for forbidden in ("password_hash", "password", "token", "user_id"):
        assert forbidden not in result.json()
    login(client, actors[0])
    item = client.get("/master/students").json()["items"][0]
    assert set(item) == {
        "id",
        "name",
        "email",
        "goal",
        "status",
        "professional_id",
        "professional_name",
    }


@pytest.mark.parametrize("prefix", ["master", "professional"])
@pytest.mark.parametrize(
    "method,suffix",
    [
        ("GET", ""),
        ("GET", "/id"),
        ("PATCH", "/id"),
        ("POST", "/id/approve"),
        ("POST", "/id/reject"),
        ("POST", "/id/activate"),
        ("POST", "/id/deactivate"),
    ],
)
def test_anonymous_and_wrong_role(
    client: TestClient, roster: list[Student], prefix: str, method: str, suffix: str
) -> None:
    path = f"/{prefix}/students{suffix.replace('id', str(roster[0].id))}"
    body = {"weight": 80} if method == "PATCH" else None
    assert client.request(method, path, headers=ORIGIN, json=body).status_code == 401
    login(client, roster[0].user)
    assert client.request(method, path, headers=ORIGIN, json=body).status_code == 403


def test_edit_and_injected_fields(
    client: TestClient, actors: tuple[User, Professional, Professional], roster: list[Student]
) -> None:
    login(client, actors[1].user)
    path = f"/professional/students/{roster[0].id}"
    assert (
        client.patch(path, headers=ORIGIN, json={"weight": 82.5, "water_goal": 2.5}).json()[
            "water_goal"
        ]
        == 2.5
    )
    assert (
        client.patch(path, headers=ORIGIN, json={"water_goal": None}).json()["water_goal"] is None
    )
    for body in [
        {},
        {"weight": None},
        {"birth_date": None},
        {"goal": "OTHER"},
        {"water_goal": -1},
        {"professional_id": str(actors[2].id)},
        {"user_id": str(roster[1].user_id)},
        {"role": "MASTER"},
        {"status": "ACTIVE"},
        {"is_active": False},
        {"password_hash": "fake"},
    ]:
        assert client.patch(path, headers=ORIGIN, json=body).status_code == 422
    assert client.get(path).json()["weight"] == 82.5


@pytest.mark.parametrize(
    "method,suffix",
    [
        ("PATCH", ""),
        ("POST", "/approve"),
        ("POST", "/reject"),
        ("POST", "/activate"),
        ("POST", "/deactivate"),
    ],
)
@pytest.mark.parametrize("prefix", ["master", "professional"])
def test_csrf(
    client: TestClient,
    actors: tuple[User, Professional, Professional],
    roster: list[Student],
    method: str,
    suffix: str,
    prefix: str,
) -> None:
    login(client, actors[0] if prefix == "master" else actors[1].user)
    for headers in ({}, {"Origin": "https://untrusted.example"}):
        assert (
            client.request(
                method,
                f"/{prefix}/students/{roster[0].id}{suffix}",
                headers=headers,
                json={"weight": 80} if method == "PATCH" else None,
            ).status_code
            == 403
        )


def test_public_csrf(client: TestClient, db: Session, payload: dict[str, object]) -> None:
    for headers in ({}, {"Origin": "https://untrusted.example"}):
        assert client.post("/students/register", headers=headers, json=payload).status_code == 403


def test_revocation_and_rejected_visibility(
    client: TestClient,
    db: Session,
    actors: tuple[User, Professional, Professional],
    roster: list[Student],
) -> None:
    student = roster[0]
    login(client, student.user)
    token = client.cookies.get("nutramove_session")
    login(client, actors[1].user)
    path = f"/professional/students/{student.id}"
    assert client.post(path + "/approve", headers=ORIGIN).status_code == 200
    assert client.post(path + "/deactivate", headers=ORIGIN).status_code == 200
    assert (
        db.scalar(
            select(func.count())
            .select_from(AuthSession)
            .where(AuthSession.user_id == student.user_id)
        )
        == 0
    )
    assert (
        client.post(
            "/auth/login", headers=ORIGIN, json={"email": student.user.email, "password": PASSWORD}
        ).status_code
        == 401
    )
    assert client.post(path + "/activate", headers=ORIGIN).status_code == 200
    client.cookies.clear()
    client.cookies.set("nutramove_session", str(token))
    assert client.get("/students/me").status_code == 401
    login(client, student.user)
    assert client.get("/students/me").status_code == 200
    login(client, actors[2].user)
    assert (
        client.post(f"/professional/students/{roster[1].id}/reject", headers=ORIGIN).status_code
        == 200
    )
    login(client, roster[1].user)
    assert client.get("/students/me").json()["status"] == "REJECTED"


def test_invalid_transitions(
    client: TestClient, actors: tuple[User, Professional, Professional], roster: list[Student]
) -> None:
    login(client, actors[1].user)
    path = f"/professional/students/{roster[0].id}"
    for action in ("activate", "deactivate"):
        assert client.post(f"{path}/{action}", headers=ORIGIN).status_code == 409
    assert client.post(path + "/reject", headers=ORIGIN).status_code == 200
    for action in ("approve", "activate", "deactivate", "reject"):
        assert client.post(f"{path}/{action}", headers=ORIGIN).status_code == 409


def test_missing_professional_profile(
    client: TestClient, db: Session, encoded_password: str
) -> None:
    user = User(
        name="Orphan",
        email="orphan@example.com",
        role=UserRole.PROFESSIONAL,
        password_hash=encoded_password,
    )
    db.add(user)
    db.commit()
    login(client, user)
    assert client.get("/professional/students").status_code == 403


def test_database_constraints(db: Session, roster: list[Student]) -> None:
    student = roster[0]
    for field, value in [
        ("user_id", roster[1].user_id),
        ("professional_id", uuid4()),
        ("weight", -1),
        ("height", float("nan")),
        ("training_frequency", 8),
    ]:
        with pytest.raises(IntegrityError), db.begin_nested():
            setattr(student, field, value)
            db.flush()
        db.refresh(student)

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models import AuthSession, Professional, User, UserRole

ROOT = "/master/professionals"
ORIGIN = {"Origin": "http://localhost:3000"}
PASSWORD = "test-only-password-2026"


@pytest.fixture
def master(client: TestClient, user: User) -> TestClient:
    response = client.post(
        "/auth/login", headers=ORIGIN, json={"email": user.email, "password": PASSWORD}
    )
    assert response.status_code == 200
    return client


@pytest.fixture
def payload() -> dict[str, str]:
    return {
        "name": "Ana Silva",
        "email": "ANA@example.com",
        "password": PASSWORD,
        "specialty": "Nutrição",
    }


@pytest.fixture
def professional(master: TestClient, payload: dict[str, str]) -> dict[str, object]:
    response = master.post(ROOT, headers=ORIGIN, json=payload)
    assert response.status_code == 201
    data: dict[str, object] = response.json()
    return data


def test_create(master: TestClient, payload: dict[str, str], db: Session) -> None:
    response = master.post(ROOT, headers=ORIGIN, json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "ana@example.com" and data["is_active"] is True
    assert data["specialty"] == "Nutrição"
    assert "password" not in response.text and "hash" not in response.text
    assert response.headers["cache-control"] == "no-store"
    user = db.get(User, UUID(data["user_id"]))
    assert user and user.role == UserRole.PROFESSIONAL
    assert verify_password(PASSWORD, user.password_hash)
    assert db.scalar(select(func.count()).select_from(Professional)) == 1


def test_list_detail_and_summary(master: TestClient, professional: dict[str, object]) -> None:
    response = master.get(ROOT)
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"] == [professional]
    assert master.get(f"{ROOT}/{professional['id']}").json() == professional
    assert master.get(f"{ROOT}/summary").json() == {"total": 1, "active": 1, "inactive": 0}
    assert "password_hash" not in response.text


def test_edit(master: TestClient, professional: dict[str, object], db: Session) -> None:
    response = master.patch(
        f"{ROOT}/{professional['id']}",
        headers=ORIGIN,
        json={"name": "Ana Costa", "email": "NOVA@example.com", "specialty": None},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Ana Costa" and data["email"] == "nova@example.com"
    assert data["specialty"] is None and data["id"] == professional["id"]
    user = db.get(User, UUID(str(professional["user_id"])))
    assert user and user.role == UserRole.PROFESSIONAL and user.is_active


def test_deactivate_reactivate_revokes_all_sessions(
    master: TestClient, professional: dict[str, object], db: Session
) -> None:
    # Independent browser sessions for the target professional.
    cookies = []
    for _ in range(2):
        with TestClient(master.app) as browser:
            response = browser.post(
                "/auth/login",
                headers=ORIGIN,
                json={"email": professional["email"], "password": PASSWORD},
            )
            assert response.status_code == 200
            cookies.append(browser.cookies.get("nutramove_session"))
    target = UUID(str(professional["user_id"]))
    assert (
        db.scalar(
            select(func.count()).select_from(AuthSession).where(AuthSession.user_id == target)
        )
        == 2
    )
    path = f"{ROOT}/{professional['id']}"
    assert master.post(f"{path}/deactivate", headers=ORIGIN).json()["is_active"] is False
    assert db.get(Professional, UUID(str(professional["id"]))) is not None
    assert (
        db.scalar(
            select(func.count()).select_from(AuthSession).where(AuthSession.user_id == target)
        )
        == 0
    )
    with TestClient(master.app) as browser:
        assert (
            browser.post(
                "/auth/login",
                headers=ORIGIN,
                json={"email": professional["email"], "password": PASSWORD},
            ).status_code
            == 401
        )
    assert master.post(f"{path}/activate", headers=ORIGIN).json()["is_active"] is True
    for token in cookies:
        with TestClient(master.app) as browser:
            assert (
                browser.get(
                    "/auth/me", headers={"Cookie": f"nutramove_session={token}"}
                ).status_code
                == 401
            )
    with TestClient(master.app) as browser:
        assert (
            browser.post(
                "/auth/login",
                headers=ORIGIN,
                json={"email": professional["email"], "password": PASSWORD},
            ).status_code
            == 200
        )


def test_search_status_pagination(
    master: TestClient, professional: dict[str, object], payload: dict[str, str]
) -> None:
    payload.update(name="Bruno Lima", email="bruno@example.com", specialty="Treinamento")
    second = master.post(ROOT, headers=ORIGIN, json=payload).json()
    master.post(f"{ROOT}/{second['id']}/deactivate", headers=ORIGIN)
    for query in ["ANA", "ana@example", "Nutrição"]:
        response = master.get(ROOT, params={"q": query})
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["id"] == professional["id"]
    assert master.get(ROOT, params={"q": "%"}).json()["total"] == 0
    assert master.get(ROOT, params={"is_active": False}).json()["items"][0]["id"] == second["id"]
    page = master.get(ROOT, params={"page": 2, "page_size": 1}).json()
    assert page["total"] == 2 and page["items"][0]["id"] == second["id"]
    assert master.get(ROOT, params={"page": 10}).json()["items"] == []
    assert master.get(f"{ROOT}/summary").json() == {"total": 2, "active": 1, "inactive": 1}


@pytest.mark.parametrize("role", [None, UserRole.PROFESSIONAL, UserRole.STUDENT])
@pytest.mark.parametrize(
    "method,suffix",
    [
        ("GET", ""),
        ("GET", "/summary"),
        ("POST", ""),
        ("GET", "/{id}"),
        ("PATCH", "/{id}"),
        ("POST", "/{id}/activate"),
        ("POST", "/{id}/deactivate"),
    ],
)
def test_all_endpoints_require_master(
    client: TestClient,
    user: User,
    db: Session,
    role: UserRole | None,
    method: str,
    suffix: str,
    payload: dict[str, str],
) -> None:
    if role is not None:
        user.role = role
        db.commit()
        assert (
            client.post(
                "/auth/login", headers=ORIGIN, json={"email": user.email, "password": PASSWORD}
            ).status_code
            == 200
        )
    response = client.request(
        method,
        ROOT + suffix.replace("{id}", str(uuid4())),
        headers={**ORIGIN, "X-Role": "MASTER"},
        json=payload,
    )
    assert response.status_code == (401 if role is None else 403)


def test_duplicate_email(
    master: TestClient, professional: dict[str, object], payload: dict[str, str], db: Session
) -> None:
    response = master.post(ROOT, headers=ORIGIN, json=payload)
    assert response.status_code == 409
    assert db.scalar(select(func.count()).select_from(Professional)) == 1
    assert (
        master.patch(
            f"{ROOT}/{professional['id']}", headers=ORIGIN, json={"email": "master@example.com"}
        ).status_code
        == 409
    )
    assert master.get(f"{ROOT}/{professional['id']}").json()["email"] == professional["email"]


def test_creation_rolls_back_user_on_profile_failure(
    master: TestClient, payload: dict[str, str], db: Session
) -> None:
    def fail_insert(*args: object) -> None:
        raise IntegrityError("simulated profile failure", None, Exception("test"))

    event.listen(Professional, "before_insert", fail_insert)
    try:
        assert master.post(ROOT, headers=ORIGIN, json=payload).status_code == 409
    finally:
        event.remove(Professional, "before_insert", fail_insert)
    assert db.scalar(select(User).where(User.email == "ana@example.com")) is None
    assert db.scalar(select(func.count()).select_from(Professional)) == 0


@pytest.mark.parametrize(
    "extra",
    [
        {"role": "MASTER"},
        {"user_id": str(uuid4())},
        {"is_active": False},
        {"password_hash": "fake"},
    ],
)
def test_create_rejects_authorization_fields(
    master: TestClient, payload: dict[str, str], extra: dict[str, object]
) -> None:
    response = master.post(ROOT, headers=ORIGIN, json={**payload, **extra})
    assert response.status_code == 422
    assert PASSWORD not in response.text


@pytest.mark.parametrize(
    "change",
    [
        {},
        {"name": None},
        {"email": None},
        {"name": " "},
        {"email": "invalid"},
        {"password": PASSWORD},
        {"role": "MASTER"},
        {"is_active": False},
        {"user_id": str(uuid4())},
    ],
)
def test_update_validation(
    master: TestClient, professional: dict[str, object], change: dict[str, object]
) -> None:
    assert (
        master.patch(f"{ROOT}/{professional['id']}", headers=ORIGIN, json=change).status_code == 422
    )


@pytest.mark.parametrize(
    "method,suffix",
    [("POST", ""), ("PATCH", "/{id}"), ("POST", "/{id}/activate"), ("POST", "/{id}/deactivate")],
)
def test_mutations_require_trusted_origin(
    master: TestClient, payload: dict[str, str], method: str, suffix: str
) -> None:
    response = master.request(
        method,
        ROOT + suffix.replace("{id}", str(uuid4())),
        json=payload,
        headers={"Origin": "https://attacker.example"},
    )
    assert response.status_code == 403


def test_patch_preflight(client: TestClient) -> None:
    response = client.options(
        ROOT + "/" + str(uuid4()),
        headers={
            **ORIGIN,
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-credentials"] == "true"


@pytest.mark.parametrize(
    "method,suffix", [("GET", ""), ("PATCH", ""), ("POST", "/activate"), ("POST", "/deactivate")]
)
def test_missing_professional(master: TestClient, method: str, suffix: str) -> None:
    assert (
        master.request(
            method, f"{ROOT}/{uuid4()}{suffix}", headers=ORIGIN, json={"name": "Missing"}
        ).status_code
        == 404
    )


def test_unique_user_constraint(db: Session, professional: dict[str, object]) -> None:
    db.add(Professional(user_id=UUID(str(professional["user_id"]))))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_foreign_key_constraint(db: Session) -> None:
    db.add(Professional(user_id=uuid4()))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_create_validation(master: TestClient, payload: dict[str, str]) -> None:
    for field, invalid in [("name", " "), ("email", "invalid"), ("password", "short")]:
        assert (
            master.post(ROOT, headers=ORIGIN, json={**payload, field: invalid}).status_code == 422
        )

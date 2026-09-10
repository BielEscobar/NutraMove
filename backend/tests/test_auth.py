from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import uuid4

import pytest
from alembic.config import Config
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from app.api.dependencies import require_roles
from app.core.config import BACKEND_DIR, get_settings
from app.core.security import hash_password, token_digest, verify_password
from app.db.session import get_db
from app.models import AuthSession, User, UserRole
from app.schemas.auth import MasterCreate
from app.services.auth import create_master

ORIGIN = {"Origin": "http://localhost:3000"}
PASSWORD = "test-only-password-2026"


@pytest.fixture(scope="module")
def auth_engine() -> Iterator[Engine]:
    # Only this generated schema is created/dropped. Existing tables are never touched.
    schema = "test_auth_" + uuid4().hex
    url = str(get_settings().database_url)
    control = create_engine(url, connect_args={"connect_timeout": 5})
    with control.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(
        url, connect_args={"options": f"-csearch_path={schema}", "connect_timeout": 5}
    )
    try:
        config = Config(str(BACKEND_DIR / "alembic.ini"))
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            command.check(config)
        yield engine
        # Verify downgrade and upgrade only in the disposable test schema.
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.downgrade(config, "base")
            command.upgrade(config, "head")
            command.check(config)
    finally:
        engine.dispose()
        with control.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        control.dispose()


@pytest.fixture
def db(auth_engine: Engine, app: FastAPI) -> Iterator[Session]:
    with auth_engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:

            def override_db() -> Iterator[Session]:
                yield session

            app.dependency_overrides[get_db] = override_db
            yield session
        transaction.rollback()
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def user(db: Session) -> User:
    user = User(
        name="Test Master",
        email="master@example.com",
        password_hash=hash_password(PASSWORD),
        role=UserRole.MASTER,
    )
    db.add(user)
    db.commit()
    return user


def sign_in(client: TestClient, email: str = "master@example.com") -> None:
    response = client.post(
        "/auth/login", headers=ORIGIN, json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200


def test_login_me_logout(client: TestClient, user: User, db: Session) -> None:
    response = client.post(
        "/auth/login", headers=ORIGIN, json={"email": "MASTER@example.com", "password": PASSWORD}
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)
    assert response.json()["role"] == "MASTER"
    assert "password" not in response.text
    assert "hash" not in response.text
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert response.headers["cache-control"] == "no-store"
    token = client.cookies.get("nutramove_session")
    assert token
    session = db.scalar(select(AuthSession))
    assert session and session.token_hash == token_digest(token)
    assert session.token_hash != token
    assert client.get("/auth/me").json()["email"] == user.email
    assert client.post("/auth/logout", headers=ORIGIN).status_code == 204
    assert client.get("/auth/me").status_code == 401
    assert (
        client.get("/auth/me", headers={"Cookie": f"nutramove_session={token}"}).status_code == 401
    )
    assert db.scalar(select(AuthSession)) is None


@pytest.mark.parametrize(
    "email,password",
    [
        ("master@example.com", "incorrect"),
        ("unknown@example.com", PASSWORD),
    ],
)
def test_invalid_credentials(client: TestClient, user: User, email: str, password: str) -> None:
    response = client.post(
        "/auth/login", headers=ORIGIN, json={"email": email, "password": password}
    )
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "E-mail ou senha inválidos."
    assert "set-cookie" not in response.headers


def test_inactive_user_cannot_login(client: TestClient, user: User, db: Session) -> None:
    user.is_active = False
    db.commit()
    response = client.post(
        "/auth/login", headers=ORIGIN, json={"email": user.email, "password": PASSWORD}
    )
    assert response.status_code == 401


def test_deactivation_invalidates_access(client: TestClient, user: User, db: Session) -> None:
    sign_in(client)
    user.is_active = False
    db.commit()
    assert client.get("/auth/me").status_code == 401


def test_expired_session(client: TestClient, user: User, db: Session) -> None:
    sign_in(client)
    session = db.scalar(select(AuthSession))
    assert session
    session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    assert client.get("/auth/me").status_code == 401


@pytest.mark.parametrize("token", ["invalid", "a" * 43])
def test_unknown_session(client: TestClient, db: Session, token: str) -> None:
    assert (
        client.get("/auth/me", headers={"Cookie": f"nutramove_session={token}"}).status_code == 401
    )


def test_anonymous(client: TestClient, db: Session) -> None:
    assert client.get("/auth/me").status_code == 401


@pytest.mark.parametrize("origin", [None, "https://attacker.example", "null"])
@pytest.mark.parametrize("path", ["/auth/login", "/auth/logout"])
def test_csrf(client: TestClient, origin: str | None, path: str) -> None:
    response = client.post(
        path,
        headers={"Origin": origin} if origin else {},
        json={"email": "master@example.com", "password": PASSWORD},
    )
    assert response.status_code == 403


def test_credentialed_cors(client: TestClient) -> None:
    response = client.options(
        "/auth/login",
        headers={
            **ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-credentials"] == "true"


def test_role_and_id_injection_rejected(client: TestClient, db: Session) -> None:
    response = client.post(
        "/auth/login",
        headers=ORIGIN,
        json={
            "email": "master@example.com",
            "password": PASSWORD,
            "role": "MASTER",
            "user_id": str(uuid4()),
        },
    )
    assert response.status_code == 422
    assert PASSWORD not in response.text


@pytest.mark.parametrize(
    "role,expected", [(UserRole.MASTER, 200), (UserRole.PROFESSIONAL, 403), (UserRole.STUDENT, 403)]
)
def test_role_authorization(
    app: FastAPI, client: TestClient, user: User, db: Session, role: UserRole, expected: int
) -> None:
    @app.get("/test-master")
    def master_only(
        current: Annotated[User, Depends(require_roles(UserRole.MASTER))],
    ) -> dict[str, str]:
        return {"id": str(current.id)}

    assert client.get("/test-master").status_code == 401
    sign_in(client)
    # A changed database role must take effect even with an existing cookie.
    user.role = role
    db.commit()
    response = client.get(
        "/test-master",
        headers={"X-Role": "MASTER"},
        params={"role": "MASTER", "user_id": str(uuid4())},
    )
    assert response.status_code == expected


def test_login_rotates_session(client: TestClient, user: User, db: Session) -> None:
    sign_in(client)
    previous = client.cookies.get("nutramove_session")
    sign_in(client)
    assert previous != client.cookies.get("nutramove_session")
    assert (
        db.scalar(select(AuthSession).where(AuthSession.token_hash == token_digest(str(previous))))
        is None
    )


def test_master_bootstrap_hash_and_duplicate_email(db: Session) -> None:
    data = MasterCreate.model_validate(
        {"name": "Admin", "email": "ADMIN@example.com", "password": PASSWORD}
    )
    user = create_master(db, data)
    assert user.role == UserRole.MASTER and user.email == "admin@example.com"
    assert user.password_hash != PASSWORD
    assert verify_password(PASSWORD, user.password_hash)
    with pytest.raises(ValueError, match="E-mail"):
        create_master(db, data)


def test_email_database_constraint(user: User, db: Session) -> None:
    db.add(
        User(name="Duplicate", email=user.email, password_hash="unused", role=UserRole.PROFESSIONAL)
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_logout_is_idempotent(client: TestClient, db: Session) -> None:
    assert client.post("/auth/logout", headers=ORIGIN).status_code == 204

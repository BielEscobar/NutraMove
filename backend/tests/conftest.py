from collections.abc import Iterator
from uuid import uuid4

import pytest
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import PostgresDsn
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import BACKEND_DIR, Settings, get_settings
from app.core.security import hash_password
from app.db.session import get_db
from app.main import create_app
from app.models import User, UserRole

PASSWORD = "test-only-password-2026"


@pytest.fixture
def app() -> FastAPI:
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url=PostgresDsn("postgresql+psycopg://test:test@localhost/test"),
        cors_origins=["http://localhost:3000"],
    )
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


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

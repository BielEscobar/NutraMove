from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import PostgresDsn

from app.core.config import Settings
from app.main import create_app


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

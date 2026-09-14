import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from pydantic import PostgresDsn, ValidationError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import unexpected_error_handler
from app.core.rate_limit import consume
from app.main import create_app
from app.models import User

ORIGIN = {"Origin": "http://localhost:3000"}
PASSWORD = "test-only-password-2026"


def test_rate_window_resets_and_returns_429(db: Session, app: FastAPI) -> None:
    settings = app.dependency_overrides[get_settings]()
    start = datetime(2026, 9, 13, tzinfo=UTC)
    consume(db, settings, "unit", "one", limit=2, period_seconds=60, now=start)
    consume(
        db, settings, "unit", "one", limit=2, period_seconds=60, now=start + timedelta(seconds=1)
    )
    with pytest.raises(HTTPException) as error:
        consume(
            db,
            settings,
            "unit",
            "one",
            limit=2,
            period_seconds=60,
            now=start + timedelta(seconds=2),
        )
    assert error.value.status_code == 429
    assert error.value.headers == {"Retry-After": "60"}
    consume(
        db, settings, "unit", "one", limit=2, period_seconds=60, now=start + timedelta(seconds=61)
    )
    consume(
        db, settings, "unit", "two", limit=2, period_seconds=60, now=start + timedelta(seconds=61)
    )


def test_login_limit_does_not_block_other_routes(
    client: TestClient, db: Session, app: FastAPI, user: User
) -> None:
    settings = app.dependency_overrides[get_settings]()
    for _ in range(10):
        consume(db, settings, "login", "testclient", limit=10, period_seconds=300)
    response = client.post(
        "/auth/login", headers=ORIGIN, json={"email": user.email, "password": PASSWORD}
    )
    assert response.status_code == 429
    assert response.headers["retry-after"] == "300"
    assert "password" not in response.text
    assert client.get("/health").status_code == 200


def test_registration_limit(client: TestClient, db: Session, app: FastAPI) -> None:
    settings = app.dependency_overrides[get_settings]()
    for _ in range(5):
        consume(db, settings, "register", "testclient", limit=5, period_seconds=3600)
    response = client.post(
        "/students/register",
        headers=ORIGIN,
        json={
            "name": "Test",
            "email": "new@example.com",
            "password": PASSWORD,
            "password_confirmation": PASSWORD,
            "birth_date": "2000-01-01",
            "weight": 70,
            "height": 170,
            "goal": "FITNESS",
            "activity_level": "LOW",
            "training_experience": "NONE",
            "training_frequency": 0,
        },
    )
    assert response.status_code == 429
    assert response.headers["cache-control"] == "no-store"


def test_security_headers_cover_success_and_errors(client: TestClient) -> None:
    for path, status in (("/health", 200), ("/auth/me", 401), ("/missing", 404)):
        response = client.get(path)
        assert response.status_code == status
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["content-security-policy"] == "frame-ancestors 'none'"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["cache-control"] == "no-store"
        assert "strict-transport-security" not in response.headers


def test_production_settings_and_docs() -> None:
    kwargs: dict[str, Any] = dict(
        _env_file=None,
        environment="production",
        database_url=PostgresDsn("postgresql+psycopg://test:test@localhost/test"),
        cookie_secure=True,
        cors_origins=["https://app.example.com"],
        rate_limit_secret="test-only-secret-with-at-least-32-characters",
    )
    settings = Settings(**kwargs)
    assert not settings.docs_available
    with TestClient(create_app(settings), base_url="https://testserver") as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404
        assert client.get("/health").headers["strict-transport-security"] == "max-age=31536000"
    with pytest.raises(ValidationError):
        Settings(**(kwargs | {"cors_origins": ["https://localhost:3000"]}))
    with pytest.raises(ValidationError):
        Settings(**(kwargs | {"rate_limit_secret": "short"}))
    with pytest.raises(ValidationError):
        Settings(**(kwargs | {"ai_enabled": True}))


def test_unexpected_error_does_not_log_sensitive_values(
    caplog: pytest.LogCaptureFixture,
) -> None:
    request = Request({"type": "http", "method": "GET", "path": "/test", "headers": []})
    response = asyncio.run(unexpected_error_handler(request, ValueError("secret-value")))
    assert response.status_code == 500
    assert b"secret-value" not in response.body
    assert "secret-value" not in caplog.text
    assert "locations=" not in caplog.text

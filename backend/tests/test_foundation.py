import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_not_found(client: TestClient) -> None:
    response = client.get("/missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_error"


def test_cors_allowed_origin(client: TestClient) -> None:
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_rejects_unknown_origin(client: TestClient) -> None:
    response = client.options(
        "/health",
        headers={"Origin": "https://unknown.example", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_validation_does_not_echo_input(app: FastAPI, client: TestClient) -> None:
    @app.get("/test-validation")
    def validation_endpoint(value: int) -> dict[str, int]:
        return {"value": value}

    response = client.get("/test-validation", params={"value": "private-value"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "private-value" not in response.text


def test_unexpected_error_hides_details(app: FastAPI, client: TestClient) -> None:
    @app.get("/test-error")
    def failing_endpoint() -> None:
        raise RuntimeError("private implementation detail")

    response = client.get("/test-error")
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "Internal server error."}
    }


def test_http_error_preserves_headers(app: FastAPI, client: TestClient) -> None:
    @app.get("/test-unavailable")
    def unavailable_endpoint() -> None:
        raise HTTPException(503, "Unavailable", headers={"Retry-After": "30"})

    response = client.get("/test-unavailable")
    assert response.status_code == 503
    assert response.headers["retry-after"] == "30"


def test_unexpected_error_does_not_log_personal_data(
    app: FastAPI, client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    secret = "person@example.test private-profile"

    @app.get("/test-sensitive-error")
    def sensitive_error() -> None:
        raise RuntimeError(secret)

    response = client.get("/test-sensitive-error", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 500
    assert secret not in caplog.text
    assert "RuntimeError" in caplog.text
    assert "sensitive_error" not in caplog.text
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"

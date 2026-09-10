import pytest
from pydantic import PostgresDsn, ValidationError

from app.core.config import Settings


@pytest.mark.parametrize("origin", ["*", "https://*.example.com", "https://site.example/path"])
def test_rejects_unsafe_origins(origin: str) -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url=PostgresDsn("postgresql+psycopg://test:test@localhost/test"),
            cors_origins=[origin],
        )


def test_production_requires_secure_cookie() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            database_url=PostgresDsn("postgresql+psycopg://test:test@localhost/test"),
            cookie_secure=False,
            cors_origins=["https://app.example.com"],
        )


def test_production_requires_https_origin() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            database_url=PostgresDsn("postgresql+psycopg://test:test@localhost/test"),
            cookie_secure=True,
            cors_origins=["http://app.example.com"],
        )


def test_secure_cookie_name() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        database_url=PostgresDsn("postgresql+psycopg://test:test@localhost/test"),
        cookie_secure=True,
        cors_origins=["https://app.example.com"],
    )
    assert settings.session_cookie_name == "__Host-nutramove_session"

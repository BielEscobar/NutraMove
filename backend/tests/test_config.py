import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_read_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost/test")
    monkeypatch.setenv("APP_NAME", "Test API")
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:4000"]')
    settings = Settings(_env_file=None)
    assert settings.app_name == "Test API"
    assert settings.cors_origins == ["http://localhost:4000"]


@pytest.mark.parametrize("url", ["sqlite:///test.db", "postgresql://test:test@localhost/test"])
def test_settings_require_postgresql_psycopg(monkeypatch: pytest.MonkeyPatch, url: str) -> None:
    monkeypatch.setenv("DATABASE_URL", url)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)

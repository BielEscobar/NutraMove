from functools import lru_cache
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, PostgresDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "NUTRAMOVE API"
    environment: Literal["development", "test", "production"] = "development"
    database_url: PostgresDsn
    cors_origins: list[str] = ["http://localhost:3000"]
    session_seconds: int = Field(default=3600, ge=300, le=604800)
    cookie_secure: bool = False
    business_timezone: str = "America/Sao_Paulo"

    @field_validator("business_timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Use a valid IANA timezone.") from None
        return value

    @property
    def session_cookie_name(self) -> str:
        return "__Host-nutramove_session" if self.cookie_secure else "nutramove_session"

    @field_validator("database_url")
    @classmethod
    def require_psycopg(cls, value: PostgresDsn) -> PostgresDsn:
        if value.scheme != "postgresql+psycopg":
            raise ValueError("DATABASE_URL must use postgresql+psycopg://")
        return value

    @field_validator("cors_origins")
    @classmethod
    def explicit_origins(cls, values: list[str]) -> list[str]:
        if not values:
            raise ValueError("At least one frontend origin is required.")
        for value in values:
            parsed = urlsplit(value)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or "*" in value
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
                or parsed.password
            ):
                raise ValueError(
                    "CORS_ORIGINS must contain explicit HTTP(S) origins without paths."
                )
        return values

    @model_validator(mode="after")
    def production_security(self) -> Self:
        if self.environment == "production":
            if not self.cookie_secure or any(
                not origin.startswith("https://") for origin in self.cors_origins
            ):
                raise ValueError(
                    "Production requires COOKIE_SECURE=true and HTTPS frontend origins."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)


class ProfessionalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: SecretStr = Field(min_length=12, max_length=128)
    specialty: str | None = Field(default=None, max_length=120)

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name is required.")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("specialty")
    @classmethod
    def normalize_specialty(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class ProfessionalUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    email: EmailStr | None = None
    specialty: str | None = Field(default=None, max_length=120)

    @field_validator("name", "email")
    @classmethod
    def required_when_provided(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("This field cannot be null or blank.")
        return value.strip()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("specialty")
    @classmethod
    def normalize_specialty(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @model_validator(mode="after")
    def nonempty_update(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Provide at least one field.")
        return self


class ProfessionalResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    email: str
    specialty: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProfessionalList(BaseModel):
    items: list[ProfessionalResponse]
    total: int
    page: int
    page_size: int


class ProfessionalSummary(BaseModel):
    total: int
    active: int
    inactive: int

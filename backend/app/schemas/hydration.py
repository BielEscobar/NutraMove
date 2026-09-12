from datetime import UTC, date, datetime, timedelta
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

HydrationPeriod = Literal[1, 7, 30]


class WaterCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount_ml: int = Field(strict=True, ge=1, le=10000)
    consumed_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("consumed_at")
    @classmethod
    def not_future(cls, value: datetime) -> datetime:
        if value > datetime.now(UTC) + timedelta(minutes=5):
            raise ValueError("O horário não pode estar mais de cinco minutos no futuro.")
        return value


class WaterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    amount_ml: int
    consumed_at: datetime
    created_at: datetime


class HydrationSummary(BaseModel):
    date: date
    timezone: str
    consumed_ml: int
    goal_ml: int | None
    remaining_ml: int | None
    percentage: float | None


class HydrationDay(HydrationSummary):
    records: list[WaterResponse]
    total_records: int
    page: int
    page_size: int


class HydrationPoint(BaseModel):
    date: date
    consumed_ml: int


class HydrationHistory(BaseModel):
    timezone: str
    days: int
    items: list[HydrationPoint]

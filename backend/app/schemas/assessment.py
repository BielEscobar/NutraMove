from datetime import date, datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from app.models.assessment import MeasurementSide, MeasurementType

Period = Literal["7d", "30d", "90d", "6m", "1y", "all"]
Positive = Annotated[float, Field(ge=0.1, le=10000, allow_inf_nan=False)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, from_attributes=True)


class MeasurementInput(InputModel):
    measurement_type: MeasurementType
    side: MeasurementSide | None = None
    value_cm: Positive
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def valid_side(self) -> Self:
        if self.side and self.measurement_type not in {
            MeasurementType.ARM,
            MeasurementType.THIGH,
            MeasurementType.CALF,
        }:
            raise ValueError("Laterality applies only to arms, thighs and calves.")
        return self


class AssessmentContent(InputModel):
    weight_kg: Positive | None = None
    height_cm: Positive | None = None
    notes: str | None = Field(default=None, max_length=4000)
    measurements: list[MeasurementInput] = Field(default_factory=list, max_length=13)

    @model_validator(mode="after")
    def valid_content(self) -> Self:
        if (
            self.weight_kg is None
            and self.height_cm is None
            and not self.measurements
            and not self.notes
        ):
            raise ValueError("Provide at least one observation or measurement.")
        keys = [(m.measurement_type, m.side) for m in self.measurements]
        if len(keys) != len(set(keys)):
            raise ValueError("Repeated measurement type and side.")
        for kind in MeasurementType:
            sides = {m.side for m in self.measurements if m.measurement_type == kind}
            if None in sides and len(sides) > 1:
                raise ValueError("Use either unspecified or explicit sides for a measurement type.")
        return self


class AssessmentCreate(AssessmentContent):
    assessment_date: date

    @field_validator("assessment_date")
    @classmethod
    def not_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Assessment date cannot be in the future.")
        return value


class AssessmentUpdate(AssessmentContent):
    expected_revision: int = Field(ge=1, strict=True)


def bmi(weight: float | None, height: float | None) -> float | None:
    if weight is None or height is None:
        return None
    return round(weight / (height / 100) ** 2, 2)


class AssessmentBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    assessment_date: date
    weight_kg: float | None
    height_cm: float | None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]  # Pydantic wraps the property at runtime.
    @property
    def bmi(self) -> float | None:
        return bmi(self.weight_kg, self.height_cm)


class AssessmentResponse(AssessmentBrief):
    notes: str | None
    measurements: list[MeasurementInput]


class StaffAssessmentResponse(AssessmentResponse):
    student_id: UUID
    created_by_user_id: UUID
    updated_by_user_id: UUID
    edit_revision: int


class AssessmentList(BaseModel):
    items: list[AssessmentBrief]
    total: int
    page: int
    page_size: int


class HistoryPoint(BaseModel):
    assessment_id: UUID
    date: date
    value: float


class MeasurementSeries(BaseModel):
    measurement_type: MeasurementType
    side: MeasurementSide | None
    points: list[HistoryPoint]


class EvolutionCurrent(BaseModel):
    latest_assessment_date: date
    weight_kg: float | None
    weight_date: date | None
    bmi: float | None


class EvolutionResponse(BaseModel):
    current: EvolutionCurrent | None
    weight_history: list[HistoryPoint]
    bmi_history: list[HistoryPoint]
    measurements: list[MeasurementSeries]
    period: Period

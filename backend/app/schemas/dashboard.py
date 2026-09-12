from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.student import Goal, StudentStatus


class StudentMetrics(BaseModel):
    total: int
    active: int
    pending: int
    inactive: int
    rejected: int


class MasterDashboard(BaseModel):
    professionals_total: int
    professionals_active: int
    students: StudentMetrics
    students_unassigned: int


class RecentStudent(BaseModel):
    id: UUID
    name: str
    status: StudentStatus
    created_at: datetime


class ProfessionalDashboard(BaseModel):
    reevaluations_pending: int
    reevaluations_in_review: int
    students: StudentMetrics
    recent_students: list[RecentStudent]


class StudentDashboard(BaseModel):
    name: str
    status: StudentStatus
    goal: Goal
    goal_detail: str | None
    weight: float
    height: float
    professional_name: str | None

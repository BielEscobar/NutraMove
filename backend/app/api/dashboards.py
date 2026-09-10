from fastapi import APIRouter, Depends

from app.api.dependencies import CurrentUser, DbSession, require_roles
from app.api.professionals import no_cache
from app.models import UserRole
from app.repositories import dashboards, professionals
from app.schemas.dashboard import MasterDashboard, ProfessionalDashboard, StudentDashboard
from app.services.students import get

router = APIRouter(tags=["dashboards"], dependencies=[Depends(no_cache)])


@router.get(
    "/master/dashboard",
    response_model=MasterDashboard,
    dependencies=[Depends(require_roles(UserRole.MASTER))],
)
def master_dashboard(db: DbSession, actor: CurrentUser) -> MasterDashboard:
    metrics, unassigned = dashboards.student_metrics(db, actor)
    total, active = professionals.summary(db)
    return MasterDashboard(
        professionals_total=total,
        professionals_active=active,
        students=metrics,
        students_unassigned=unassigned,
    )


@router.get(
    "/professional/dashboard",
    response_model=ProfessionalDashboard,
    dependencies=[Depends(require_roles(UserRole.PROFESSIONAL))],
)
def professional_dashboard(db: DbSession, actor: CurrentUser) -> ProfessionalDashboard:
    metrics, _ = dashboards.student_metrics(db, actor)
    return ProfessionalDashboard(
        students=metrics, recent_students=dashboards.recent_students(db, actor)
    )


@router.get(
    "/student/dashboard",
    response_model=StudentDashboard,
    dependencies=[Depends(require_roles(UserRole.STUDENT))],
)
def student_dashboard(db: DbSession, actor: CurrentUser) -> StudentDashboard:
    student = get(db, actor)
    return StudentDashboard(
        name=student.user.name,
        status=student.status,
        goal=student.goal,
        goal_detail=student.goal_detail,
        weight=student.weight,
        height=student.height,
        professional_name=student.professional.user.name if student.professional else None,
    )

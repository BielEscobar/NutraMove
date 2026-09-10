from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Student, StudentStatus, User
from app.repositories.students import scoped_query
from app.schemas.dashboard import RecentStudent, StudentMetrics


def student_metrics(db: Session, actor: User) -> tuple[StudentMetrics, int]:
    # Keep ownership in SQL, including every aggregate.
    scope = (
        scoped_query(db, actor)
        .with_only_columns(Student.id, Student.status, Student.professional_id)
        .subquery()
    )
    row = db.execute(
        select(
            func.count(scope.c.id),
            func.count(scope.c.id).filter(scope.c.status == StudentStatus.ACTIVE),
            func.count(scope.c.id).filter(scope.c.status == StudentStatus.PENDING_APPROVAL),
            func.count(scope.c.id).filter(scope.c.status == StudentStatus.INACTIVE),
            func.count(scope.c.id).filter(scope.c.status == StudentStatus.REJECTED),
            func.count(scope.c.id).filter(scope.c.professional_id.is_(None)),
        )
    ).one()
    return StudentMetrics(
        total=row[0], active=row[1], pending=row[2], inactive=row[3], rejected=row[4]
    ), row[5]


def recent_students(db: Session, actor: User) -> list[RecentStudent]:
    query = (
        scoped_query(db, actor)
        .with_only_columns(Student.id, User.name, Student.status, Student.created_at)
        .order_by(Student.created_at.desc(), Student.id.desc())
        .limit(5)
    )
    return [
        RecentStudent(id=row.id, name=row.name, status=row.status, created_at=row.created_at)
        for row in db.execute(query)
    ]

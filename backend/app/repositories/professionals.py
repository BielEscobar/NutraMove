from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, contains_eager

from app.models.professional import Professional
from app.models.user import User, UserRole


def base_query() -> Select[tuple[Professional]]:
    return (
        select(Professional)
        .join(Professional.user)
        .options(contains_eager(Professional.user))
        .where(User.role == UserRole.PROFESSIONAL)
    )


def get_by_id(db: Session, professional_id: UUID, *, lock: bool = False) -> Professional | None:
    query = base_query().where(Professional.id == professional_id)
    if lock:
        query = query.with_for_update(of=(Professional, User)).execution_options(
            populate_existing=True
        )
    return db.scalar(query)


def list_professionals(
    db: Session, search: str, is_active: bool | None, page: int, page_size: int
) -> tuple[list[Professional], int]:
    query = base_query()
    if search:
        query = query.where(
            or_(
                User.name.icontains(search, autoescape=True),
                User.email.icontains(search, autoescape=True),
                Professional.specialty.icontains(search, autoescape=True),
            )
        )
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = list(
        db.scalars(
            query.order_by(func.lower(User.name), Professional.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return items, total


def summary(db: Session) -> tuple[int, int]:
    query = (
        select(
            func.count(Professional.id),
            func.count(Professional.id).filter(User.is_active.is_(True)),
        )
        .join(Professional.user)
        .where(User.role == UserRole.PROFESSIONAL)
    )
    total, active = db.execute(query).one()
    return total, active

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.time import business_today
from app.models import User
from app.models.hydration import WaterRecord
from app.repositories import hydration
from app.schemas.hydration import HydrationDay, HydrationSummary, WaterCreate
from app.services.students import get


def create(db: Session, actor: User, data: WaterCreate) -> WaterRecord:
    owner = get(db, actor, lock=True)
    if not owner.user.is_active:
        raise HTTPException(401, "Sessão inválida ou expirada.")
    record = WaterRecord(student_id=owner.id, **data.model_dump())
    db.add(record)
    db.commit()
    return record


def summary(
    db: Session, actor: User, timezone: str, student_id: UUID | None = None
) -> HydrationSummary:
    owner = get(db, actor, student_id)
    today = business_today(timezone)
    total = hydration.daily_total(db, owner.id, timezone, today)
    # Existing professional goal is in liters; zero means no usable goal.
    goal = round(owner.water_goal * 1000) if owner.water_goal else None
    goal = goal if goal and goal > 0 else None
    return HydrationSummary(
        date=today,
        timezone=timezone,
        consumed_ml=total,
        goal_ml=goal,
        remaining_ml=max(0, goal - total) if goal else None,
        percentage=round(total / goal * 100, 1) if goal else None,
    )


def daily(
    db: Session, actor: User, timezone: str, student_id: UUID | None, page: int, page_size: int
) -> HydrationDay:
    owner = get(db, actor, student_id)
    result = summary(db, actor, timezone, owner.id)
    records, total = hydration.daily_records(db, owner.id, timezone, result.date, page, page_size)
    return HydrationDay(
        **result.model_dump(), records=records, total_records=total, page=page, page_size=page_size
    )

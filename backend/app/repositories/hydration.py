from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.core.time import business_today, day_bounds
from app.models.hydration import WaterRecord
from app.schemas.hydration import HydrationHistory, HydrationPoint, WaterResponse


def daily_total(db: Session, student_id: UUID, timezone: str, day: date) -> int:
    start, end = day_bounds(day, timezone)
    return int(
        db.scalar(
            select(func.coalesce(func.sum(WaterRecord.amount_ml), 0)).where(
                WaterRecord.student_id == student_id,
                WaterRecord.consumed_at >= start,
                WaterRecord.consumed_at < end,
            )
        )
        or 0
    )


def daily_records(
    db: Session, student_id: UUID, timezone: str, day: date, page: int, page_size: int
) -> tuple[list[WaterResponse], int]:
    start, end = day_bounds(day, timezone)
    query = select(WaterRecord).where(
        WaterRecord.student_id == student_id,
        WaterRecord.consumed_at >= start,
        WaterRecord.consumed_at < end,
    )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    records = db.scalars(
        query.order_by(WaterRecord.consumed_at.desc(), WaterRecord.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return [WaterResponse.model_validate(record) for record in records], total


def history(db: Session, student_id: UUID, timezone: str, days: int) -> HydrationHistory:
    today = business_today(timezone)
    first = today - timedelta(days=days - 1)
    start, _ = day_bounds(first, timezone)
    _, end = day_bounds(today, timezone)
    local_date = cast(func.timezone(timezone, WaterRecord.consumed_at), Date)
    rows = db.execute(
        select(local_date, func.sum(WaterRecord.amount_ml))
        .where(
            WaterRecord.student_id == student_id,
            WaterRecord.consumed_at >= start,
            WaterRecord.consumed_at < end,
        )
        .group_by(local_date)
    ).all()
    totals = {row[0]: int(row[1]) for row in rows}
    # Fill dates without records; all consumption totals were aggregated by PostgreSQL.
    return HydrationHistory(
        timezone=timezone,
        days=days,
        items=[
            HydrationPoint(
                date=first + timedelta(days=i), consumed_ml=totals.get(first + timedelta(days=i), 0)
            )
            for i in range(days)
        ],
    )

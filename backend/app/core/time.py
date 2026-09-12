from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def day_bounds(day: date, timezone: str) -> tuple[datetime, datetime]:
    zone = ZoneInfo(timezone)
    return (
        datetime.combine(day, time.min, zone).astimezone(UTC),
        datetime.combine(day + timedelta(days=1), time.min, zone).astimezone(UTC),
    )


def business_today(timezone: str) -> date:
    return datetime.now(ZoneInfo(timezone)).date()

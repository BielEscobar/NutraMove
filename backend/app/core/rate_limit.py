"""Shared PostgreSQL windows for sensitive public and paid endpoints."""

import hashlib
import hmac
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import case, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.rate_limit import RateLimitWindow


def consume(
    db: Session,
    settings: Settings,
    scope: str,
    subject: str,
    *,
    limit: int,
    period_seconds: int,
    now: datetime | None = None,
) -> None:
    """Count before business logic, including failed attempts; do not trust X-Forwarded-For here."""
    now = now or datetime.now(UTC)
    secret = settings.rate_limit_secret.get_secret_value().encode()
    key_hash = hmac.new(secret, f"{scope}:{subject}".encode(), hashlib.sha256).hexdigest()
    cutoff = now - timedelta(seconds=period_seconds)
    statement = insert(RateLimitWindow).values(
        key_hash=key_hash, window_started_at=now, attempts=1, updated_at=now
    )
    upsert = statement.on_conflict_do_update(
        index_elements=[RateLimitWindow.key_hash],
        set_={
            "window_started_at": case(
                (RateLimitWindow.window_started_at <= cutoff, now),
                else_=RateLimitWindow.window_started_at,
            ),
            "attempts": case(
                (RateLimitWindow.window_started_at <= cutoff, 1),
                else_=RateLimitWindow.attempts + 1,
            ),
            "updated_at": now,
        },
    ).returning(RateLimitWindow.attempts)
    attempts = db.scalar(upsert)
    # Keep only recent pseudonymous identifiers. Cleanup uses the indexed timestamp.
    db.execute(delete(RateLimitWindow).where(RateLimitWindow.updated_at < now - timedelta(days=2)))
    db.commit()
    if attempts is not None and attempts > limit:
        raise HTTPException(
            429,
            "Muitas tentativas. Aguarde antes de tentar novamente.",
            headers={"Retry-After": str(period_seconds)},
        )

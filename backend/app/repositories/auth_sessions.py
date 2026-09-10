from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.security import token_digest
from app.models.auth_session import AuthSession
from app.models.user import User


def get_authenticated_user(db: Session, token: str) -> User | None:
    return db.scalar(
        select(User)
        .join(AuthSession, AuthSession.user_id == User.id)
        .where(
            AuthSession.token_hash == token_digest(token),
            AuthSession.expires_at > datetime.now(UTC),
            User.is_active.is_(True),
        )
    )


def revoke(db: Session, token: str) -> None:
    db.execute(delete(AuthSession).where(AuthSession.token_hash == token_digest(token)))

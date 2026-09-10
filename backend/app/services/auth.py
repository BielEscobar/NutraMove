import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import DUMMY_HASH, hash_password, token_digest, verify_password
from app.models.auth_session import AuthSession
from app.models.user import User, UserRole
from app.repositories import auth_sessions, users
from app.schemas.auth import LoginRequest, MasterCreate


def login(
    db: Session, data: LoginRequest, session_seconds: int, previous_token: str | None
) -> tuple[User, str]:
    user = users.get_by_email(db, str(data.email))
    valid = verify_password(
        data.password.get_secret_value(), user.password_hash if user else DUMMY_HASH
    )
    if user is None or not valid or not user.is_active:
        raise HTTPException(401, "E-mail ou senha inválidos.")

    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    if previous_token:
        auth_sessions.revoke(db, previous_token)
    db.execute(
        delete(AuthSession).where(AuthSession.user_id == user.id, AuthSession.expires_at <= now)
    )
    db.add(
        AuthSession(
            token_hash=token_digest(token),
            user_id=user.id,
            expires_at=now + timedelta(seconds=session_seconds),
        )
    )
    db.commit()
    return user, token


def logout(db: Session, token: str | None) -> None:
    if token:
        auth_sessions.revoke(db, token)
        db.commit()


def create_master(db: Session, data: MasterCreate) -> User:
    if users.get_by_email(db, str(data.email)):
        raise ValueError("E-mail já cadastrado.")
    user = User(
        name=data.name,
        email=str(data.email),
        password_hash=hash_password(data.password.get_secret_value()),
        role=UserRole.MASTER,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("Não foi possível criar o usuário; verifique o e-mail.") from exc
    db.refresh(user)
    return user

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.user import User, UserRole
from app.repositories.auth_sessions import get_authenticated_user

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def require_trusted_origin(request: Request, settings: AppSettings) -> None:
    if request.headers.get("origin") not in settings.cors_origins:
        raise HTTPException(403, "Origem da requisição não permitida.")


def get_current_user(request: Request, db: DbSession, settings: AppSettings) -> User:
    token = request.cookies.get(settings.session_cookie_name)
    if not token or len(token) != 43:
        raise HTTPException(401, "Autenticação necessária.")
    user = get_authenticated_user(db, token)
    if user is None:
        raise HTTPException(401, "Sessão inválida ou expirada.")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        require_trusted_origin(request, settings)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[..., User]:
    def check_role(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Você não tem permissão para acessar este recurso.")
        return user

    return check_role

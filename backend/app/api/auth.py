from fastapi import APIRouter, Depends, Request, Response

from app.api.dependencies import AppSettings, CurrentUser, DbSession, require_trusted_origin
from app.core.rate_limit import consume
from app.schemas.auth import LoginRequest, UserResponse
from app.services import auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserResponse, dependencies=[Depends(require_trusted_origin)])
def login(
    data: LoginRequest, request: Request, response: Response, db: DbSession, settings: AppSettings
) -> UserResponse:
    consume(
        db,
        settings,
        "login",
        request.client.host if request.client else "unknown",
        limit=10,
        period_seconds=300,
    )
    user, token = auth.login(
        db, data, settings.session_seconds, request.cookies.get(settings.session_cookie_name)
    )
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return UserResponse.model_validate(user)


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser, response: Response) -> UserResponse:
    response.headers["Cache-Control"] = "no-store"
    return UserResponse.model_validate(user)


@router.post("/logout", status_code=204, dependencies=[Depends(require_trusted_origin)])
def logout(request: Request, db: DbSession, settings: AppSettings) -> Response:
    auth.logout(db, request.cookies.get(settings.session_cookie_name))
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
    return response

import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = logging.getLogger(__name__)


async def http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "http_error", "message": str(exc.detail)}},
        headers=exc.headers,
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Do not echo submitted values: a future request may contain credentials.
    details = [{"location": list(error["loc"]), "type": error["type"]} for error in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Invalid request.",
                "details": details,
            }
        },
    )


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    frames = traceback.extract_tb(exc.__traceback__)
    locations = [(frame.filename, frame.lineno, frame.name) for frame in frames]
    logger.error("Unhandled application error: %s; locations=%s", type(exc).__name__, locations)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "Internal server error."}},
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)


class SafeErrorMiddleware(BaseHTTPMiddleware):
    """Handle failures before the server can log exception values containing personal data."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            return await unexpected_error_handler(request, exc)

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


logger = logging.getLogger(__name__)


def build_error_response(
    request: Request,
    status_code: int,
    error_type: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    content = {
        "success": False,
        "error": {
            "type": error_type,
            "code": status_code,
            "message": message,
            "details": details or [],
        },
        "method": request.method,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "path": request.url.path,
    }

    return JSONResponse(
        content=content,
        status_code=status_code,
        headers=headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "HTTP error"
        details = [] if isinstance(exc.detail, str) else [{"detail": exc.detail}]

        return build_error_response(
            request=request,
            status_code=exc.status_code,
            error_type="http_error",
            message=message,
            details=details,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = []

        for error in exc.errors():
            errors.append({
                "type": error.get("type"),
                "loc": ".".join(str(x) for x in error.get("loc", [])),
                "msg": error.get("msg"),
                "input": error.get("input"),
            })

        return build_error_response(
            request=request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_type="validation_error",
            message="Request validation failed",
            details=errors,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.error(
            "Unhandled exception while processing %s %s",
            request.method,
            request.url.path,
            exc_info=(type(exc), exc, exc.__traceback__),
        )

        return build_error_response(
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_type="internal_error",
            message="Internal server error",
        )

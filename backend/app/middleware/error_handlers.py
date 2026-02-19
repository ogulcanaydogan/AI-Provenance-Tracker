"""Global exception handlers for structured error responses."""

from __future__ import annotations

import uuid

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = structlog.get_logger()


def _request_id(request: Request) -> str:
    """Return the X-Request-Id header or generate a new one."""
    return request.headers.get("X-Request-Id") or uuid.uuid4().hex[:12]


def _error_body(
    *,
    request_id: str,
    status_code: int,
    error: str,
    detail: str | list | dict,
    path: str,
) -> dict:
    return {
        "error": error,
        "detail": detail,
        "status_code": status_code,
        "request_id": request_id,
        "path": path,
    }


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle FastAPI/Starlette HTTP exceptions with a consistent shape."""
    rid = _request_id(request)
    body = _error_body(
        request_id=rid,
        status_code=exc.status_code,
        error=_status_phrase(exc.status_code),
        detail=exc.detail,
        path=str(request.url.path),
    )
    # Preserve any extra headers from the exception (e.g. Retry-After)
    headers = getattr(exc, "headers", None) or {}
    return JSONResponse(status_code=exc.status_code, content=body, headers=headers)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle pydantic / query-param validation errors."""
    rid = _request_id(request)
    errors = []
    for err in exc.errors():
        errors.append(
            {
                "field": " -> ".join(str(loc) for loc in err.get("loc", [])),
                "message": err.get("msg", ""),
                "type": err.get("type", ""),
            }
        )
    body = _error_body(
        request_id=rid,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error="Validation Error",
        detail=errors,
        path=str(request.url.path),
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=body)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unexpected server errors — log and return 500."""
    rid = _request_id(request)
    logger.exception(
        "unhandled_exception",
        request_id=rid,
        path=str(request.url.path),
        method=request.method,
        error=str(exc),
    )
    body = _error_body(
        request_id=rid,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error="Internal Server Error",
        detail="An unexpected error occurred. Please try again or contact support.",
        path=str(request.url.path),
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=body)


def register_error_handlers(app: FastAPI) -> None:
    """Attach all global exception handlers to the FastAPI app."""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)  # type: ignore[arg-type]


_PHRASES: dict[int, str] = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    408: "Request Timeout",
    409: "Conflict",
    413: "Payload Too Large",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
}


def _status_phrase(code: int) -> str:
    return _PHRASES.get(code, "Error")

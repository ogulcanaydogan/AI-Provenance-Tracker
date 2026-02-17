"""HTTP audit middleware."""

from __future__ import annotations

import time

from fastapi import Request, Response

from app.core.config import settings
from app.services.audit_events import audit_event_store

_SKIP_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico")


async def audit_http_request(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
    """Capture request/response metadata as audit events."""
    if not settings.audit_events_enabled or not settings.audit_log_http_requests:
        return await call_next(request)

    path = request.url.path
    if path.startswith(_SKIP_PREFIXES):
        return await call_next(request)

    started = time.perf_counter()
    status_code = 500
    error_name: str | None = None
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception as exc:  # noqa: BLE001
        error_name = exc.__class__.__name__
        raise
    finally:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        actor_id = request.headers.get(settings.audit_actor_header, "") or None
        request_id = request.headers.get("X-Request-Id", "") or None
        client_ip = request.client.host if request.client else ""
        severity = "error" if status_code >= 500 else "warning" if status_code >= 400 else "info"
        await audit_event_store.safe_log_event(
            event_type="http.request",
            severity=severity,
            source="api",
            actor_id=actor_id,
            request_id=request_id,
            payload={
                "method": request.method,
                "path": path,
                "query": str(request.url.query),
                "status_code": status_code,
                "duration_ms": duration_ms,
                "client_ip": client_ip,
                "error": error_name,
            },
        )

"""Add Cache-Control headers to selected API responses."""

from __future__ import annotations

from fastapi import Request, Response

# Endpoints that benefit from short client-side caching.
_CACHEABLE_PREFIXES = (
    "/api/v1/analyze/stats",
    "/api/v1/analyze/dashboard",
    "/api/v1/analyze/evaluation",
)

# Long-lived static-ish content.
_LONG_CACHE_PREFIXES = ("/openapi.json",)


async def cache_control_middleware(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
    """Attach Cache-Control headers based on request path."""
    response: Response = await call_next(request)

    # Only cache successful GET responses
    if request.method != "GET" or response.status_code >= 400:
        return response

    path = request.url.path

    if path.startswith(_CACHEABLE_PREFIXES):
        response.headers.setdefault(
            "Cache-Control", "public, max-age=30, stale-while-revalidate=60"
        )
    elif path.startswith(_LONG_CACHE_PREFIXES):
        response.headers.setdefault(
            "Cache-Control", "public, max-age=3600, stale-while-revalidate=86400"
        )
    elif path.startswith("/api/"):
        # API mutation / history endpoints: no caching
        response.headers.setdefault("Cache-Control", "no-store")

    return response

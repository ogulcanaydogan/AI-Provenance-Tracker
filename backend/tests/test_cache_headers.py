"""Unit tests for the Cache-Control middleware."""

from __future__ import annotations

import pytest
from starlette.requests import Request
from starlette.responses import Response

from app.middleware.cache_headers import cache_control_middleware

SHORT_CACHE = "public, max-age=30, stale-while-revalidate=60"
LONG_CACHE = "public, max-age=3600, stale-while-revalidate=86400"


def _request(method: str, path: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "query_string": b"",
        }
    )


def _call_next(response: Response):  # type: ignore[no-untyped-def]
    async def _inner(_request: Request) -> Response:
        return response

    return _inner


class TestShortCache:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/analyze/stats",
            "/api/v1/analyze/dashboard",
            "/api/v1/analyze/evaluation",
        ],
    )
    async def test_cacheable_get_gets_short_cache(self, path: str) -> None:
        result = await cache_control_middleware(
            _request("GET", path), _call_next(Response(status_code=200))
        )
        assert result.headers["Cache-Control"] == SHORT_CACHE

    @pytest.mark.asyncio
    async def test_subpath_of_cacheable_prefix_matches(self) -> None:
        result = await cache_control_middleware(
            _request("GET", "/api/v1/analyze/stats/today"),
            _call_next(Response(status_code=200)),
        )
        assert result.headers["Cache-Control"] == SHORT_CACHE


class TestLongCache:
    @pytest.mark.asyncio
    async def test_openapi_gets_long_cache(self) -> None:
        result = await cache_control_middleware(
            _request("GET", "/openapi.json"), _call_next(Response(status_code=200))
        )
        assert result.headers["Cache-Control"] == LONG_CACHE


class TestNoStore:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "path",
        ["/api/v1/history", "/api/v1/detect/text", "/api/health"],
    )
    async def test_other_api_get_gets_no_store(self, path: str) -> None:
        result = await cache_control_middleware(
            _request("GET", path), _call_next(Response(status_code=200))
        )
        assert result.headers["Cache-Control"] == "no-store"


class TestNoHeaderAdded:
    @pytest.mark.asyncio
    async def test_non_api_path_gets_no_header(self) -> None:
        result = await cache_control_middleware(
            _request("GET", "/health"), _call_next(Response(status_code=200))
        )
        assert "Cache-Control" not in result.headers

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH"])
    async def test_non_get_method_gets_no_header(self, method: str) -> None:
        result = await cache_control_middleware(
            _request(method, "/api/v1/analyze/stats"),
            _call_next(Response(status_code=200)),
        )
        assert "Cache-Control" not in result.headers

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status", [400, 404, 500])
    async def test_error_status_gets_no_header(self, status: int) -> None:
        result = await cache_control_middleware(
            _request("GET", "/api/v1/analyze/stats"),
            _call_next(Response(status_code=status)),
        )
        assert "Cache-Control" not in result.headers


class TestSetdefault:
    @pytest.mark.asyncio
    async def test_existing_cache_control_is_preserved(self) -> None:
        response = Response(status_code=200, headers={"Cache-Control": "private, max-age=5"})
        result = await cache_control_middleware(
            _request("GET", "/api/v1/analyze/stats"), _call_next(response)
        )
        assert result.headers["Cache-Control"] == "private, max-age=5"

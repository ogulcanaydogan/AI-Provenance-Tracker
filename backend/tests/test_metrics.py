"""Tests for Prometheus /metrics endpoint and CORS hardening."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


# ── Prometheus /metrics endpoint ──────────────────────────────────────


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_200(client: AsyncClient) -> None:
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_metrics_contains_default_metrics(client: AsyncClient) -> None:
    # Fire a request to generate some metrics first
    await client.get("/health")
    response = await client.get("/metrics")
    body = response.text
    assert "http_request_duration" in body or "http_requests" in body


@pytest.mark.asyncio
async def test_metrics_excludes_health(client: AsyncClient) -> None:
    """Health endpoint hits should be excluded from metrics instrumentation."""
    for _ in range(3):
        await client.get("/health")
    response = await client.get("/metrics")
    body = response.text
    assert 'handler="/health"' not in body


# ── CORS hardening ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cors_preflight_restricted_methods(client: AsyncClient) -> None:
    response = await client.options(
        "/api/v1/detect/text",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    allowed = response.headers.get("access-control-allow-methods", "")
    assert "GET" in allowed
    assert "POST" in allowed
    assert "DELETE" not in allowed
    assert "PUT" not in allowed
    assert "PATCH" not in allowed


@pytest.mark.asyncio
async def test_cors_preflight_restricted_headers(client: AsyncClient) -> None:
    response = await client.options(
        "/api/v1/detect/text",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, X-API-Key",
        },
    )
    allowed_headers = response.headers.get("access-control-allow-headers", "").lower()
    assert "content-type" in allowed_headers
    assert "x-api-key" in allowed_headers


@pytest.mark.asyncio
async def test_cors_exposes_rate_limit_headers(client: AsyncClient) -> None:
    """Expose-headers are sent on actual cross-origin responses, not preflight."""
    response = await client.get(
        "/health",
        headers={"Origin": "http://localhost:3000"},
    )
    exposed = response.headers.get("access-control-expose-headers", "").lower()
    assert "retry-after" in exposed
    assert "x-request-id" in exposed


@pytest.mark.asyncio
async def test_cors_preflight_max_age(client: AsyncClient) -> None:
    response = await client.options(
        "/api/v1/detect/text",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    max_age = response.headers.get("access-control-max-age", "")
    assert max_age == "600"

"""Tests for deep health check and cache-control headers."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_basic(client: AsyncClient):
    """Basic health check returns healthy status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "checks" not in data  # No deep check by default


@pytest.mark.asyncio
async def test_health_deep_includes_db_check(client: AsyncClient):
    """Deep health check verifies database connectivity."""
    response = await client.get("/health?deep=true")
    assert response.status_code == 200
    data = response.json()
    assert "checks" in data
    assert data["checks"]["database"] == "ok"


@pytest.mark.asyncio
async def test_health_deep_includes_redis_check(client: AsyncClient):
    """Deep health check reports Redis status (may be unavailable in test)."""
    response = await client.get("/health?deep=true")
    data = response.json()
    assert "redis" in data["checks"]
    # Redis may or may not be available in test env
    assert isinstance(data["checks"]["redis"], str)


# ---------------------------------------------------------------------------
# Cache-Control headers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stats_endpoint_has_cache_header(client: AsyncClient):
    """Stats endpoint should return Cache-Control header."""
    # First create some data
    await client.post(
        "/api/v1/detect/text",
        json={"text": "Cache header test content." * 6},
    )
    response = await client.get("/api/v1/analyze/stats")
    assert response.status_code == 200
    cache_control = response.headers.get("cache-control", "")
    assert "max-age" in cache_control


@pytest.mark.asyncio
async def test_dashboard_endpoint_has_cache_header(client: AsyncClient):
    """Dashboard endpoint should return Cache-Control header."""
    response = await client.get("/api/v1/analyze/dashboard?days=7")
    assert response.status_code == 200
    cache_control = response.headers.get("cache-control", "")
    assert "max-age" in cache_control


@pytest.mark.asyncio
async def test_detection_post_has_no_cache_header(client: AsyncClient):
    """POST detection endpoints should not receive cache headers."""
    response = await client.post(
        "/api/v1/detect/text",
        json={"text": "No-store cache test content." * 6},
    )
    assert response.status_code == 200
    cache_control = response.headers.get("cache-control", "")
    # POST responses should not have caching directives
    assert "max-age" not in cache_control


@pytest.mark.asyncio
async def test_history_endpoint_has_no_store(client: AsyncClient):
    """History listing is dynamic and should not be cached."""
    response = await client.get("/api/v1/analyze/history")
    assert response.status_code == 200
    cache_control = response.headers.get("cache-control", "")
    assert "no-store" in cache_control

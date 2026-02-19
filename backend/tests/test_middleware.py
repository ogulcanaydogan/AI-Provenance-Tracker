"""Tests for middleware: rate limiter, error handlers, and audit."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.middleware.rate_limiter import (
    InMemoryRateLimiter,
    _client_identifier,
    _cost_for_bucket,
    _limit_for_bucket,
    _path_bucket,
    rate_limiter,
)


# ---------------------------------------------------------------------------
# Rate limiter — path bucketing
# ---------------------------------------------------------------------------


class TestPathBucket:
    """Verify URL paths are categorised into the correct rate-limit bucket."""

    def test_text_detection(self):
        assert _path_bucket("/api/v1/detect/text") == "text"

    def test_image_detection(self):
        assert _path_bucket("/api/v1/detect/image") == "media"

    def test_audio_detection(self):
        assert _path_bucket("/api/v1/detect/audio") == "media"

    def test_video_detection(self):
        assert _path_bucket("/api/v1/detect/video") == "media"

    def test_url_detection(self):
        assert _path_bucket("/api/v1/detect/url") == "media"

    def test_batch_text(self):
        assert _path_bucket("/api/v1/batch/text") == "batch"

    def test_intel_endpoint(self):
        assert _path_bucket("/api/v1/intel/collect") == "intel"

    def test_unknown_falls_to_default(self):
        assert _path_bucket("/api/v1/analyze/history") == "default"

    def test_root_falls_to_default(self):
        assert _path_bucket("/health") == "default"


# ---------------------------------------------------------------------------
# Rate limiter — bucket limit/cost helpers
# ---------------------------------------------------------------------------


class TestBucketLimits:
    def test_media_limit_uses_media_setting(self):
        assert _limit_for_bucket("media") == settings.rate_limit_media_requests

    def test_batch_limit_uses_batch_setting(self):
        assert _limit_for_bucket("batch") == settings.rate_limit_batch_requests

    def test_intel_limit_uses_intel_setting(self):
        assert _limit_for_bucket("intel") == settings.rate_limit_intel_requests

    def test_default_limit_uses_default_setting(self):
        assert _limit_for_bucket("default") == settings.rate_limit_requests

    def test_text_cost(self):
        assert _cost_for_bucket("text") == settings.spend_cost_text

    def test_media_cost_picks_max(self):
        expected = max(
            settings.spend_cost_image,
            settings.spend_cost_audio,
            settings.spend_cost_video,
        )
        assert _cost_for_bucket("media") == expected

    def test_batch_cost(self):
        assert _cost_for_bucket("batch") == settings.spend_cost_batch

    def test_intel_cost(self):
        assert _cost_for_bucket("intel") == settings.spend_cost_intel

    def test_unknown_bucket_cost_is_one(self):
        assert _cost_for_bucket("unknown") == 1


# ---------------------------------------------------------------------------
# Rate limiter — in-memory window behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_limiter_allows_within_limit():
    limiter = InMemoryRateLimiter()
    usage = await limiter.check("test-client", "/api/v1/detect/text")
    assert usage["cost"] == settings.spend_cost_text
    assert usage["daily_points"] >= 1


@pytest.mark.asyncio
async def test_limiter_rejects_after_limit_exceeded():
    """Exceeding the window limit raises 429."""
    limiter = InMemoryRateLimiter()
    old_limit = settings.rate_limit_requests
    settings.rate_limit_requests = 2
    try:
        await limiter.check("client-a", "/api/v1/analyze/stats")
        await limiter.check("client-a", "/api/v1/analyze/stats")
        with pytest.raises(Exception) as exc_info:
            await limiter.check("client-a", "/api/v1/analyze/stats")
        assert exc_info.value.status_code == 429  # type: ignore[union-attr]
    finally:
        settings.rate_limit_requests = old_limit


@pytest.mark.asyncio
async def test_limiter_daily_spend_cap():
    """Exceeding the daily spend cap raises 429."""
    limiter = InMemoryRateLimiter()
    old_cap = settings.daily_spend_cap_points
    settings.daily_spend_cap_points = 2
    try:
        await limiter.check("spender", "/api/v1/detect/text")
        await limiter.check("spender", "/api/v1/detect/text")
        with pytest.raises(Exception) as exc_info:
            await limiter.check("spender", "/api/v1/detect/text")
        assert exc_info.value.status_code == 429  # type: ignore[union-attr]
        assert "spend cap" in str(exc_info.value.detail).lower()  # type: ignore[union-attr]
    finally:
        settings.daily_spend_cap_points = old_cap


@pytest.mark.asyncio
async def test_limiter_isolates_clients():
    """Different clients have independent limits."""
    limiter = InMemoryRateLimiter()
    old_limit = settings.rate_limit_requests
    settings.rate_limit_requests = 1
    try:
        await limiter.check("client-x", "/api/v1/analyze/stats")
        # client-y should still be allowed
        usage = await limiter.check("client-y", "/api/v1/analyze/stats")
        assert usage["limit"] == 1
    finally:
        settings.rate_limit_requests = old_limit


# ---------------------------------------------------------------------------
# Client identifier extraction
# ---------------------------------------------------------------------------


class TestClientIdentifier:
    def test_uses_x_forwarded_for(self):
        class FakeRequest:
            headers = {"x-forwarded-for": "1.2.3.4, 5.6.7.8"}
            client = None

        assert _client_identifier(FakeRequest()) == "1.2.3.4"

    def test_falls_back_to_client_host(self):
        class FakeClient:
            host = "10.0.0.1"

        class FakeRequest:
            headers = {}
            client = FakeClient()

        assert _client_identifier(FakeRequest()) == "10.0.0.1"

    def test_unknown_when_no_client(self):
        class FakeRequest:
            headers = {}
            client = None

        assert _client_identifier(FakeRequest()) == "unknown"


# ---------------------------------------------------------------------------
# Error handler — structured JSON responses
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_error_handler_404_returns_structured_json(client: AsyncClient):
    """Non-existent route returns structured error body."""
    response = await client.get("/api/v1/nonexistent-endpoint-xyz")
    assert response.status_code in (404, 405)
    body = response.json()
    assert "error" in body
    assert "detail" in body
    assert "status_code" in body
    assert "request_id" in body
    assert "path" in body


@pytest.mark.asyncio
async def test_error_handler_422_returns_validation_errors(client: AsyncClient):
    """Validation error produces structured error with field list."""
    response = await client.post("/api/v1/detect/text", json={})
    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "Validation Error"
    assert isinstance(body["detail"], list)
    assert len(body["detail"]) >= 1
    assert "field" in body["detail"][0]
    assert "message" in body["detail"][0]


@pytest.mark.asyncio
async def test_error_handler_preserves_retry_after_header(client: AsyncClient):
    """Rate-limited response includes Retry-After header via error handler."""
    settings.rate_limit_requests = 1
    settings.rate_limit_window_seconds = 60
    rate_limiter._hits.clear()

    body = {"text": "Rate limit error handler test." * 4}
    await client.post("/api/v1/detect/text", json=body)
    response = await client.post("/api/v1/detect/text", json=body)

    assert response.status_code == 429
    assert response.headers.get("retry-after") is not None
    data = response.json()
    assert data["status_code"] == 429
    assert "request_id" in data


@pytest.mark.asyncio
async def test_error_handler_uses_request_id_header(client: AsyncClient):
    """X-Request-Id is echoed back in the error body."""
    response = await client.get(
        "/api/v1/nonexistent-endpoint-xyz",
        headers={"X-Request-Id": "test-req-123"},
    )
    body = response.json()
    assert body["request_id"] == "test-req-123"


# ---------------------------------------------------------------------------
# Audit middleware — skips health/docs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_middleware_skips_health_endpoint(client: AsyncClient):
    """Health check does not produce an audit event."""
    from app.services.audit_events import audit_event_store

    await audit_event_store.reset()
    await client.get("/health")

    events, total = await audit_event_store.list_events(limit=10, offset=0)
    # Health endpoint is in _SKIP_PREFIXES, so no event should be recorded
    http_events = [
        e
        for e in events
        if e.get("event_type") == "http.request"
        and "/health" in str(e.get("payload", {}).get("path", ""))
    ]
    assert len(http_events) == 0


@pytest.mark.asyncio
async def test_audit_middleware_records_api_request(client: AsyncClient):
    """API detection requests produce audit events."""
    from app.services.audit_events import audit_event_store

    await audit_event_store.reset()
    await client.post(
        "/api/v1/detect/text",
        json={"text": "Audit middleware test content." * 6},
    )

    events, total = await audit_event_store.list_events(limit=20, offset=0)
    http_events = [e for e in events if e.get("event_type") == "http.request"]
    assert len(http_events) >= 1
    payload = http_events[0].get("payload", {})
    assert payload.get("method") == "POST"
    assert "/detect/text" in payload.get("path", "")

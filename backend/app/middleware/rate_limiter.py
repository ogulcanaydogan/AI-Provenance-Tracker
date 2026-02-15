"""Rate limiting, API-key auth, and spend-cap controls."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from datetime import UTC, datetime

import structlog
from fastapi import HTTPException, Request

from app.core.config import settings

logger = structlog.get_logger()


class InMemoryRateLimiter:
    """Fixed-window limiter with per-day spend cap."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._daily_points: dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def check(self, key: str, path: str) -> dict[str, int]:
        now = time.time()
        window = settings.rate_limit_window_seconds
        bucket = _path_bucket(path)
        limit = _limit_for_bucket(bucket)
        cost = _cost_for_bucket(bucket)
        hit_key = f"{key}:{bucket}"

        async with self._lock:
            hit_window = self._hits.setdefault(hit_key, deque())
            cutoff = now - window

            while hit_window and hit_window[0] <= cutoff:
                hit_window.popleft()

            if len(hit_window) >= limit:
                retry_after = max(1, int(window - (now - hit_window[0])))
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Please try again later.",
                    headers={"Retry-After": str(retry_after)},
                )

            day_key = f"{key}:{datetime.now(UTC).date().isoformat()}"
            current_points = self._daily_points.get(day_key, 0)
            next_points = current_points + cost
            if next_points > settings.daily_spend_cap_points:
                raise HTTPException(
                    status_code=429,
                    detail=(
                        "Daily spend cap reached for this client. "
                        "Try again tomorrow or reduce heavy endpoint usage."
                    ),
                )

            hit_window.append(now)
            self._daily_points[day_key] = next_points
            return {"cost": cost, "daily_points": next_points, "limit": limit}


def _path_bucket(path: str) -> str:
    if path.endswith("/detect/text"):
        return "text"
    if "/detect/" in path and any(path.endswith(suffix) for suffix in ("/image", "/audio", "/video", "/url")):
        return "media"
    if "/batch/" in path:
        return "batch"
    if "/intel/" in path:
        return "intel"
    return "default"


def _limit_for_bucket(bucket: str) -> int:
    if bucket == "media":
        return settings.rate_limit_media_requests
    if bucket == "batch":
        return settings.rate_limit_batch_requests
    if bucket == "intel":
        return settings.rate_limit_intel_requests
    return settings.rate_limit_requests


def _cost_for_bucket(bucket: str) -> int:
    if bucket == "text":
        return settings.spend_cost_text
    if bucket == "media":
        return max(settings.spend_cost_image, settings.spend_cost_audio, settings.spend_cost_video)
    if bucket == "batch":
        return settings.spend_cost_batch
    if bucket == "intel":
        return settings.spend_cost_intel
    return 1


rate_limiter = InMemoryRateLimiter()


def _client_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded_for:
        return forwarded_for
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _validate_api_key(request: Request) -> str | None:
    provided = request.headers.get(settings.api_key_header)
    if not settings.require_api_key:
        return provided
    if not provided or provided not in settings.api_keys:
        raise HTTPException(status_code=401, detail="Missing or invalid API key")
    return provided


async def rate_limit(request: Request) -> None:
    """Enforce API key, endpoint quotas, and spend cap."""
    api_key = _validate_api_key(request)
    client_key = api_key or _client_identifier(request)
    usage = await rate_limiter.check(client_key, request.url.path)
    logger.info(
        "api_usage",
        path=request.url.path,
        client=client_key[:12],
        cost=usage["cost"],
        daily_points=usage["daily_points"],
        window_limit=usage["limit"],
    )


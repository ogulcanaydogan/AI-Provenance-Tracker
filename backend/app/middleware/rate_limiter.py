"""Rate limiting, API-key auth, and spend-cap controls."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import HTTPException, Request

from app.core.config import settings
from app.services.api_key_plan_store import api_key_plan_store

logger = structlog.get_logger()


class InMemoryRateLimiter:
    """Fixed-window limiter with per-day spend cap."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._daily_points: dict[str, int] = {}
        self._monthly_usage: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def check(self, key: str, path: str, plan: str = "anonymous") -> dict[str, Any]:
        now = time.time()
        window = settings.rate_limit_window_seconds
        bucket = _path_bucket(path)
        limit = _limit_for_bucket(bucket, plan=plan)
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
            month_key = f"{key}:{datetime.now(UTC).strftime('%Y-%m')}"
            current_points = self._daily_points.get(day_key, 0)
            next_points = current_points + cost
            daily_cap = _daily_cap_for_plan(plan=plan)
            if next_points > daily_cap:
                raise HTTPException(
                    status_code=429,
                    detail=(
                        "Daily spend cap reached for this client. "
                        "Try again tomorrow or reduce heavy endpoint usage."
                    ),
                )

            month = self._monthly_usage.setdefault(
                month_key,
                {"requests": 0, "points": 0, "plan": plan, "by_bucket": {}},
            )
            next_month_requests = int(month["requests"]) + 1
            monthly_cap = _monthly_request_cap_for_plan(plan=plan)
            if next_month_requests > monthly_cap:
                raise HTTPException(
                    status_code=429,
                    detail=(
                        "Monthly request quota reached for this API key plan. "
                        "Upgrade plan or wait for next billing cycle."
                    ),
                )

            hit_window.append(now)
            self._daily_points[day_key] = next_points
            month["requests"] = next_month_requests
            month["points"] = int(month["points"]) + cost
            month["plan"] = plan
            by_bucket = month.setdefault("by_bucket", {})
            by_bucket[bucket] = int(by_bucket.get(bucket, 0)) + 1
            return {
                "cost": cost,
                "daily_points": next_points,
                "limit": limit,
                "plan": plan,
                "monthly_requests": next_month_requests,
                "monthly_request_cap": monthly_cap,
                "daily_point_cap": daily_cap,
            }

    async def get_client_usage(self, key: str, plan: str = "anonymous") -> dict[str, Any]:
        """Return current daily/monthly usage counters for a client key."""
        today_key = f"{key}:{datetime.now(UTC).date().isoformat()}"
        month_key = f"{key}:{datetime.now(UTC).strftime('%Y-%m')}"
        async with self._lock:
            monthly = dict(self._monthly_usage.get(month_key, {}))
            return {
                "client_key": key,
                "plan": plan,
                "daily_points": int(self._daily_points.get(today_key, 0)),
                "daily_point_cap": _daily_cap_for_plan(plan=plan),
                "monthly_requests": int(monthly.get("requests", 0)),
                "monthly_points": int(monthly.get("points", 0)),
                "monthly_request_cap": _monthly_request_cap_for_plan(plan=plan),
                "by_bucket_monthly": monthly.get("by_bucket", {}),
            }

    async def list_monthly_usage(self) -> list[dict[str, Any]]:
        """Return metering rows for the active month across all known keys."""
        month_prefix = datetime.now(UTC).strftime("%Y-%m")
        rows: list[dict[str, Any]] = []
        async with self._lock:
            for key, payload in self._monthly_usage.items():
                if not key.endswith(month_prefix):
                    continue
                client_key = key.rsplit(":", 1)[0]
                rows.append(
                    {
                        "client_key": client_key,
                        "month": month_prefix,
                        "plan": payload.get("plan", "anonymous"),
                        "requests": int(payload.get("requests", 0)),
                        "points": int(payload.get("points", 0)),
                        "by_bucket": payload.get("by_bucket", {}),
                    }
                )
        rows.sort(key=lambda item: (item["requests"], item["points"]), reverse=True)
        return rows


def _path_bucket(path: str) -> str:
    if path.endswith("/detect/text"):
        return "text"
    if "/detect/" in path and any(
        path.endswith(suffix) for suffix in ("/image", "/audio", "/video", "/url")
    ):
        return "media"
    if "/batch/" in path:
        return "batch"
    if "/intel/" in path:
        return "intel"
    return "default"


def _limit_for_bucket(bucket: str, plan: str = "anonymous") -> int:
    plan_limits = settings.api_plan_window_limits
    if plan != "anonymous" and isinstance(plan_limits, dict) and plan in plan_limits:
        try:
            configured = int(plan_limits.get(plan, 0))
        except (TypeError, ValueError):
            configured = 0
        if configured > 0:
            return configured

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


def _daily_cap_for_plan(plan: str) -> int:
    caps = settings.api_plan_daily_point_caps
    if plan != "anonymous" and isinstance(caps, dict) and plan in caps:
        try:
            value = int(caps.get(plan, 0))
        except (TypeError, ValueError):
            value = 0
        if value > 0:
            return value
    return settings.daily_spend_cap_points


def _monthly_request_cap_for_plan(plan: str) -> int:
    caps = settings.api_plan_monthly_request_caps
    if plan != "anonymous" and isinstance(caps, dict) and plan in caps:
        try:
            value = int(caps.get(plan, 0))
        except (TypeError, ValueError):
            value = 0
        if value > 0:
            return value
    return 1_000_000_000


rate_limiter = InMemoryRateLimiter()


def _client_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded_for:
        return forwarded_for
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


async def _validate_api_key(request: Request) -> tuple[str | None, str]:
    provided = request.headers.get(settings.api_key_header)
    known_keys = set(settings.api_keys or [])
    known_keys.update((settings.api_key_plans or {}).keys())
    if not settings.require_api_key:
        if not provided:
            return None, "anonymous"
        plan = await api_key_plan_store.resolve_plan(provided)
        return provided, plan
    if not provided or provided not in known_keys:
        raise HTTPException(status_code=401, detail="Missing or invalid API key")
    plan = await api_key_plan_store.resolve_plan(provided)
    return provided, plan


async def rate_limit(request: Request) -> None:
    """Enforce API key, endpoint quotas, and spend cap."""
    api_key, plan = await _validate_api_key(request)
    client_key = api_key or _client_identifier(request)
    usage = await rate_limiter.check(client_key, request.url.path, plan=plan)
    request.state.api_usage = usage
    request.state.api_plan = plan
    request.state.api_client_key = client_key
    logger.info(
        "api_usage",
        path=request.url.path,
        client=client_key[:12],
        plan=plan,
        cost=usage["cost"],
        daily_points=usage["daily_points"],
        window_limit=usage["limit"],
        monthly_requests=usage["monthly_requests"],
    )

"""Persistent API-key plan overrides for billing sync workflows."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import settings

SUPPORTED_PLANS = {"starter", "pro", "enterprise"}


def normalize_plan(plan: str | None) -> str:
    raw = (plan or "").strip().lower()
    if raw in SUPPORTED_PLANS:
        return raw
    return settings.api_key_default_plan.strip().lower() or "starter"


def resolve_plan_from_price(price_id: str | None) -> str | None:
    if not price_id:
        return None
    mapped = settings.stripe_price_plan_map.get(price_id)
    if not mapped:
        return None
    return normalize_plan(mapped)


class ApiKeyPlanStore:
    """Loads env defaults and applies persisted plan overrides."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._loaded = False
        self._overrides: dict[str, dict[str, Any]] = {}

    @property
    def _overrides_path(self) -> Path:
        return Path(settings.billing_plan_overrides_file).expanduser().resolve()

    async def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        async with self._lock:
            if self._loaded:
                return
            path = self._overrides_path
            if path.exists():
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    payload = {}
                overrides = payload.get("overrides", {})
                if isinstance(overrides, dict):
                    self._overrides = {
                        str(k): v
                        for k, v in overrides.items()
                        if isinstance(v, dict) and isinstance(v.get("plan"), str)
                    }
            self._loaded = True

    async def resolve_plan(self, api_key: str | None) -> str:
        """Resolve plan for API key, using overrides first then env defaults."""
        if not api_key:
            return "anonymous"
        await self._ensure_loaded()
        async with self._lock:
            override = self._overrides.get(api_key)
            if override:
                return normalize_plan(override.get("plan"))
        configured = settings.api_key_plans.get(api_key)
        if configured:
            return normalize_plan(configured)
        if api_key in (settings.api_keys or []):
            return normalize_plan(settings.api_key_default_plan)
        return "anonymous"

    async def upsert_override(
        self,
        *,
        api_key: str,
        plan: str,
        source: str,
        event_id: str | None = None,
        customer_id: str | None = None,
        subscription_id: str | None = None,
        price_id: str | None = None,
    ) -> dict[str, Any]:
        await self._ensure_loaded()
        normalized_plan = normalize_plan(plan)
        updated_at = datetime.now(UTC).isoformat()
        record: dict[str, Any] = {
            "plan": normalized_plan,
            "source": source,
            "updated_at": updated_at,
        }
        if event_id:
            record["event_id"] = event_id
        if customer_id:
            record["customer_id"] = customer_id
        if subscription_id:
            record["subscription_id"] = subscription_id
        if price_id:
            record["price_id"] = price_id

        async with self._lock:
            self._overrides[api_key] = record
            path = self._overrides_path
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"updated_at": updated_at, "overrides": self._overrides}
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return record

    async def list_overrides(self) -> dict[str, dict[str, Any]]:
        await self._ensure_loaded()
        async with self._lock:
            return dict(self._overrides)


api_key_plan_store = ApiKeyPlanStore()

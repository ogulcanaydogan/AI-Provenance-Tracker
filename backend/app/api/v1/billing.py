"""Billing API endpoints for API-key plan sync and usage-based monetization."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.api_key_plan_store import (
    normalize_plan,
    resolve_plan_from_price,
    api_key_plan_store,
)
from app.services.audit_events import audit_event_store

router = APIRouter()


class PlanSyncRequest(BaseModel):
    """Manual plan-sync payload for operational backfills."""

    api_key: str = Field(..., min_length=6)
    plan: str = Field(..., description="starter|pro|enterprise")
    customer_id: str | None = None
    subscription_id: str | None = None
    source: str = "manual"


def _authorize_billing_webhook(secret_header: str | None) -> None:
    required = settings.billing_webhook_secret.strip()
    if not required:
        return
    if not secret_header or secret_header != required:
        raise HTTPException(status_code=403, detail="Invalid billing webhook secret")


@router.post("/plan-sync")
async def sync_plan(
    payload: PlanSyncRequest,
    x_billing_webhook_secret: str | None = Header(default=None),
) -> dict[str, Any]:
    """
    Upsert API key plan mapping.

    This endpoint is intended for internal billing orchestration and admin backfills.
    """
    _authorize_billing_webhook(x_billing_webhook_secret)
    record = await api_key_plan_store.upsert_override(
        api_key=payload.api_key,
        plan=payload.plan,
        source=payload.source,
        customer_id=payload.customer_id,
        subscription_id=payload.subscription_id,
    )
    await audit_event_store.safe_log_event(
        event_type="billing.plan_synced",
        source="api",
        payload={
            "api_key_suffix": payload.api_key[-6:],
            "plan": normalize_plan(payload.plan),
            "source": payload.source,
            "customer_id": payload.customer_id,
            "subscription_id": payload.subscription_id,
        },
    )
    return {"status": "ok", "record": record}


@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    x_billing_webhook_secret: str | None = Header(default=None),
) -> dict[str, Any]:
    """
    Stripe-style webhook handler for plan synchronization.

    Expected payload format:
      {
        "id": "evt_...",
        "type": "customer.subscription.updated",
        "data": {
          "object": {
            "metadata": {"api_key": "...", "plan": "pro"},
            "items": {"data": [{"price": {"id": "price_..."}}]},
            "customer": "cus_...",
            "id": "sub_..."
          }
        }
      }
    """
    _authorize_billing_webhook(x_billing_webhook_secret)
    payload = await request.json()
    event_type = str(payload.get("type", "unknown"))
    event_id = str(payload.get("id", "")) or None
    obj = payload.get("data", {}).get("object", {})
    metadata = obj.get("metadata", {}) if isinstance(obj, dict) else {}

    api_key = str(metadata.get("api_key", "")).strip()
    explicit_plan = str(metadata.get("plan", "")).strip().lower()

    price_id = None
    try:
        price_id = str(obj["items"]["data"][0]["price"]["id"])
    except Exception:
        price_id = None

    derived_plan = resolve_plan_from_price(price_id)
    final_plan = explicit_plan or derived_plan

    accepted = False
    if api_key and final_plan:
        await api_key_plan_store.upsert_override(
            api_key=api_key,
            plan=final_plan,
            source="stripe_webhook",
            event_id=event_id,
            customer_id=str(obj.get("customer", "") or "") or None,
            subscription_id=str(obj.get("id", "") or "") or None,
            price_id=price_id,
        )
        accepted = True
    elif api_key and event_type in {
        "customer.subscription.deleted",
        "customer.subscription.paused",
    }:
        await api_key_plan_store.upsert_override(
            api_key=api_key,
            plan=settings.api_key_default_plan,
            source="stripe_webhook",
            event_id=event_id,
            customer_id=str(obj.get("customer", "") or "") or None,
            subscription_id=str(obj.get("id", "") or "") or None,
            price_id=price_id,
        )
        accepted = True

    await audit_event_store.safe_log_event(
        event_type="billing.webhook_received",
        source="stripe",
        payload={
            "event_id": event_id,
            "event_type": event_type,
            "accepted": accepted,
            "api_key_suffix": api_key[-6:] if api_key else None,
            "plan": normalize_plan(final_plan) if final_plan else None,
            "price_id": price_id,
        },
    )
    return {"status": "accepted", "applied": accepted, "event_type": event_type}

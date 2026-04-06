"""Instagram-first social intake and admin endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from app.core.config import settings
from app.models.social import (
    SocialEventItem,
    SocialEventListResponse,
    SocialQueueProcessResponse,
    SocialWebhookIngestResponse,
)
from app.services.audit_events import audit_event_store
from app.services.social_intake import social_intake_service

router = APIRouter()


def _authorize_social_admin(secret_header: str | None) -> None:
    required = settings.social_admin_secret.strip()
    if not required:
        return
    if not secret_header or secret_header != required:
        raise HTTPException(status_code=403, detail="Invalid social admin secret")


@router.get("/instagram/webhook", include_in_schema=False)
async def verify_instagram_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> PlainTextResponse:
    """Webhook verification handshake for Instagram subscriptions."""
    if hub_mode != "subscribe" or not hub_challenge:
        raise HTTPException(status_code=400, detail="Invalid webhook verification challenge")

    expected_token = settings.instagram_webhook_verify_token.strip()
    if expected_token and hub_verify_token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid Instagram verify token")

    return PlainTextResponse(hub_challenge)


@router.post("/instagram/webhook", response_model=SocialWebhookIngestResponse)
async def ingest_instagram_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
) -> SocialWebhookIngestResponse:
    """Receive Instagram webhook notifications and enqueue unique events."""
    body = await request.body()
    if not social_intake_service.verify_instagram_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Invalid Instagram webhook signature")

    try:
        payload = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid Instagram webhook payload") from exc

    if not isinstance(payload, dict) or payload.get("object") != "instagram":
        raise HTTPException(status_code=400, detail="Unsupported webhook object")

    result = await social_intake_service.enqueue_instagram_webhook(payload)
    await audit_event_store.safe_log_event(
        event_type="social.webhook_received",
        source="instagram_webhook",
        payload=result,
    )
    return SocialWebhookIngestResponse(**result)


@router.get("/events", response_model=SocialEventListResponse)
async def list_social_events(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: str = Query(default="", max_length=16),
    x_social_admin_secret: str | None = Header(default=None),
) -> SocialEventListResponse:
    """List social queue rows for admin inspection."""
    _authorize_social_admin(x_social_admin_secret)
    items, total = await social_intake_service.list_events(
        limit=limit,
        offset=offset,
        status=status.strip() or None,
    )
    return SocialEventListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        status=status.strip() or None,
    )


@router.get("/events/{event_id}", response_model=SocialEventItem)
async def get_social_event(
    event_id: int,
    x_social_admin_secret: str | None = Header(default=None),
) -> SocialEventItem:
    """Return one social queue row for detail inspection."""
    _authorize_social_admin(x_social_admin_secret)
    item = await social_intake_service.get_event(event_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Social event not found")
    return SocialEventItem(**item)


@router.post("/events/process", response_model=SocialQueueProcessResponse)
async def process_social_events(
    limit: int = Query(default=0, ge=0, le=200),
    x_social_admin_secret: str | None = Header(default=None),
) -> SocialQueueProcessResponse:
    """Drain pending social events immediately."""
    _authorize_social_admin(x_social_admin_secret)
    result = await social_intake_service.process_pending_events(limit=limit or None)
    return SocialQueueProcessResponse(**result)


@router.post("/events/{event_id}/process", response_model=SocialEventItem)
async def process_social_event(
    event_id: int,
    x_social_admin_secret: str | None = Header(default=None),
) -> SocialEventItem:
    """Process or reprocess a specific social queue row immediately."""
    _authorize_social_admin(x_social_admin_secret)
    item = await social_intake_service.process_event(event_id)
    return SocialEventItem(**item)

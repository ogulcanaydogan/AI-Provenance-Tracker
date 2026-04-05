"""Pydantic models for social intake queue and admin responses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SocialEventItem(BaseModel):
    """Admin-facing social event queue item."""

    id: int
    platform_event_id: str
    platform: str
    event_type: str
    reply_channel: Literal["dm", "public_comment"]
    status: Literal["pending", "processing", "completed", "failed", "skipped"]
    source_url: str | None = None
    actor_platform_id: str | None = None
    platform_media_id: str | None = None
    platform_comment_id: str | None = None
    analysis_id: str | None = None
    response_status: str | None = None
    response_id: str | None = None
    attempt_count: int = 0
    last_error: str | None = None
    created_at: str
    updated_at: str


class SocialEventListResponse(BaseModel):
    """Paginated social event list."""

    items: list[SocialEventItem]
    total: int
    limit: int
    offset: int
    status: str | None = None


class SocialQueueProcessResponse(BaseModel):
    """Worker/admin queue drain summary."""

    scanned: int = Field(default=0)
    processed: int = Field(default=0)
    completed: int = Field(default=0)
    failed: int = Field(default=0)
    skipped: int = Field(default=0)


class SocialWebhookIngestResponse(BaseModel):
    """Webhook ingest summary."""

    received: int = Field(default=0)
    queued: int = Field(default=0)
    duplicates: int = Field(default=0)

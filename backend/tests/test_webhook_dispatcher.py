from __future__ import annotations

from datetime import UTC, datetime
import json
from unittest.mock import patch

import httpx
import pytest

from app.core.config import settings
from app.services.webhook_dispatcher import WebhookDispatcher


@pytest.mark.asyncio
async def test_webhook_failures_are_queued(tmp_path):
    queue_file = tmp_path / "retry_queue.json"
    dead_letter_file = tmp_path / "dead_letter.jsonl"

    old_urls = list(settings.webhook_urls)
    old_retry_attempts = settings.webhook_retry_attempts
    old_retry_backoff = settings.webhook_retry_backoff_seconds
    old_queue_file = settings.webhook_queue_file
    old_dead_letter_file = settings.webhook_dead_letter_file

    settings.webhook_urls = ["https://example.com/webhook"]
    settings.webhook_retry_attempts = 3
    settings.webhook_retry_backoff_seconds = 0
    settings.webhook_queue_file = str(queue_file)
    settings.webhook_dead_letter_file = str(dead_letter_file)

    async def fake_post(self, url, **kwargs):  # noqa: ARG001
        request = httpx.Request("POST", str(url))
        raise httpx.ConnectError("network down", request=request)

    try:
        dispatcher = WebhookDispatcher()
        with patch.object(httpx.AsyncClient, "post", new=fake_post):
            result = await dispatcher.dispatch("scheduled_pipeline_success", {"handle": "@targetacct"})
    finally:
        settings.webhook_urls = old_urls
        settings.webhook_retry_attempts = old_retry_attempts
        settings.webhook_retry_backoff_seconds = old_retry_backoff
        settings.webhook_queue_file = old_queue_file
        settings.webhook_dead_letter_file = old_dead_letter_file

    assert result["sent"] == 1
    assert result["delivered"] == 0
    assert result["queued"] == 1
    queued = json.loads(queue_file.read_text(encoding="utf-8"))
    assert len(queued) == 1
    assert queued[0]["attempts"] == 1


@pytest.mark.asyncio
async def test_webhook_dead_letter_after_max_attempts(tmp_path):
    queue_file = tmp_path / "retry_queue.json"
    dead_letter_file = tmp_path / "dead_letter.jsonl"

    old_urls = list(settings.webhook_urls)
    old_retry_attempts = settings.webhook_retry_attempts
    old_retry_backoff = settings.webhook_retry_backoff_seconds
    old_queue_file = settings.webhook_queue_file
    old_dead_letter_file = settings.webhook_dead_letter_file

    settings.webhook_urls = ["https://example.com/webhook"]
    settings.webhook_retry_attempts = 2
    settings.webhook_retry_backoff_seconds = 0
    settings.webhook_queue_file = str(queue_file)
    settings.webhook_dead_letter_file = str(dead_letter_file)

    async def fake_post(self, url, **kwargs):  # noqa: ARG001
        request = httpx.Request("POST", str(url))
        raise httpx.ConnectError("network down", request=request)

    now = datetime.now(UTC).isoformat()
    queue_file.write_text(
        json.dumps(
            [
                {
                    "event_type": "scheduled_pipeline_failed",
                    "payload": {"handle": "@targetacct"},
                    "url": "https://example.com/webhook",
                    "attempts": 1,
                    "created_at": now,
                    "updated_at": now,
                    "next_attempt_at": now,
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    try:
        dispatcher = WebhookDispatcher()
        with patch.object(httpx.AsyncClient, "post", new=fake_post):
            drain = await dispatcher.drain_retry_queue()
    finally:
        settings.webhook_urls = old_urls
        settings.webhook_retry_attempts = old_retry_attempts
        settings.webhook_retry_backoff_seconds = old_retry_backoff
        settings.webhook_queue_file = old_queue_file
        settings.webhook_dead_letter_file = old_dead_letter_file

    assert drain["processed"] == 1
    assert drain["dead_lettered"] == 1
    assert drain["pending"] == 0
    pending_queue = json.loads(queue_file.read_text(encoding="utf-8"))
    assert pending_queue == []
    dead_lines = dead_letter_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(dead_lines) == 1
    dead_payload = json.loads(dead_lines[0])
    assert dead_payload["event_type"] == "scheduled_pipeline_failed"
    assert dead_payload["attempts"] == 2


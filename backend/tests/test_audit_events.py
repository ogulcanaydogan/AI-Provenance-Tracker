"""Tests for the AuditEventStore persistence layer."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import settings
from app.services.audit_events import AuditEventStore, audit_event_store


# ── log_event ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_log_event_returns_id() -> None:
    event_id = await audit_event_store.log_event(event_type="test_event")
    assert isinstance(event_id, int)


@pytest.mark.asyncio
async def test_log_event_stores_all_fields() -> None:
    event_id = await audit_event_store.log_event(
        event_type="detection.completed",
        severity="info",
        source="api",
        actor_id="user-123",
        request_id="req-456",
        payload={"analysis_id": "abc-789"},
    )
    items, total = await audit_event_store.list_events(limit=10, offset=0)
    assert total == 1
    item = items[0]
    assert item["id"] == event_id
    assert item["event_type"] == "detection.completed"
    assert item["severity"] == "info"
    assert item["source"] == "api"
    assert item["actor_id"] == "user-123"
    assert item["request_id"] == "req-456"
    assert item["payload"] == {"analysis_id": "abc-789"}
    assert "created_at" in item


@pytest.mark.asyncio
async def test_log_event_returns_none_when_disabled() -> None:
    original = settings.audit_events_enabled
    try:
        settings.audit_events_enabled = False
        result = await audit_event_store.log_event(event_type="should_be_skipped")
        assert result is None
    finally:
        settings.audit_events_enabled = original


@pytest.mark.asyncio
async def test_log_event_with_default_values() -> None:
    await audit_event_store.log_event(event_type="simple")
    items, _ = await audit_event_store.list_events(limit=10, offset=0)
    item = items[0]
    assert item["severity"] == "info"
    assert item["source"] == "api"
    assert item["actor_id"] is None
    assert item["request_id"] is None
    assert item["payload"] == {}


# ── safe_log_event ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_safe_log_event_does_not_raise_on_failure() -> None:
    store = AuditEventStore()
    with patch.object(
        store, "log_event", new_callable=AsyncMock, side_effect=RuntimeError("db down")
    ):
        await store.safe_log_event(event_type="fail_event")
        # no exception should propagate


@pytest.mark.asyncio
async def test_safe_log_event_logs_warning_on_failure() -> None:
    store = AuditEventStore()
    with (
        patch.object(
            store, "log_event", new_callable=AsyncMock, side_effect=RuntimeError("db down")
        ),
        patch("app.services.audit_events.logger") as mock_logger,
    ):
        await store.safe_log_event(event_type="fail_event")
        mock_logger.warning.assert_called_once()


# ── list_events ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_events_returns_paginated() -> None:
    for i in range(5):
        await audit_event_store.log_event(event_type=f"event-{i}")
    items, total = await audit_event_store.list_events(limit=2, offset=0)
    assert total == 5
    assert len(items) == 2


@pytest.mark.asyncio
async def test_list_events_filters_by_event_type() -> None:
    await audit_event_store.log_event(event_type="detection.text")
    await audit_event_store.log_event(event_type="detection.image")
    await audit_event_store.log_event(event_type="detection.text")

    items, total = await audit_event_store.list_events(
        limit=10, offset=0, event_type="detection.text"
    )
    assert total == 2
    assert all(item["event_type"] == "detection.text" for item in items)


@pytest.mark.asyncio
async def test_list_events_filters_by_severity() -> None:
    await audit_event_store.log_event(event_type="a", severity="info")
    await audit_event_store.log_event(event_type="b", severity="warning")
    await audit_event_store.log_event(event_type="c", severity="info")

    items, total = await audit_event_store.list_events(limit=10, offset=0, severity="warning")
    assert total == 1
    assert items[0]["event_type"] == "b"


@pytest.mark.asyncio
async def test_list_events_combined_filters() -> None:
    await audit_event_store.log_event(event_type="detection.text", severity="info")
    await audit_event_store.log_event(event_type="detection.text", severity="warning")
    await audit_event_store.log_event(event_type="detection.image", severity="warning")

    items, total = await audit_event_store.list_events(
        limit=10, offset=0, event_type="detection.text", severity="warning"
    )
    assert total == 1
    assert items[0]["event_type"] == "detection.text"
    assert items[0]["severity"] == "warning"


@pytest.mark.asyncio
async def test_list_events_newest_first() -> None:
    await audit_event_store.log_event(event_type="first")
    await audit_event_store.log_event(event_type="second")
    await audit_event_store.log_event(event_type="third")

    items, _ = await audit_event_store.list_events(limit=10, offset=0)
    assert items[0]["event_type"] == "third"
    assert items[2]["event_type"] == "first"


# ── reset ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reset_clears_events() -> None:
    await audit_event_store.log_event(event_type="to_be_cleared")
    _, total_before = await audit_event_store.list_events(limit=1, offset=0)
    assert total_before == 1

    await audit_event_store.reset()
    _, total_after = await audit_event_store.list_events(limit=1, offset=0)
    assert total_after == 0

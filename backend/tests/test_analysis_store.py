"""Tests for the AnalysisStore persistence layer."""

from __future__ import annotations

import hashlib

import pytest
from pydantic import BaseModel

from app.services.analysis_store import AnalysisStore, analysis_store


class FakeResult(BaseModel):
    """Minimal pydantic model that acts like a detection result."""

    is_ai_generated: bool = True
    confidence: float = 0.85
    model_prediction: str | None = "gpt-4"
    explanation: str = "Test detection result."


# ── save + get round-trip ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_save_text_result_returns_id() -> None:
    aid = await analysis_store.save_text_result("hello world", FakeResult())
    assert isinstance(aid, str) and len(aid) > 0


@pytest.mark.asyncio
async def test_save_text_result_and_get_record() -> None:
    aid = await analysis_store.save_text_result("test text", FakeResult(confidence=0.9))
    record = await analysis_store.get_record(aid)
    assert record is not None
    assert record.analysis_id == aid
    assert record.content_type == "text"
    assert record.result["confidence"] == 0.9
    assert record.content_hash == hashlib.sha256(b"test text").hexdigest()
    assert record.input_size == len("test text")


@pytest.mark.asyncio
async def test_save_image_result_stores_filename() -> None:
    data = b"\x89PNG fake image bytes"
    aid = await analysis_store.save_image_result(data, "test.png", FakeResult())
    record = await analysis_store.get_record(aid)
    assert record is not None
    assert record.filename == "test.png"
    assert record.content_type == "image"
    assert record.input_size == len(data)


@pytest.mark.asyncio
async def test_save_audio_result_stores_hash() -> None:
    data = b"RIFF fake audio bytes"
    aid = await analysis_store.save_audio_result(data, "test.wav", FakeResult())
    record = await analysis_store.get_record(aid)
    assert record is not None
    assert record.content_hash == hashlib.sha256(data).hexdigest()
    assert record.content_type == "audio"


@pytest.mark.asyncio
async def test_save_video_result_stores_size() -> None:
    data = b"\x00\x00\x00\x1c ftypmp42"
    aid = await analysis_store.save_video_result(data, "test.mp4", FakeResult())
    record = await analysis_store.get_record(aid)
    assert record is not None
    assert record.input_size == len(data)
    assert record.content_type == "video"


@pytest.mark.asyncio
async def test_get_record_returns_none_for_missing_id() -> None:
    assert await analysis_store.get_record("nonexistent-id-000") is None


# ── get_history ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_history_returns_reverse_chronological() -> None:
    for i in range(3):
        await analysis_store.save_text_result(f"text-{i}", FakeResult())
    items, total = await analysis_store.get_history(limit=10, offset=0)
    assert total == 3
    assert len(items) == 3
    # newest first: items[0].created_at > items[1].created_at
    assert items[0]["created_at"] >= items[1]["created_at"]


@pytest.mark.asyncio
async def test_get_history_filters_by_content_type() -> None:
    await analysis_store.save_text_result("text", FakeResult())
    await analysis_store.save_image_result(b"img", "img.png", FakeResult())
    items, total = await analysis_store.get_history(limit=10, offset=0, content_type="text")
    assert total == 1
    assert items[0]["content_type"] == "text"


@pytest.mark.asyncio
async def test_get_history_pagination() -> None:
    for i in range(5):
        await analysis_store.save_text_result(f"text-{i}", FakeResult())
    items, total = await analysis_store.get_history(limit=2, offset=0)
    assert total == 5
    assert len(items) == 2
    items2, _ = await analysis_store.get_history(limit=2, offset=2)
    assert len(items2) == 2
    # No overlap
    ids_page1 = {it["analysis_id"] for it in items}
    ids_page2 = {it["analysis_id"] for it in items2}
    assert ids_page1.isdisjoint(ids_page2)


# ── get_stats ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_stats_empty_store() -> None:
    stats = await analysis_store.get_stats()
    assert stats["total_analyses"] == 0
    assert stats["average_confidence"] == 0.0


@pytest.mark.asyncio
async def test_get_stats_with_mixed_records() -> None:
    await analysis_store.save_text_result(
        "ai text", FakeResult(is_ai_generated=True, confidence=0.9)
    )
    await analysis_store.save_text_result(
        "human text", FakeResult(is_ai_generated=False, confidence=0.1)
    )
    await analysis_store.save_image_result(
        b"img", "img.png", FakeResult(is_ai_generated=True, confidence=0.8)
    )

    stats = await analysis_store.get_stats()
    assert stats["total_analyses"] == 3
    assert stats["ai_detected_count"] == 2
    assert stats["human_detected_count"] == 1
    assert stats["by_type"]["text"] == 2
    assert stats["by_type"]["image"] == 1
    assert stats["average_confidence"] == pytest.approx(0.6, abs=0.01)


# ── get_dashboard ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_dashboard_empty() -> None:
    dashboard = await analysis_store.get_dashboard(days=7)
    assert dashboard["window_days"] == 7
    assert dashboard["summary"]["total_analyses_window"] == 0
    assert len(dashboard["timeline"]) == 7


@pytest.mark.asyncio
async def test_get_dashboard_with_records() -> None:
    for _ in range(3):
        await analysis_store.save_text_result("t", FakeResult(is_ai_generated=True, confidence=0.8))
    for _ in range(2):
        await analysis_store.save_text_result(
            "t", FakeResult(is_ai_generated=False, confidence=0.2)
        )

    dashboard = await analysis_store.get_dashboard(days=7)
    summary = dashboard["summary"]
    assert summary["total_analyses_all_time"] == 5
    assert summary["total_analyses_window"] == 5
    assert summary["ai_detected_window"] == 3
    assert summary["human_detected_window"] == 2
    assert summary["ai_rate_window"] == pytest.approx(0.6, abs=0.01)


@pytest.mark.asyncio
async def test_get_dashboard_top_models() -> None:
    await analysis_store.save_text_result("t", FakeResult(model_prediction="gpt-4"))
    await analysis_store.save_text_result("t", FakeResult(model_prediction="gpt-4"))
    await analysis_store.save_text_result("t", FakeResult(model_prediction="claude-3"))

    dashboard = await analysis_store.get_dashboard(days=7)
    top_models = dashboard["top_models_window"]
    assert len(top_models) >= 1
    assert top_models[0]["model"] == "gpt-4"
    assert top_models[0]["count"] == 2


@pytest.mark.asyncio
async def test_get_dashboard_clamps_days() -> None:
    dashboard = await analysis_store.get_dashboard(days=200)
    assert dashboard["window_days"] == 90


# ── reset ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reset_clears_records() -> None:
    await analysis_store.save_text_result("text", FakeResult())
    stats_before = await analysis_store.get_stats()
    assert stats_before["total_analyses"] == 1

    await analysis_store.reset()
    stats_after = await analysis_store.get_stats()
    assert stats_after["total_analyses"] == 0


# ── max_items eviction ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_max_items_eviction() -> None:
    small_store = AnalysisStore(max_items=3)
    small_store._initialized = True  # skip re-init since conftest already did it
    ids = []
    for i in range(5):
        aid = await small_store.save_text_result(f"text-{i}", FakeResult())
        ids.append(aid)

    # oldest 2 should have been evicted
    assert await small_store.get_record(ids[0]) is None
    assert await small_store.get_record(ids[1]) is None
    # newest 3 remain
    assert await small_store.get_record(ids[2]) is not None
    assert await small_store.get_record(ids[3]) is not None
    assert await small_store.get_record(ids[4]) is not None


# ── _to_history_item structure ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_history_item_structure() -> None:
    aid = await analysis_store.save_text_result(
        "test",
        FakeResult(
            is_ai_generated=True, confidence=0.85, model_prediction="gpt-4", explanation="Test."
        ),
        source="extension",
        source_url="https://example.com",
    )
    items, _ = await analysis_store.get_history(limit=1, offset=0)
    item = items[0]

    assert item["analysis_id"] == aid
    assert item["content_type"] == "text"
    assert item["is_ai_generated"] is True
    assert item["confidence"] == 0.85
    assert item["model_prediction"] == "gpt-4"
    assert item["explanation"] == "Test."
    assert item["source"] == "extension"
    assert item["source_url"] == "https://example.com"
    assert "created_at" in item

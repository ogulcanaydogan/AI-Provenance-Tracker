import io
import json
import math
import struct
import wave
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from httpx import AsyncClient
from PIL import Image

from app.core.config import settings
from app.middleware.rate_limiter import rate_limiter


def _create_test_png() -> bytes:
    image = Image.new("RGB", (32, 32), color=(255, 100, 50))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _create_test_wav(duration_seconds: float = 0.6, sample_rate: int = 16000) -> bytes:
    frame_count = int(duration_seconds * sample_rate)
    amplitude = 0.35
    frequency = 440.0

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 16-bit PCM
        wav_file.setframerate(sample_rate)

        frames = bytearray()
        for n in range(frame_count):
            value = amplitude * math.sin(2.0 * math.pi * frequency * (n / sample_rate))
            frames.extend(struct.pack("<h", int(value * 32767)))
        wav_file.writeframes(bytes(frames))

    return buffer.getvalue()


def _create_test_mp4() -> bytes:
    # Minimal MP4-like payload with ftyp box plus synthetic media bytes.
    header = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
    body = b"\x00\x00\x00\x08free" + b"videodata12345678" * 5000
    return header + body


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


@pytest.mark.asyncio
async def test_text_detection_missing_body(client: AsyncClient):
    response = await client.post("/api/v1/detect/text", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_text_detection_success_returns_analysis_id(client: AsyncClient):
    response = await client.post(
        "/api/v1/detect/text",
        json={"text": "This is a sufficiently long sample text for API testing." * 4},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_id"]
    assert "confidence" in payload
    assert "analysis" in payload
    assert "explanation" in payload
    assert "consensus" in payload
    assert payload["consensus"]["providers"][0]["provider"] == "internal"


@pytest.mark.asyncio
async def test_image_detection_no_file(client: AsyncClient):
    response = await client.post("/api/v1/detect/image")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_image_detection_wrong_type(client: AsyncClient):
    response = await client.post(
        "/api/v1/detect/image",
        files={"file": ("test.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_audio_detection_wrong_type(client: AsyncClient):
    response = await client.post(
        "/api/v1/detect/audio",
        files={"file": ("test.txt", b"not audio", "text/plain")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_audio_detection_success_returns_analysis_id(client: AsyncClient):
    response = await client.post(
        "/api/v1/detect/audio",
        files={"file": ("sample.wav", _create_test_wav(), "audio/wav")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_id"]
    assert payload["filename"] == "sample.wav"
    assert "analysis" in payload
    assert payload["analysis"]["sample_rate"] == 16000
    assert payload["analysis"]["duration_seconds"] > 0.0


@pytest.mark.asyncio
async def test_audio_detection_updates_stats(client: AsyncClient):
    detect_response = await client.post(
        "/api/v1/detect/audio",
        files={"file": ("sample.wav", _create_test_wav(), "audio/wav")},
    )
    assert detect_response.status_code == 200

    stats_response = await client.get("/api/v1/analyze/stats")
    assert stats_response.status_code == 200
    stats_payload = stats_response.json()
    assert stats_payload["total_analyses"] == 1
    assert stats_payload["by_type"]["audio"] == 1


@pytest.mark.asyncio
async def test_video_detection_wrong_type(client: AsyncClient):
    response = await client.post(
        "/api/v1/detect/video",
        files={"file": ("test.txt", b"not video", "text/plain")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_video_detection_success_returns_analysis_id(client: AsyncClient):
    response = await client.post(
        "/api/v1/detect/video",
        files={"file": ("clip.mp4", _create_test_mp4(), "video/mp4")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_id"]
    assert payload["filename"] == "clip.mp4"
    assert "analysis" in payload
    assert payload["analysis"]["file_size_mb"] > 0.0
    assert "signature_flags" in payload["analysis"]


@pytest.mark.asyncio
async def test_video_detection_updates_stats(client: AsyncClient):
    detect_response = await client.post(
        "/api/v1/detect/video",
        files={"file": ("clip.mp4", _create_test_mp4(), "video/mp4")},
    )
    assert detect_response.status_code == 200

    stats_response = await client.get("/api/v1/analyze/stats")
    assert stats_response.status_code == 200
    stats_payload = stats_response.json()
    assert stats_payload["total_analyses"] == 1
    assert stats_payload["by_type"]["video"] == 1


@pytest.mark.asyncio
async def test_analysis_detailed_history_and_stats_flow(client: AsyncClient):
    detect_response = await client.post(
        "/api/v1/detect/text",
        json={"text": "Detection data for history and stats checks." * 5},
    )
    assert detect_response.status_code == 200
    analysis_id = detect_response.json()["analysis_id"]

    detailed_response = await client.post(
        "/api/v1/analyze/detailed",
        json={"content_id": analysis_id, "include_metadata": True, "include_timeline": True},
    )
    assert detailed_response.status_code == 200
    detailed_payload = detailed_response.json()
    assert detailed_payload["content_id"] == analysis_id
    assert detailed_payload["analysis_type"] == "text"
    assert detailed_payload["details"]["result"]["analysis_id"] == analysis_id
    assert detailed_payload["metadata"]["timeline"][0]["event"] == "content_analyzed"

    history_response = await client.get("/api/v1/analyze/history?limit=10&offset=0")
    assert history_response.status_code == 200
    history_payload = history_response.json()
    assert history_payload["total"] == 1
    assert history_payload["items"][0]["analysis_id"] == analysis_id

    stats_response = await client.get("/api/v1/analyze/stats")
    assert stats_response.status_code == 200
    stats_payload = stats_response.json()
    assert stats_payload["total_analyses"] == 1
    assert stats_payload["by_type"]["text"] == 1


@pytest.mark.asyncio
async def test_analysis_detailed_not_found(client: AsyncClient):
    response = await client.post(
        "/api/v1/analyze/detailed",
        json={"content_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_url_detection_text(client: AsyncClient):
    async def fake_get(self, url, **kwargs):  # noqa: ARG001
        request = httpx.Request("GET", url)
        return httpx.Response(
            status_code=200,
            headers={"content-type": "text/html; charset=utf-8"},
            text="<html><body><h1>Article</h1><p>This is URL sourced content for testing.</p></body></html>",
            request=request,
        )

    with patch.object(httpx.AsyncClient, "get", new=fake_get):
        response = await client.post(
            "/api/v1/detect/url",
            json={"url": "https://example.com/article"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["content_type"] == "text"
    assert payload["analysis_id"]
    assert payload["result"]["analysis_id"] == payload["analysis_id"]
    assert payload["text_length"] > 0


@pytest.mark.asyncio
async def test_url_detection_image(client: AsyncClient):
    image_bytes = _create_test_png()

    async def fake_get(self, url, **kwargs):  # noqa: ARG001
        request = httpx.Request("GET", url)
        return httpx.Response(
            status_code=200,
            headers={"content-type": "image/png"},
            content=image_bytes,
            request=request,
        )

    with patch.object(httpx.AsyncClient, "get", new=fake_get):
        response = await client.post(
            "/api/v1/detect/url",
            json={"url": "https://example.com/image.png"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["content_type"] == "image"
    assert payload["analysis_id"]
    assert payload["result"]["analysis_id"] == payload["analysis_id"]


@pytest.mark.asyncio
async def test_rate_limit_enforced(client: AsyncClient):
    settings.rate_limit_requests = 2
    settings.rate_limit_window_seconds = 60
    rate_limiter._hits.clear()

    body = {"text": "Rate limit test content that is long enough." * 3}

    first = await client.post("/api/v1/detect/text", json=body)
    second = await client.post("/api/v1/detect/text", json=body)
    third = await client.post("/api/v1/detect/text", json=body)

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.headers.get("retry-after") is not None


@pytest.mark.asyncio
async def test_api_key_required_blocks_unauthorized_requests(client: AsyncClient):
    old_required = settings.require_api_key
    old_keys = list(settings.api_keys)
    settings.require_api_key = True
    settings.api_keys = ["test-key"]
    rate_limiter._hits.clear()
    rate_limiter._daily_points.clear()
    try:
        blocked = await client.post(
            "/api/v1/detect/text",
            json={"text": "API key requirement test text." * 4},
        )
        allowed = await client.post(
            "/api/v1/detect/text",
            headers={settings.api_key_header: "test-key"},
            json={"text": "API key requirement test text." * 4},
        )
    finally:
        settings.require_api_key = old_required
        settings.api_keys = old_keys

    assert blocked.status_code == 401
    assert allowed.status_code == 200


@pytest.mark.asyncio
async def test_batch_text_detection_success(client: AsyncClient):
    response = await client.post(
        "/api/v1/batch/text",
        json={
            "items": [
                {"item_id": "a", "text": "Batch text sample one. " * 10},
                {"item_id": "b", "text": "Batch text sample two. " * 10},
            ],
            "stop_on_error": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["succeeded"] == 2
    assert payload["failed"] == 0
    assert payload["items"][0]["status"] == "ok"
    assert payload["items"][0]["result"]["analysis_id"]


@pytest.mark.asyncio
async def test_batch_text_detection_rejects_oversized_batch(client: AsyncClient):
    old_max = settings.max_batch_items
    settings.max_batch_items = 1
    try:
        response = await client.post(
            "/api/v1/batch/text",
            json={
                "items": [
                    {"item_id": "a", "text": "Batch text sample one. " * 10},
                    {"item_id": "b", "text": "Batch text sample two. " * 10},
                ]
            },
        )
    finally:
        settings.max_batch_items = old_max

    assert response.status_code == 400
    assert "maximum size" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_dashboard_endpoint_returns_timeline(client: AsyncClient):
    detect_response = await client.post(
        "/api/v1/detect/text",
        json={"text": "Dashboard metrics test content." * 6},
    )
    assert detect_response.status_code == 200

    dashboard_response = await client.get("/api/v1/analyze/dashboard?days=7")
    assert dashboard_response.status_code == 200
    payload = dashboard_response.json()
    assert payload["window_days"] == 7
    assert payload["summary"]["total_analyses_window"] == 1
    assert len(payload["timeline"]) == 7
    assert "by_type_window" in payload


@pytest.mark.asyncio
async def test_evaluation_endpoint_returns_registered_reports(client: AsyncClient, tmp_path: Path):
    old_dir = settings.calibration_reports_dir
    settings.calibration_reports_dir = str(tmp_path)
    try:
        payload = {
            "generated_at": "2026-02-15T12:00:00+00:00",
            "content_type": "text",
            "sample_count": 40,
            "recommended_threshold": 0.55,
            "best_metrics": {
                "precision": 0.8,
                "recall": 0.75,
                "f1": 0.77,
                "accuracy": 0.78,
            },
        }
        report_path = tmp_path / "text" / "sample_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload), encoding="utf-8")

        response = await client.get("/api/v1/analyze/evaluation?days=90")
    finally:
        settings.calibration_reports_dir = old_dir

    assert response.status_code == 200
    data = response.json()
    assert data["total_reports"] == 1
    assert data["by_content_type"]["text"] == 1
    assert data["latest_by_content_type"]["text"]["precision"] == 0.8


@pytest.mark.asyncio
async def test_audit_events_endpoint_returns_detection_event(client: AsyncClient):
    detect_response = await client.post(
        "/api/v1/detect/text",
        json={"text": "Audit event verification text sample." * 6},
    )
    assert detect_response.status_code == 200

    response = await client.get("/api/v1/analyze/audit-events?limit=20")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert any(item["event_type"] == "detection.completed" for item in payload["items"])


@pytest.mark.asyncio
async def test_audit_events_filter_by_event_type(client: AsyncClient):
    detect_response = await client.post(
        "/api/v1/detect/text",
        json={"text": "Audit event filter test text." * 6},
    )
    assert detect_response.status_code == 200

    response = await client.get("/api/v1/analyze/audit-events?event_type=detection.completed")
    assert response.status_code == 200
    payload = response.json()
    assert payload["event_type"] == "detection.completed"
    assert payload["total"] >= 1
    assert all(item["event_type"] == "detection.completed" for item in payload["items"])


# ---------------------------------------------------------------------------
# Image detection – success, stats, and size-limit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_image_detection_success_returns_analysis_id(client: AsyncClient):
    """Upload a valid PNG and verify a full detection response."""
    png_bytes = _create_test_png()
    response = await client.post(
        "/api/v1/detect/image",
        files={"file": ("photo.png", png_bytes, "image/png")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_id"]
    assert payload["filename"] == "photo.png"
    assert "analysis" in payload
    assert "frequency_anomaly" in payload["analysis"]
    assert "artifact_score" in payload["analysis"]
    assert "metadata_flags" in payload["analysis"]
    assert payload["dimensions"][0] == 32
    assert payload["dimensions"][1] == 32


@pytest.mark.asyncio
async def test_image_detection_updates_stats(client: AsyncClient):
    """Stats reflect an image detection after it completes."""
    detect_response = await client.post(
        "/api/v1/detect/image",
        files={"file": ("photo.png", _create_test_png(), "image/png")},
    )
    assert detect_response.status_code == 200

    stats_response = await client.get("/api/v1/analyze/stats")
    assert stats_response.status_code == 200
    stats_payload = stats_response.json()
    assert stats_payload["total_analyses"] == 1
    assert stats_payload["by_type"]["image"] == 1


@pytest.mark.asyncio
async def test_image_detection_rejects_oversized_file(client: AsyncClient):
    """Image exceeding max_image_size_mb is rejected with 400."""
    old_max = settings.max_image_size_mb
    settings.max_image_size_mb = 0  # any file will be too large
    try:
        response = await client.post(
            "/api/v1/detect/image",
            files={"file": ("photo.png", _create_test_png(), "image/png")},
        )
    finally:
        settings.max_image_size_mb = old_max
    assert response.status_code == 400
    assert "exceeds maximum size" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# URL detection – edge-case tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_url_detection_fetch_failure(client: AsyncClient):
    """URL fetch that raises an HTTP error returns 400."""

    async def failing_get(self, url, **kwargs):  # noqa: ARG001
        raise httpx.ConnectError("Connection refused")

    with patch.object(httpx.AsyncClient, "get", new=failing_get):
        response = await client.post(
            "/api/v1/detect/url",
            json={"url": "https://unreachable.example.com/page"},
        )
    assert response.status_code == 400
    assert "failed to fetch" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_url_detection_remote_error_status(client: AsyncClient):
    """Remote server returning 404 is surfaced as 400."""

    async def not_found_get(self, url, **kwargs):  # noqa: ARG001
        request = httpx.Request("GET", url)
        return httpx.Response(status_code=404, request=request)

    with patch.object(httpx.AsyncClient, "get", new=not_found_get):
        response = await client.post(
            "/api/v1/detect/url",
            json={"url": "https://example.com/missing"},
        )
    assert response.status_code == 400
    assert "404" in response.json()["detail"]


@pytest.mark.asyncio
async def test_url_detection_empty_html(client: AsyncClient):
    """HTML page with no extractable text returns 400."""

    async def empty_html_get(self, url, **kwargs):  # noqa: ARG001
        request = httpx.Request("GET", url)
        return httpx.Response(
            status_code=200,
            headers={"content-type": "text/html"},
            text="<html><body><script>var x=1;</script></body></html>",
            request=request,
        )

    with patch.object(httpx.AsyncClient, "get", new=empty_html_get):
        response = await client.post(
            "/api/v1/detect/url",
            json={"url": "https://example.com/empty"},
        )
    assert response.status_code == 400
    assert "no analyzable text" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_url_detection_unsupported_content_type(client: AsyncClient):
    """Non-text, non-image content type returns 400."""

    async def pdf_get(self, url, **kwargs):  # noqa: ARG001
        request = httpx.Request("GET", url)
        return httpx.Response(
            status_code=200,
            headers={"content-type": "application/pdf"},
            content=b"%PDF-1.4 fake",
            request=request,
        )

    with patch.object(httpx.AsyncClient, "get", new=pdf_get):
        response = await client.post(
            "/api/v1/detect/url",
            json={"url": "https://example.com/doc.pdf"},
        )
    assert response.status_code == 400
    assert "unsupported content type" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Batch text – stop_on_error and partial failure tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_text_stop_on_error_halts_early(client: AsyncClient):
    """Batch with stop_on_error=True stops after first empty-text failure."""
    response = await client.post(
        "/api/v1/batch/text",
        json={
            "items": [
                {"item_id": "ok", "text": "Valid text for batch testing." * 10},
                {"item_id": "bad", "text": "   "},
                {"item_id": "skipped", "text": "This should be skipped." * 10},
            ],
            "stop_on_error": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["succeeded"] == 1
    assert payload["failed"] == 1
    # Third item should NOT have been processed
    assert len(payload["items"]) == 2
    assert payload["items"][0]["status"] == "ok"
    assert payload["items"][1]["status"] == "error"


@pytest.mark.asyncio
async def test_batch_text_partial_failure_continues(client: AsyncClient):
    """Batch with stop_on_error=False processes all items despite failures."""
    response = await client.post(
        "/api/v1/batch/text",
        json={
            "items": [
                {"item_id": "good1", "text": "Valid text content here." * 10},
                {"item_id": "empty", "text": "   "},
                {"item_id": "good2", "text": "Another valid text batch item." * 10},
            ],
            "stop_on_error": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert payload["succeeded"] == 2
    assert payload["failed"] == 1
    assert len(payload["items"]) == 3


# ---------------------------------------------------------------------------
# Video detection – size limit test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_video_detection_rejects_oversized_file(client: AsyncClient):
    """Video exceeding max_video_size_mb is rejected with 400."""
    old_max = settings.max_video_size_mb
    settings.max_video_size_mb = 0  # any file will be too large
    try:
        response = await client.post(
            "/api/v1/detect/video",
            files={"file": ("clip.mp4", _create_test_mp4(), "video/mp4")},
        )
    finally:
        settings.max_video_size_mb = old_max
    assert response.status_code == 400
    assert "exceeds maximum size" in response.json()["detail"].lower()

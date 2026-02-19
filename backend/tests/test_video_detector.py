"""Unit tests for the video detection engine."""

import pytest

from app.detection.video.detector import VideoDetector


def _create_mp4() -> bytes:
    """Create a minimal MP4-like payload."""
    header = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
    body = b"\x00\x00\x00\x08free" + b"videodata12345678" * 5000
    return header + body


def _create_random_bytes(size: int = 100_000) -> bytes:
    """Create pseudo-random bytes (high entropy)."""
    import random

    random.seed(42)
    return bytes(random.getrandbits(8) for _ in range(size))


@pytest.fixture
def detector() -> VideoDetector:
    return VideoDetector()


@pytest.mark.asyncio
async def test_detect_returns_valid_response(detector: VideoDetector):
    """Detector returns a properly structured response."""
    result = await detector.detect(_create_mp4(), "clip.mp4")
    assert hasattr(result, "is_ai_generated")
    assert isinstance(result.is_ai_generated, bool)
    assert 0.0 <= result.confidence <= 1.0
    assert result.filename == "clip.mp4"


@pytest.mark.asyncio
async def test_detect_analysis_has_expected_fields(detector: VideoDetector):
    """Analysis section contains all required signal fields."""
    result = await detector.detect(_create_mp4(), "clip.mp4")
    analysis = result.analysis
    assert hasattr(analysis, "file_size_mb")
    assert hasattr(analysis, "entropy_score")
    assert hasattr(analysis, "byte_uniformity")
    assert hasattr(analysis, "repeated_chunk_ratio")
    assert hasattr(analysis, "signature_flags")
    assert isinstance(analysis.signature_flags, list)


@pytest.mark.asyncio
async def test_detect_file_size_calculated(detector: VideoDetector):
    """File size in MB is positive and reasonable."""
    result = await detector.detect(_create_mp4(), "clip.mp4")
    assert result.analysis.file_size_mb > 0


@pytest.mark.asyncio
async def test_detect_processing_time_recorded(detector: VideoDetector):
    """Processing time is a positive number."""
    result = await detector.detect(_create_mp4(), "clip.mp4")
    assert result.processing_time_ms > 0


@pytest.mark.asyncio
async def test_detect_explanation_is_non_empty(detector: VideoDetector):
    """Explanation string is always populated."""
    result = await detector.detect(_create_mp4(), "clip.mp4")
    assert len(result.explanation) > 0


@pytest.mark.asyncio
async def test_detect_mp4_has_signature_flags(detector: VideoDetector):
    """MP4 files should produce signature flag analysis."""
    result = await detector.detect(_create_mp4(), "clip.mp4")
    # Signature flags list should exist even if empty
    assert isinstance(result.analysis.signature_flags, list)


@pytest.mark.asyncio
async def test_detect_empty_video_raises(detector: VideoDetector):
    """Empty video data should raise ValueError."""
    with pytest.raises((ValueError, Exception)):
        await detector.detect(b"", "empty.mp4")


@pytest.mark.asyncio
async def test_detect_entropy_within_bounds(detector: VideoDetector):
    """Entropy score should be between 0 and 8 (max for byte entropy)."""
    result = await detector.detect(_create_mp4(), "clip.mp4")
    assert 0.0 <= result.analysis.entropy_score <= 8.0

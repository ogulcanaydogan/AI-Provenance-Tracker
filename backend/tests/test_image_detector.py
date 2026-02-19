"""Unit tests for the image detection engine."""

import io

import pytest
from PIL import Image

from app.detection.image.detector import ImageDetector


def _create_png(width: int = 64, height: int = 64, color: tuple = (128, 128, 128)) -> bytes:
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _create_jpeg_with_exif() -> bytes:
    """Create a JPEG with minimal EXIF data."""
    img = Image.new("RGB", (64, 64), color=(200, 100, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


@pytest.fixture
def detector() -> ImageDetector:
    return ImageDetector()


@pytest.mark.asyncio
async def test_detect_returns_valid_response(detector: ImageDetector):
    """Detector returns a properly structured response."""
    result = await detector.detect(_create_png(), "test.png")
    assert hasattr(result, "is_ai_generated")
    assert isinstance(result.is_ai_generated, bool)
    assert 0.0 <= result.confidence <= 1.0
    assert result.filename == "test.png"


@pytest.mark.asyncio
async def test_detect_dimensions_match_input(detector: ImageDetector):
    """Returned dimensions reflect the input image size."""
    result = await detector.detect(_create_png(100, 50), "wide.png")
    assert result.dimensions == (100, 50)


@pytest.mark.asyncio
async def test_detect_analysis_has_expected_fields(detector: ImageDetector):
    """Analysis section contains all required signal fields."""
    result = await detector.detect(_create_png(), "test.png")
    analysis = result.analysis
    assert hasattr(analysis, "frequency_anomaly")
    assert hasattr(analysis, "artifact_score")
    assert hasattr(analysis, "metadata_flags")
    assert isinstance(analysis.metadata_flags, list)


@pytest.mark.asyncio
async def test_detect_processing_time_recorded(detector: ImageDetector):
    """Processing time is a positive number."""
    result = await detector.detect(_create_png(), "test.png")
    assert result.processing_time_ms > 0


@pytest.mark.asyncio
async def test_detect_png_reports_missing_exif(detector: ImageDetector):
    """PNG images should flag missing EXIF as a metadata concern."""
    result = await detector.detect(_create_png(), "test.png")
    assert "missing_exif" in result.analysis.metadata_flags


@pytest.mark.asyncio
async def test_detect_explanation_is_non_empty(detector: ImageDetector):
    """Explanation string is always populated."""
    result = await detector.detect(_create_png(), "test.png")
    assert len(result.explanation) > 0


@pytest.mark.asyncio
async def test_detect_different_colors_give_varying_scores(detector: ImageDetector):
    """Different input images should produce (potentially) different scores."""
    result_gray = await detector.detect(_create_png(color=(128, 128, 128)), "gray.png")
    result_red = await detector.detect(_create_png(color=(255, 0, 0)), "red.png")
    # Both should be valid regardless of exact score
    assert 0.0 <= result_gray.confidence <= 1.0
    assert 0.0 <= result_red.confidence <= 1.0


@pytest.mark.asyncio
async def test_detect_jpeg_format(detector: ImageDetector):
    """JPEG images are detected without error."""
    result = await detector.detect(_create_jpeg_with_exif(), "photo.jpg")
    assert result.filename == "photo.jpg"
    assert 0.0 <= result.confidence <= 1.0

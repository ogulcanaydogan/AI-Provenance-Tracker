import io

from PIL import Image

from app.detection.image.detector import ImageDetector


def _create_png() -> tuple[Image.Image, bytes]:
    image = Image.new("RGB", (100, 100), color="red")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return image, buffer.getvalue()


def test_metadata_flags_include_missing_exif_for_png():
    detector = ImageDetector()
    image, raw = _create_png()

    flags = detector._analyze_metadata(image, raw)

    assert "missing_exif" in flags


def test_compression_analysis_returns_expected_buckets():
    detector = ImageDetector()

    heavily = detector._analyze_compression(b"x" * (30 * 1024))
    moderate = detector._analyze_compression(b"x" * (120 * 1024))
    normal = detector._analyze_compression(b"x" * (600 * 1024))
    minimal = detector._analyze_compression(b"x" * (6000 * 1024))

    assert heavily == "heavily_compressed"
    assert moderate == "moderately_compressed"
    assert normal == "normal_compression"
    assert minimal == "minimal_compression"

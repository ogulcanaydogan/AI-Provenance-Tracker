"""Tests for image preprocessing utility functions."""

import io

import pytest
from PIL import Image

from app.utils.image_preprocessing import (
    load_image,
    resize_for_analysis,
    to_grayscale,
    to_rgb,
)


def _make_png_bytes(width: int = 100, height: int = 80, mode: str = "RGB") -> bytes:
    img = Image.new(mode, (width, height), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestLoadImage:
    def test_loads_valid_png(self):
        img = load_image(_make_png_bytes())
        assert isinstance(img, Image.Image)
        assert img.size == (100, 80)

    def test_loads_rgba_image(self):
        img = load_image(_make_png_bytes(mode="RGBA"))
        assert img.mode == "RGBA"

    def test_raises_on_invalid_bytes(self):
        with pytest.raises((OSError, ValueError)):
            load_image(b"not an image")


class TestResizeForAnalysis:
    def test_resizes_to_default_512(self):
        img = Image.new("RGB", (1000, 800))
        resized = resize_for_analysis(img)
        assert resized.size == (512, 512)

    def test_resizes_to_custom_size(self):
        img = Image.new("RGB", (300, 400))
        resized = resize_for_analysis(img, size=256)
        assert resized.size == (256, 256)


class TestToRgb:
    def test_converts_grayscale_to_rgb(self):
        img = Image.new("L", (50, 50))
        rgb = to_rgb(img)
        assert rgb.mode == "RGB"

    def test_keeps_rgb_as_rgb(self):
        img = Image.new("RGB", (50, 50))
        rgb = to_rgb(img)
        assert rgb.mode == "RGB"

    def test_converts_rgba_to_rgb(self):
        img = Image.new("RGBA", (50, 50))
        rgb = to_rgb(img)
        assert rgb.mode == "RGB"


class TestToGrayscale:
    def test_converts_rgb_to_grayscale(self):
        img = Image.new("RGB", (50, 50))
        gray = to_grayscale(img)
        assert gray.mode == "L"

    def test_keeps_grayscale(self):
        img = Image.new("L", (50, 50))
        gray = to_grayscale(img)
        assert gray.mode == "L"

"""Tests for schema constants (image limits)."""

from app.schemas.image import ALLOWED_IMAGE_TYPES, MAX_IMAGE_SIZE_BYTES


def test_allowed_image_types_contains_expected() -> None:
    assert "image/jpeg" in ALLOWED_IMAGE_TYPES
    assert "image/png" in ALLOWED_IMAGE_TYPES
    assert "image/webp" in ALLOWED_IMAGE_TYPES
    assert len(ALLOWED_IMAGE_TYPES) == 3


def test_max_image_size_is_10mb() -> None:
    assert MAX_IMAGE_SIZE_BYTES == 10 * 1024 * 1024

"""Pydantic models."""

from app.models.detection import (
    TextDetectionRequest,
    TextDetectionResponse,
    ImageDetectionResponse,
    DetectionAnalysis,
)

__all__ = [
      "TextDetectionRequest",
      "TextDetectionResponse",
      "ImageDetectionResponse",
      "DetectionAnalysis",
]

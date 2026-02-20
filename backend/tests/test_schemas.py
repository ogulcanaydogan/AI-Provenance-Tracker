"""Tests for schema models and utility functions."""

import pytest
from datetime import UTC, datetime

from pydantic import ValidationError

from app.schemas.common import DetectionSignal, DetectionResult, compute_verdict


class TestDetectionSignal:
    def test_valid_signal(self):
        signal = DetectionSignal(
            name="perplexity", score=0.75, weight=0.3, description="Low perplexity"
        )
        assert signal.name == "perplexity"
        assert signal.score == 0.75

    def test_score_bounds(self):
        with pytest.raises(ValidationError):
            DetectionSignal(name="x", score=1.5, weight=0.3, description="Bad")

    def test_weight_bounds(self):
        with pytest.raises(ValidationError):
            DetectionSignal(name="x", score=0.5, weight=-0.1, description="Bad")


class TestDetectionResult:
    def test_valid_result(self):
        result = DetectionResult(
            id="test-1",
            content_type="text",
            confidence_score=75.0,
            verdict="likely_ai",
            signals=[],
            summary="Test summary",
            analyzed_at=datetime.now(UTC),
        )
        assert result.verdict == "likely_ai"

    def test_confidence_out_of_range(self):
        with pytest.raises(ValidationError):
            DetectionResult(
                id="test-2",
                content_type="text",
                confidence_score=150.0,
                verdict="human",
                signals=[],
                summary="Bad",
                analyzed_at=datetime.now(UTC),
            )


class TestComputeVerdict:
    @pytest.mark.parametrize(
        "confidence, expected",
        [
            (5, "human"),
            (19, "human"),
            (20, "likely_human"),
            (39, "likely_human"),
            (40, "uncertain"),
            (59, "uncertain"),
            (60, "likely_ai"),
            (79, "likely_ai"),
            (80, "ai_generated"),
            (99, "ai_generated"),
        ],
    )
    def test_verdict_thresholds(self, confidence: float, expected: str):
        assert compute_verdict(confidence) == expected

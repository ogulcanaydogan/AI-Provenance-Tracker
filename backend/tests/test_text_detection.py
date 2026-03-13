"""Tests for text detection engine."""

from pathlib import Path

import pytest
from app.core.config import settings
from app.detection.text.detector import TextDetector


@pytest.fixture
def detector():
    """Create a text detector instance."""
    return TextDetector()


class TestTextDetector:
    """Test suite for TextDetector."""

    @pytest.mark.asyncio
    async def test_detect_returns_response(self, detector):
        """Test that detect returns a valid response."""
        text = "This is a sample text to analyze for AI detection purposes."
        result = await detector.detect(text)

        assert result is not None
        assert isinstance(result.is_ai_generated, bool)
        assert 0 <= result.confidence <= 1
        assert result.decision_band in {"human", "uncertain", "ai"}
        assert result.distance_to_threshold >= 0
        assert result.explanation is not None
        assert result.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_detect_short_text(self, detector):
        """Test detection with short text."""
        text = "Hello world."
        result = await detector.detect(text)

        assert result is not None
        assert result.decision_band == "uncertain"
        assert result.uncertainty_reason is not None

    @pytest.mark.asyncio
    async def test_detect_analysis_metrics(self, detector):
        """Test that analysis metrics are populated."""
        text = """
        This is a longer piece of text that should provide enough data
        for the detection algorithms to analyze properly. It contains
        multiple sentences with varying lengths and vocabulary to test
        the burstiness and perplexity calculations.
        """
        result = await detector.detect(text)

        assert result.analysis is not None
        assert result.analysis.perplexity > 0
        assert 0 <= result.analysis.burstiness <= 1
        assert 0 <= result.analysis.vocabulary_richness <= 1
        assert result.analysis.average_sentence_length > 0
        assert 0 <= result.analysis.punctuation_diversity <= 1
        assert 0 <= result.analysis.stopword_ratio <= 1
        assert result.analysis.sentence_length_variance >= 0

    @pytest.mark.asyncio
    async def test_typical_ai_text_patterns(self, detector):
        """Test with text that has typical AI patterns."""
        # Text with uniform sentence structure and low variation
        ai_like_text = """
        The quick brown fox jumps over the lazy dog.
        The fast red cat runs under the tired dog.
        The slow gray bird flies above the sleepy dog.
        The swift blue fish swims around the calm dog.
        """
        result = await detector.detect(ai_like_text)

        # Should detect low burstiness
        assert result.analysis.burstiness < 0.5

    @pytest.mark.asyncio
    async def test_typical_human_text_patterns(self, detector):
        """Test with text that has typical human patterns."""
        # Text with varied sentence structure
        human_like_text = """
        Wait, what? I can't believe this actually happened yesterday!
        So there I was, just minding my own business, when suddenly
        everything changed. It was absolutely wild - you should have
        seen the look on everyone's faces. Crazy, right?!
        """
        result = await detector.detect(human_like_text)

        # Should detect higher burstiness
        assert result.analysis.burstiness > 0.3


class TestTextPreprocessing:
    """Test text preprocessing functions."""

    def test_preprocess_removes_extra_whitespace(self):
        detector = TextDetector()
        text = "Hello    world   test"
        result = detector._preprocess_text(text)
        assert "    " not in result
        assert "   " not in result

    def test_split_sentences(self):
        detector = TextDetector()
        text = "First sentence. Second sentence! Third sentence?"
        sentences = detector._split_sentences(text)
        assert len(sentences) == 3

    def test_tokenize(self):
        detector = TextDetector()
        text = "Hello World Test"
        words = detector._tokenize(text)
        assert words == ["hello", "world", "test"]

    def test_apply_decision_band_threshold_regions(self):
        detector = TextDetector()
        band_ai, _, _ = detector.apply_decision_band(
            confidence=0.9,
            threshold=0.5,
            word_count=120,
            sentence_count=6,
        )
        band_human, _, _ = detector.apply_decision_band(
            confidence=0.1,
            threshold=0.5,
            word_count=120,
            sentence_count=6,
        )
        band_uncertain, _, reason = detector.apply_decision_band(
            confidence=0.52,
            threshold=0.5,
            word_count=120,
            sentence_count=6,
        )

        assert band_ai == "ai"
        assert band_human == "human"
        assert band_uncertain == "uncertain"
        assert reason is not None

    def test_domain_profile_override_resolution(self):
        detector = TextDetector()
        detector._calibration_profile["domain_profiles"] = {
            "news": {"decision_threshold": 0.22, "uncertainty_margin": 0.03},
            "general": {"decision_threshold": 0.48, "uncertainty_margin": 0.05},
        }

        news_profile, news_domain = detector._resolve_calibration_profile("news")
        general_profile, general_domain = detector._resolve_calibration_profile("general")

        assert news_domain == "news"
        assert general_domain == "general"
        assert news_profile["decision_threshold"] == 0.22
        assert general_profile["decision_threshold"] == 0.48

    def test_resolve_model_id_prefers_existing_local_path(self, tmp_path: Path):
        detector = TextDetector()
        model_dir = tmp_path / "dummy-model"
        model_dir.mkdir(parents=True, exist_ok=True)

        original_path = settings.text_detection_model_path
        original_model = settings.text_detection_model
        settings.text_detection_model_path = str(model_dir)
        settings.text_detection_model = "distilroberta-base"
        try:
            resolved = detector._resolve_model_id()
        finally:
            settings.text_detection_model_path = original_path
            settings.text_detection_model = original_model

        assert resolved == str(model_dir)

    def test_apply_calibration_map_identity_without_map(self):
        detector = TextDetector()
        profile = {"decision_threshold": 0.5}
        score = detector._apply_calibration_map(0.61, profile)
        assert score == pytest.approx(0.61, abs=1e-9)

    def test_make_prediction_uses_calibrated_confidence(self):
        detector = TextDetector()
        profile = {
            **detector._calibration_profile,
            "weights": dict(detector._calibration_profile["weights"]),
            "ranges": dict(detector._calibration_profile["ranges"]),
            "ml_weight": 1.0,
            "decision_threshold": 0.5,
            "uncertainty_margin": 0.01,
            "calibration_map": {"type": "platt", "coef": 10.0, "intercept": -8.0},
        }

        is_ai, confidence, _model_pred, decision_band, _distance, _reason = (
            detector._make_prediction(
                perplexity=20.0,
                burstiness=0.2,
                vocab_richness=0.5,
                avg_sentence_length=18.0,
                repetition=0.1,
                punctuation_diversity=0.3,
                stopword_ratio=0.25,
                sentence_length_variance=8.0,
                sentence_length_kurtosis=0.0,
                word_count=150,
                sentence_count=8,
                ml_score=0.6,
                calibration_profile=profile,
            )
        )

        assert confidence < 0.5
        assert decision_band == "human"
        assert is_ai is False

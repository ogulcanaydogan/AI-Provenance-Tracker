"""Tests for text detection engine."""

import pytest
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
        assert result.explanation is not None
        assert result.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_detect_short_text(self, detector):
        """Test detection with short text."""
        text = "Hello world."
        result = await detector.detect(text)

        assert result is not None
        # Short text should have lower confidence
        assert result.confidence < 0.9

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

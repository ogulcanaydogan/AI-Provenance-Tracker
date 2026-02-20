"""Unit tests for the audio detection engine."""

import io
import math
import struct
import wave

import pytest

from app.detection.audio.detector import AudioDetector


def _create_wav(
    duration: float = 0.5,
    sample_rate: int = 16000,
    frequency: float = 440.0,
    amplitude: float = 0.4,
) -> bytes:
    """Create a synthetic WAV file."""
    frame_count = int(duration * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for n in range(frame_count):
            value = amplitude * math.sin(2.0 * math.pi * frequency * (n / sample_rate))
            frames.extend(struct.pack("<h", int(value * 32767)))
        wf.writeframes(bytes(frames))
    return buf.getvalue()


def _create_silence_wav(duration: float = 0.5, sample_rate: int = 16000) -> bytes:
    """Create a silent WAV file."""
    frame_count = int(duration * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * frame_count)
    return buf.getvalue()


@pytest.fixture
def detector() -> AudioDetector:
    return AudioDetector()


@pytest.mark.asyncio
async def test_detect_returns_valid_response(detector: AudioDetector):
    """Detector returns a properly structured response."""
    result = await detector.detect(_create_wav(), "clip.wav")
    assert hasattr(result, "is_ai_generated")
    assert isinstance(result.is_ai_generated, bool)
    assert 0.0 <= result.confidence <= 1.0
    assert result.filename == "clip.wav"


@pytest.mark.asyncio
async def test_detect_analysis_has_expected_fields(detector: AudioDetector):
    """Analysis section contains all required signal fields."""
    result = await detector.detect(_create_wav(), "clip.wav")
    analysis = result.analysis
    assert hasattr(analysis, "sample_rate")
    assert hasattr(analysis, "duration_seconds")
    assert hasattr(analysis, "spectral_flatness")
    assert hasattr(analysis, "dynamic_range")
    assert hasattr(analysis, "clipping_ratio")
    assert hasattr(analysis, "zero_crossing_rate")


@pytest.mark.asyncio
async def test_detect_sample_rate_matches_input(detector: AudioDetector):
    """Detected sample rate reflects input WAV header."""
    result = await detector.detect(_create_wav(sample_rate=44100), "hi-fi.wav")
    assert result.analysis.sample_rate == 44100


@pytest.mark.asyncio
async def test_detect_duration_reasonable(detector: AudioDetector):
    """Duration is approximately correct."""
    result = await detector.detect(_create_wav(duration=1.0), "one_sec.wav")
    assert 0.9 <= result.analysis.duration_seconds <= 1.1


@pytest.mark.asyncio
async def test_detect_processing_time_recorded(detector: AudioDetector):
    """Processing time is a positive number."""
    result = await detector.detect(_create_wav(), "clip.wav")
    assert result.processing_time_ms > 0


@pytest.mark.asyncio
async def test_detect_silence_differs_from_tone(detector: AudioDetector):
    """Silent audio should produce different analysis than a tone."""
    silence = await detector.detect(_create_silence_wav(), "silence.wav")
    tone = await detector.detect(_create_wav(), "tone.wav")

    # Both valid, but spectral characteristics should differ
    assert 0.0 <= silence.confidence <= 1.0
    assert 0.0 <= tone.confidence <= 1.0
    # Dynamic range should differ — silence has very low dynamic range
    assert silence.analysis.dynamic_range != tone.analysis.dynamic_range


@pytest.mark.asyncio
async def test_detect_explanation_is_non_empty(detector: AudioDetector):
    """Explanation string is always populated."""
    result = await detector.detect(_create_wav(), "clip.wav")
    assert len(result.explanation) > 0

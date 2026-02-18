"""Audio AI detection engine."""

from __future__ import annotations

import io
import time
import wave
from typing import Optional

import numpy as np

from app.models.detection import AIModel, AudioAnalysis, AudioDetectionResponse


class AudioDetector:
    """
    Detects AI-generated audio using lightweight signal heuristics.

    MVP approach:
    - Spectral flatness
    - Dynamic range
    - Clipping ratio
    - Zero-crossing rate
    """

    async def detect(self, audio_data: bytes, filename: str) -> AudioDetectionResponse:
        """Analyze audio bytes and return an AI-likelihood score."""
        start_time = time.time()

        signal, sample_rate, channels, duration_seconds = self._decode_wav(audio_data)

        spectral_flatness = self._spectral_flatness(signal)
        dynamic_range = self._dynamic_range(signal)
        clipping_ratio = self._clipping_ratio(signal)
        zero_crossing_rate = self._zero_crossing_rate(signal)

        is_ai, confidence, model_prediction = self._make_prediction(
            spectral_flatness=spectral_flatness,
            dynamic_range=dynamic_range,
            clipping_ratio=clipping_ratio,
            zero_crossing_rate=zero_crossing_rate,
        )

        explanation = self._generate_explanation(
            is_ai=is_ai,
            confidence=confidence,
            spectral_flatness=spectral_flatness,
            dynamic_range=dynamic_range,
            clipping_ratio=clipping_ratio,
        )

        processing_time = (time.time() - start_time) * 1000

        return AudioDetectionResponse(
            is_ai_generated=is_ai,
            confidence=confidence,
            model_prediction=model_prediction,
            analysis=AudioAnalysis(
                sample_rate=sample_rate,
                duration_seconds=duration_seconds,
                channel_count=channels,
                spectral_flatness=spectral_flatness,
                dynamic_range=dynamic_range,
                clipping_ratio=clipping_ratio,
                zero_crossing_rate=zero_crossing_rate,
            ),
            explanation=explanation,
            filename=filename,
            processing_time_ms=processing_time,
        )

    def _decode_wav(self, audio_data: bytes) -> tuple[np.ndarray, int, int, float]:
        """Decode PCM WAV audio bytes into normalized mono float signal."""
        try:
            with wave.open(io.BytesIO(audio_data), "rb") as wav_file:
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                sample_rate = wav_file.getframerate()
                frame_count = wav_file.getnframes()
                raw = wav_file.readframes(frame_count)
        except wave.Error as exc:
            raise ValueError("Invalid or unsupported WAV audio data") from exc

        if frame_count == 0 or sample_rate <= 0:
            raise ValueError("Audio contains no samples")

        if sample_width == 1:
            samples = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
            samples = (samples - 128.0) / 128.0
        elif sample_width == 2:
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        elif sample_width == 4:
            samples = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            raise ValueError(f"Unsupported WAV bit depth: {sample_width * 8}")

        if channels > 1:
            sample_count = len(samples) - (len(samples) % channels)
            samples = samples[:sample_count].reshape(-1, channels).mean(axis=1)

        duration_seconds = len(samples) / float(sample_rate)
        return samples, sample_rate, channels, round(duration_seconds, 3)

    def _spectral_flatness(self, signal: np.ndarray) -> float:
        """Estimate spectral flatness from FFT magnitudes."""
        if signal.size < 32:
            return 0.5

        window = np.hanning(signal.size)
        spectrum = np.abs(np.fft.rfft(signal * window)) + 1e-12
        geometric = np.exp(np.mean(np.log(spectrum)))
        arithmetic = np.mean(spectrum)
        if arithmetic == 0:
            return 0.5
        return round(float(np.clip(geometric / arithmetic, 0.0, 1.0)), 3)

    def _dynamic_range(self, signal: np.ndarray) -> float:
        """Compute robust dynamic range (P95-P5) over absolute amplitude."""
        if signal.size == 0:
            return 0.0
        abs_signal = np.abs(signal)
        value = np.percentile(abs_signal, 95) - np.percentile(abs_signal, 5)
        return round(float(np.clip(value, 0.0, 1.0)), 3)

    def _clipping_ratio(self, signal: np.ndarray) -> float:
        """Ratio of near-clipped samples."""
        if signal.size == 0:
            return 0.0
        ratio = float(np.mean(np.abs(signal) >= 0.98))
        return round(float(np.clip(ratio, 0.0, 1.0)), 4)

    def _zero_crossing_rate(self, signal: np.ndarray) -> float:
        """Fraction of adjacent samples that cross zero."""
        if signal.size < 2:
            return 0.0
        crossings = np.signbit(signal[:-1]) != np.signbit(signal[1:])
        return round(float(np.mean(crossings)), 4)

    def _make_prediction(
        self,
        spectral_flatness: float,
        dynamic_range: float,
        clipping_ratio: float,
        zero_crossing_rate: float,
    ) -> tuple[bool, float, Optional[AIModel]]:
        """Combine audio signals into an AI likelihood score."""
        flatness_signal = np.clip((spectral_flatness - 0.25) / 0.45, 0.0, 1.0)
        dynamic_signal = np.clip((0.22 - dynamic_range) / 0.22, 0.0, 1.0)
        clipping_signal = np.clip(clipping_ratio / 0.05, 0.0, 1.0)
        zcr_signal = 1.0 if zero_crossing_rate < 0.02 or zero_crossing_rate > 0.35 else 0.2

        confidence = (
            (flatness_signal * 0.35)
            + (dynamic_signal * 0.30)
            + (clipping_signal * 0.20)
            + (zcr_signal * 0.15)
        )
        confidence = float(np.clip(confidence, 0.05, 0.95))

        is_ai = confidence > 0.5
        model_prediction = AIModel.UNKNOWN if is_ai else None
        return is_ai, round(confidence, 3), model_prediction

    def _generate_explanation(
        self,
        is_ai: bool,
        confidence: float,
        spectral_flatness: float,
        dynamic_range: float,
        clipping_ratio: float,
    ) -> str:
        """Create user-facing explanation for the audio verdict."""
        verdict = "likely AI-generated" if is_ai else "likely human-recorded"
        conf_label = "high" if confidence > 0.75 else "moderate" if confidence > 0.5 else "low"

        reasons: list[str] = []
        if spectral_flatness > 0.55:
            reasons.append("high spectral flatness")
        if dynamic_range < 0.12:
            reasons.append("compressed dynamic range")
        if clipping_ratio > 0.02:
            reasons.append("frequent near-clipping samples")
        if not reasons:
            reasons.append("mixed acoustic signals")

        return (
            f"Audio appears {verdict} ({conf_label} confidence). "
            f"Key indicators: {', '.join(reasons)}."
        )

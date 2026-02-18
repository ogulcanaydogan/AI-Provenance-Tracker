"""Video AI detection engine (MVP scaffold)."""

from __future__ import annotations

import math
import time
from collections import Counter
from typing import Optional

import numpy as np

from app.models.detection import AIModel, VideoAnalysis, VideoDetectionResponse


class VideoDetector:
    """
    Detects AI-generated video using lightweight byte-level heuristics.

    MVP approach:
    - Byte entropy profile
    - Byte-distribution uniformity
    - Repeated chunk patterns
    - Container/signature flags
    """

    async def detect(self, video_data: bytes, filename: str) -> VideoDetectionResponse:
        """Analyze a video payload and return an AI-likelihood score."""
        start_time = time.time()

        if not video_data:
            raise ValueError("Uploaded video is empty")

        sampled = self._sample(video_data)

        entropy_score = self._entropy_score(sampled)
        byte_uniformity = self._byte_uniformity(sampled)
        repeated_chunk_ratio = self._repeated_chunk_ratio(sampled)
        signature_flags = self._signature_flags(video_data, filename)

        is_ai, confidence, model_prediction = self._make_prediction(
            entropy_score=entropy_score,
            byte_uniformity=byte_uniformity,
            repeated_chunk_ratio=repeated_chunk_ratio,
            signature_flags=signature_flags,
        )

        explanation = self._generate_explanation(
            is_ai=is_ai,
            confidence=confidence,
            entropy_score=entropy_score,
            repeated_chunk_ratio=repeated_chunk_ratio,
            signature_flags=signature_flags,
        )

        processing_time = (time.time() - start_time) * 1000

        return VideoDetectionResponse(
            is_ai_generated=is_ai,
            confidence=confidence,
            model_prediction=model_prediction,
            analysis=VideoAnalysis(
                file_size_mb=round(len(video_data) / (1024 * 1024), 3),
                entropy_score=entropy_score,
                byte_uniformity=byte_uniformity,
                repeated_chunk_ratio=repeated_chunk_ratio,
                signature_flags=signature_flags,
            ),
            explanation=explanation,
            filename=filename,
            processing_time_ms=processing_time,
        )

    def _sample(self, video_data: bytes, max_bytes: int = 2 * 1024 * 1024) -> bytes:
        if len(video_data) <= max_bytes:
            return video_data

        half = max_bytes // 2
        return video_data[:half] + video_data[-half:]

    def _entropy_score(self, data: bytes) -> float:
        """Shannon entropy in [0, 8]."""
        if not data:
            return 0.0
        counts = Counter(data)
        total = float(len(data))
        entropy = -sum((count / total) * math.log2(count / total) for count in counts.values())
        return round(float(np.clip(entropy, 0.0, 8.0)), 3)

    def _byte_uniformity(self, data: bytes) -> float:
        """How flat the byte distribution is (0-1)."""
        if not data:
            return 0.0
        hist = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256).astype(np.float64)
        mean = float(np.mean(hist))
        std = float(np.std(hist))
        if mean == 0:
            return 0.0
        normalized = 1.0 - min(1.0, std / (mean * 4.0))
        return round(float(np.clip(normalized, 0.0, 1.0)), 3)

    def _repeated_chunk_ratio(self, data: bytes, chunk_size: int = 32) -> float:
        """Fraction of repeated fixed-size chunks."""
        if len(data) < chunk_size * 2:
            return 0.0
        usable = len(data) - (len(data) % chunk_size)
        chunks = [data[i : i + chunk_size] for i in range(0, usable, chunk_size)]
        if not chunks:
            return 0.0
        counts = Counter(chunks)
        repeated = sum(count for count in counts.values() if count > 1)
        ratio = repeated / len(chunks)
        return round(float(np.clip(ratio, 0.0, 1.0)), 4)

    def _signature_flags(self, video_data: bytes, filename: str) -> list[str]:
        """Collect suspicious or notable container/signature flags."""
        flags: list[str] = []
        header = video_data[:4096]
        lower_header = header.lower()
        lower_name = filename.lower()

        has_mp4 = b"ftyp" in header
        has_webm = b"\x1a\x45\xdf\xa3" in header  # EBML
        if not has_mp4 and not has_webm and not lower_name.endswith((".avi", ".mov", ".mkv")):
            flags.append("unknown_container_signature")

        encoder_keywords = [b"lavf", b"ffmpeg", b"x264", b"x265", b"nvenc", b"svt"]
        if any(keyword in lower_header for keyword in encoder_keywords):
            flags.append("generated_encoder_tag")

        ai_keywords = [b"ai", b"synth", b"diffusion", b"runway", b"sora", b"gen"]
        if any(keyword in lower_header for keyword in ai_keywords):
            flags.append("ai_keyword_tag")

        if len(video_data) < 20 * 1024:
            flags.append("unusually_small_file")

        return flags

    def _make_prediction(
        self,
        entropy_score: float,
        byte_uniformity: float,
        repeated_chunk_ratio: float,
        signature_flags: list[str],
    ) -> tuple[bool, float, Optional[AIModel]]:
        entropy_signal = np.clip((entropy_score - 6.8) / 1.0, 0.0, 1.0)
        uniformity_signal = np.clip((byte_uniformity - 0.55) / 0.45, 0.0, 1.0)
        repeat_signal = np.clip(repeated_chunk_ratio / 0.20, 0.0, 1.0)
        flag_signal = min(1.0, len(signature_flags) * 0.25)

        confidence = (
            (entropy_signal * 0.30)
            + (uniformity_signal * 0.25)
            + (repeat_signal * 0.25)
            + (flag_signal * 0.20)
        )
        confidence = float(np.clip(confidence, 0.05, 0.95))

        is_ai = confidence > 0.5
        model_prediction = AIModel.UNKNOWN if is_ai else None
        return is_ai, round(confidence, 3), model_prediction

    def _generate_explanation(
        self,
        is_ai: bool,
        confidence: float,
        entropy_score: float,
        repeated_chunk_ratio: float,
        signature_flags: list[str],
    ) -> str:
        verdict = "likely AI-generated" if is_ai else "likely human-captured"
        conf_label = "high" if confidence > 0.75 else "moderate" if confidence > 0.5 else "low"

        reasons: list[str] = []
        if entropy_score > 7.5:
            reasons.append("high entropy profile")
        if repeated_chunk_ratio > 0.08:
            reasons.append("repeated chunk patterns")
        if "ai_keyword_tag" in signature_flags:
            reasons.append("AI-related metadata keywords")
        if not reasons:
            reasons.append("mixed container and byte-pattern signals")

        return (
            f"Video appears {verdict} ({conf_label} confidence). "
            f"Key indicators: {', '.join(reasons)}."
        )


"""Image AI detection engine."""

import io
import time
from typing import Optional

import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS
from scipy import fft

from app.models.detection import (
    AIModel,
    ImageAnalysis,
    ImageDetectionResponse,
)


class ImageDetector:
    """
    Detects AI-generated images using multiple signals.

    Detection methods:
    1. Frequency domain analysis - AI images have distinct FFT patterns
    2. Artifact detection - Look for AI-specific generation artifacts
    3. Metadata forensics - Check EXIF and compression patterns
    4. CNN classifier - Trained binary classifier (future)

    This MVP uses statistical heuristics as a foundation.
    Production would use trained CNN/transformer models.
    """

    def __init__(self) -> None:
        """Initialize the image detector."""
        self.model_loaded = False

    async def detect(self, image_data: bytes, filename: str) -> ImageDetectionResponse:
        """
        Analyze image and determine if it's AI-generated.

        Args:
            image_data: Raw image bytes
            filename: Original filename

        Returns:
            ImageDetectionResponse with detection results
        """
        start_time = time.time()

        # Load image
        image = Image.open(io.BytesIO(image_data))
        width, height = image.size

        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Convert to numpy array
        img_array = np.array(image)

        # Calculate detection signals
        freq_anomaly = self._analyze_frequency_domain(img_array)
        artifact_score = self._detect_artifacts(img_array)
        metadata_flags = self._analyze_metadata(image, image_data)
        compression_notes = self._analyze_compression(image_data)

        # Combine signals into final prediction
        is_ai, confidence, model_pred = self._make_prediction(
            freq_anomaly=freq_anomaly,
            artifact_score=artifact_score,
            metadata_flags=metadata_flags,
        )

        # Generate explanation
        explanation = self._generate_explanation(
            is_ai=is_ai,
            confidence=confidence,
            freq_anomaly=freq_anomaly,
            artifact_score=artifact_score,
            metadata_flags=metadata_flags,
        )

        processing_time = (time.time() - start_time) * 1000

        return ImageDetectionResponse(
            is_ai_generated=is_ai,
            confidence=confidence,
            model_prediction=model_pred,
            analysis=ImageAnalysis(
                frequency_anomaly=freq_anomaly,
                artifact_score=artifact_score,
                metadata_flags=metadata_flags,
                compression_analysis=compression_notes,
            ),
            explanation=explanation,
            filename=filename,
            dimensions=(width, height),
            processing_time_ms=processing_time,
        )

    def _analyze_frequency_domain(self, img_array: np.ndarray) -> float:
        """
        Analyze image in frequency domain using FFT.

        AI-generated images often have distinctive patterns in the
        frequency domain, particularly in high-frequency components.
        """
        # Convert to grayscale for FFT analysis
        if len(img_array.shape) == 3:
            gray = np.mean(img_array, axis=2)
        else:
            gray = img_array

        # Compute 2D FFT
        f_transform = fft.fft2(gray)
        f_shift = fft.fftshift(f_transform)
        magnitude = np.abs(f_shift)

        # Analyze frequency distribution
        center_y, center_x = magnitude.shape[0] // 2, magnitude.shape[1] // 2

        # Calculate energy in different frequency bands
        total_energy = np.sum(magnitude)
        if total_energy == 0:
            return 0.5

        # High frequency region (outer ring)
        y, x = np.ogrid[:magnitude.shape[0], :magnitude.shape[1]]
        distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
        max_dist = np.sqrt(center_x**2 + center_y**2)

        high_freq_mask = distance > (0.7 * max_dist)
        high_freq_energy = np.sum(magnitude[high_freq_mask])

        # AI images often have unusual high-frequency patterns
        high_freq_ratio = high_freq_energy / total_energy

        # Also check for periodic patterns (grid artifacts)
        # Sample specific frequencies that might show AI artifacts
        mid_freq_mask = (distance > 0.3 * max_dist) & (distance < 0.7 * max_dist)
        mid_freq_std = np.std(magnitude[mid_freq_mask])
        mid_freq_mean = np.mean(magnitude[mid_freq_mask])

        if mid_freq_mean > 0:
            uniformity = mid_freq_std / mid_freq_mean
        else:
            uniformity = 1.0

        # Combine metrics into anomaly score
        # Lower uniformity and certain high_freq patterns suggest AI
        anomaly = 0.0

        # Unusual high frequency distribution
        if high_freq_ratio < 0.01 or high_freq_ratio > 0.15:
            anomaly += 0.4

        # Too uniform mid-frequencies
        if uniformity < 0.5:
            anomaly += 0.3

        # Normalize to 0-1
        return round(min(1.0, anomaly + 0.2), 3)

    def _detect_artifacts(self, img_array: np.ndarray) -> float:
        """
        Detect AI-specific generation artifacts.

        Common AI artifacts:
        - Unusual texture patterns
        - Edge inconsistencies
        - Color banding
        - Repeated patterns
        """
        artifact_score = 0.0

        # Check for color banding (limited color palette)
        unique_colors = len(np.unique(img_array.reshape(-1, 3), axis=0))
        total_pixels = img_array.shape[0] * img_array.shape[1]
        color_ratio = unique_colors / min(total_pixels, 100000)

        if color_ratio < 0.3:  # Surprisingly few unique colors
            artifact_score += 0.3

        # Check for unnatural smoothness
        # Calculate local variance
        local_vars = []
        step = max(1, min(img_array.shape[0], img_array.shape[1]) // 20)

        for i in range(0, img_array.shape[0] - step, step):
            for j in range(0, img_array.shape[1] - step, step):
                patch = img_array[i:i+step, j:j+step]
                local_vars.append(np.var(patch))

        if local_vars:
            var_of_vars = np.std(local_vars) / (np.mean(local_vars) + 1e-6)
            if var_of_vars < 0.5:  # Too uniform variance
                artifact_score += 0.25

        # Check for edge artifacts
        # Simple edge detection using gradient magnitude
        gy, gx = np.gradient(np.mean(img_array, axis=2))
        gradient_mag = np.sqrt(gx**2 + gy**2)

        # AI images sometimes have unusual edge distributions
        edge_mean = np.mean(gradient_mag)
        edge_std = np.std(gradient_mag)

        if edge_std / (edge_mean + 1e-6) < 1.0:  # Too uniform edges
            artifact_score += 0.2

        return round(min(1.0, artifact_score), 3)

    def _analyze_metadata(self, image: Image.Image, raw_data: bytes) -> list[str]:
        """
        Analyze image metadata for authenticity signals.

        Real photos typically have EXIF data from cameras.
        AI-generated images often lack this metadata.
        """
        flags = []

        # Check for EXIF data
        exif_data = image._getexif() if hasattr(image, '_getexif') else None

        if exif_data is None:
            flags.append("missing_exif")
        else:
            # Check for camera-specific tags
            exif_tags = {TAGS.get(k, k): v for k, v in exif_data.items()}

            if 'Make' not in exif_tags and 'Model' not in exif_tags:
                flags.append("no_camera_info")

            if 'DateTimeOriginal' not in exif_tags:
                flags.append("no_capture_date")

            if 'GPSInfo' not in exif_tags:
                # Not necessarily suspicious, but noted
                pass

        # Check file size vs dimensions ratio
        file_size = len(raw_data)
        pixel_count = image.size[0] * image.size[1]
        bytes_per_pixel = file_size / pixel_count

        if bytes_per_pixel < 0.5:  # Unusually high compression
            flags.append("unusual_compression")

        # Check for software tags
        if exif_data:
            exif_tags = {TAGS.get(k, k): v for k, v in exif_data.items()}
            software = exif_tags.get('Software', '')
            if isinstance(software, str):
                ai_keywords = ['dalle', 'midjourney', 'stable', 'diffusion', 'ai']
                if any(kw in software.lower() for kw in ai_keywords):
                    flags.append("ai_software_tag")

        return flags

    def _analyze_compression(self, image_data: bytes) -> str:
        """Analyze compression patterns."""
        file_size_kb = len(image_data) / 1024

        if file_size_kb < 50:
            return "heavily_compressed"
        elif file_size_kb < 200:
            return "moderately_compressed"
        elif file_size_kb > 5000:
            return "minimal_compression"
        else:
            return "normal_compression"

    def _make_prediction(
        self,
        freq_anomaly: float,
        artifact_score: float,
        metadata_flags: list[str],
    ) -> tuple[bool, float, Optional[AIModel]]:
        """Combine signals to make final prediction."""
        signals = []

        # Frequency anomaly contribution
        signals.append(freq_anomaly * 0.35)

        # Artifact score contribution
        signals.append(artifact_score * 0.35)

        # Metadata flags contribution
        metadata_score = 0.0
        if "missing_exif" in metadata_flags:
            metadata_score += 0.4
        if "no_camera_info" in metadata_flags:
            metadata_score += 0.2
        if "unusual_compression" in metadata_flags:
            metadata_score += 0.2
        if "ai_software_tag" in metadata_flags:
            metadata_score += 0.8

        signals.append(min(1.0, metadata_score) * 0.30)

        confidence = sum(signals)

        # Adjust confidence bounds
        confidence = max(0.1, min(0.95, confidence))

        is_ai = confidence > 0.5

        # Predict model (simplified - would use classifier in production)
        model_pred = None
        if is_ai:
            if artifact_score > 0.6:
                model_pred = AIModel.STABLE_DIFFUSION
            elif freq_anomaly > 0.6:
                model_pred = AIModel.MIDJOURNEY
            else:
                model_pred = AIModel.DALLE

        return is_ai, round(confidence, 3), model_pred

    def _generate_explanation(
        self,
        is_ai: bool,
        confidence: float,
        freq_anomaly: float,
        artifact_score: float,
        metadata_flags: list[str],
    ) -> str:
        """Generate human-readable explanation."""
        verdict = "likely AI-generated" if is_ai else "likely authentic"
        conf_level = "high" if confidence > 0.75 else "moderate" if confidence > 0.5 else "low"

        reasons = []

        if freq_anomaly > 0.5:
            reasons.append("unusual frequency patterns")
        if artifact_score > 0.4:
            reasons.append("detected generation artifacts")
        if "missing_exif" in metadata_flags:
            reasons.append("missing camera metadata")
        if "ai_software_tag" in metadata_flags:
            reasons.append("AI software tag found")

        if not is_ai:
            if freq_anomaly < 0.4:
                reasons.append("natural frequency distribution")
            if artifact_score < 0.3:
                reasons.append("no obvious artifacts")
            if "missing_exif" not in metadata_flags:
                reasons.append("contains camera metadata")

        reason_text = ", ".join(reasons) if reasons else "mixed signals"

        return f"Image appears {verdict} ({conf_level} confidence). Key indicators: {reason_text}."

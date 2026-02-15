"""Detection API endpoints."""

from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field, HttpUrl

from app.core.config import settings

from app.detection.audio.detector import AudioDetector
from app.detection.image.detector import ImageDetector
from app.detection.text.detector import TextDetector
from app.detection.video.detector import VideoDetector
from app.models.detection import (
    AIModel,
    AudioDetectionResponse,
    ImageDetectionResponse,
    TextDetectionRequest,
    TextDetectionResponse,
    VideoDetectionResponse,
)
from app.services.analysis_store import analysis_store
from app.services.provider_consensus import provider_consensus_engine

router = APIRouter()

# Initialize detectors (in production, these would be loaded at startup)
text_detector = TextDetector()
image_detector = ImageDetector()
audio_detector = AudioDetector()
video_detector = VideoDetector()


class UrlDetectionRequest(BaseModel):
    """Request payload for URL-based detection."""

    url: HttpUrl = Field(..., description="Public URL to fetch and analyze")


def _extract_text_from_html(html: str) -> str:
    """Extract readable text from raw HTML."""
    without_scripts = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    without_tags = re.sub(r"(?s)<[^>]+>", " ", without_scripts)
    return re.sub(r"\s+", " ", without_tags).strip()


def _filename_from_url(url: str) -> str:
    """Infer a filename from URL path."""
    path = urlparse(url).path.rstrip("/")
    if not path:
        return "downloaded_image"
    filename = path.split("/")[-1]
    return filename or "downloaded_image"


async def _apply_consensus(
    *,
    content_type: str,
    result: TextDetectionResponse | ImageDetectionResponse | AudioDetectionResponse | VideoDetectionResponse,
    text: str | None = None,
    binary: bytes | None = None,
    filename: str | None = None,
) -> TextDetectionResponse | ImageDetectionResponse | AudioDetectionResponse | VideoDetectionResponse:
    consensus = await provider_consensus_engine.build_consensus(
        content_type=content_type,
        internal_probability=result.confidence,
        text=text,
        binary=binary,
        filename=filename,
    )
    result.consensus = consensus
    result.confidence = consensus.final_probability
    result.is_ai_generated = consensus.is_ai_generated
    if result.is_ai_generated and result.model_prediction is None:
        result.model_prediction = AIModel.UNKNOWN
    return result


@router.post("/text", response_model=TextDetectionResponse)
async def detect_text(request: TextDetectionRequest) -> TextDetectionResponse:
    """
    Detect if text is AI-generated.

    Analyzes text using multiple signals:
    - Perplexity analysis
    - Burstiness measurement
    - Vocabulary distribution
    - Fine-tuned classifier

    Returns confidence score and detailed analysis.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    if len(request.text) > settings.max_text_length:
        raise HTTPException(
            status_code=400,
            detail=f"Text exceeds maximum length of {settings.max_text_length:,} characters",
        )

    result = await text_detector.detect(request.text)
    result = await _apply_consensus(
        content_type="text",
        result=result,
        text=request.text,
    )
    result.analysis_id = await analysis_store.save_text_result(request.text, result, source="api")
    return result


@router.post("/image", response_model=ImageDetectionResponse)
async def detect_image(file: UploadFile = File(...)) -> ImageDetectionResponse:
    """
    Detect if an image is AI-generated.

    Analyzes images using:
    - Frequency domain analysis
    - Artifact detection
    - Metadata forensics
    - CNN classifier

    Supports: PNG, JPEG, WebP
    Max size: 10MB
    """
    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )

    # Read file content
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")

    # Check file size (10MB limit)
    max_image_size_bytes = settings.max_image_size_mb * 1024 * 1024
    if len(content) > max_image_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Image exceeds maximum size of {settings.max_image_size_mb}MB",
        )

    filename = file.filename or "unknown"
    result = await image_detector.detect(content, filename)
    result = await _apply_consensus(
        content_type="image",
        result=result,
        binary=content,
        filename=filename,
    )
    result.analysis_id = await analysis_store.save_image_result(
        image_data=content,
        filename=filename,
        result=result,
        source="api",
    )
    return result


@router.post("/audio", response_model=AudioDetectionResponse)
async def detect_audio(file: UploadFile = File(...)) -> AudioDetectionResponse:
    """
    Detect if an audio clip is AI-generated.

    MVP currently supports WAV/PCM files and analyzes acoustic signals.
    """
    allowed_types = [
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
        "audio/vnd.wave",
        "audio/vnd.wav",
    ]

    filename = file.filename or "unknown.wav"
    if file.content_type not in allowed_types and not filename.lower().endswith(".wav"):
        raise HTTPException(
            status_code=400,
            detail="Invalid audio file type. Upload a WAV file.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded audio is empty")

    max_audio_size_bytes = settings.max_audio_size_mb * 1024 * 1024
    if len(content) > max_audio_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Audio exceeds maximum size of {settings.max_audio_size_mb}MB",
        )

    try:
        result = await audio_detector.detect(content, filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result = await _apply_consensus(
        content_type="audio",
        result=result,
        binary=content,
        filename=filename,
    )

    result.analysis_id = await analysis_store.save_audio_result(
        audio_data=content,
        filename=filename,
        result=result,
        source="api",
    )
    return result


@router.post("/video", response_model=VideoDetectionResponse)
async def detect_video(file: UploadFile = File(...)) -> VideoDetectionResponse:
    """
    Detect if a video clip is AI-generated.

    MVP uses byte-level heuristics on common container formats.
    """
    allowed_types = [
        "video/mp4",
        "video/webm",
        "video/quicktime",
        "video/x-msvideo",
        "video/x-matroska",
    ]
    allowed_extensions = (".mp4", ".webm", ".mov", ".avi", ".mkv")

    filename = file.filename or "unknown.mp4"
    if file.content_type not in allowed_types and not filename.lower().endswith(allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail="Invalid video file type. Upload MP4/WebM/MOV/AVI/MKV.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded video is empty")

    max_video_size_bytes = settings.max_video_size_mb * 1024 * 1024
    if len(content) > max_video_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Video exceeds maximum size of {settings.max_video_size_mb}MB",
        )

    try:
        result = await video_detector.detect(content, filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result = await _apply_consensus(
        content_type="video",
        result=result,
        binary=content,
        filename=filename,
    )

    result.analysis_id = await analysis_store.save_video_result(
        video_data=content,
        filename=filename,
        result=result,
        source="api",
    )
    return result


@router.post("/url")
async def detect_from_url(request: UrlDetectionRequest) -> dict:
    """
    Detect AI-generated content from a URL.

    Fetches content from the URL and analyzes it.
    Supports text articles and images.
    """
    max_image_size_bytes = settings.max_image_size_mb * 1024 * 1024
    source_url = str(request.url)

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=5.0),
            follow_redirects=True,
        ) as client:
            response = await client.get(
                source_url,
                headers={"User-Agent": "AIProvenanceTracker/0.1"},
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {exc}") from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=400,
            detail=f"URL returned status code {response.status_code}",
        )

    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
    resolved_url = str(response.url)

    is_image = content_type.startswith("image/")
    is_text = content_type.startswith("text/") or "json" in content_type or "xml" in content_type

    if not content_type:
        path = urlparse(resolved_url).path.lower()
        is_image = path.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"))
        is_text = not is_image

    if is_image:
        image_data = response.content
        if len(image_data) > max_image_size_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"Image exceeds maximum size of {settings.max_image_size_mb}MB",
            )

        filename = _filename_from_url(resolved_url)
        image_result = await image_detector.detect(image_data, filename)
        image_result = await _apply_consensus(
            content_type="image",
            result=image_result,
            binary=image_data,
            filename=filename,
        )
        analysis_id = await analysis_store.save_image_result(
            image_data=image_data,
            filename=filename,
            result=image_result,
            source="url",
            source_url=resolved_url,
        )
        image_result.analysis_id = analysis_id

        return {
            "analysis_id": analysis_id,
            "content_type": "image",
            "url": resolved_url,
            "result": image_result,
        }

    if is_text:
        raw_text = response.text
        extracted_text = _extract_text_from_html(raw_text) if "html" in content_type else raw_text
        extracted_text = re.sub(r"\s+", " ", extracted_text).strip()

        if not extracted_text:
            raise HTTPException(status_code=400, detail="No analyzable text found at URL")

        if len(extracted_text) > settings.max_text_length:
            extracted_text = extracted_text[: settings.max_text_length]

        text_result = await text_detector.detect(extracted_text)
        text_result = await _apply_consensus(
            content_type="text",
            result=text_result,
            text=extracted_text,
        )
        analysis_id = await analysis_store.save_text_result(
            text=extracted_text,
            result=text_result,
            source="url",
            source_url=resolved_url,
        )
        text_result.analysis_id = analysis_id

        return {
            "analysis_id": analysis_id,
            "content_type": "text",
            "url": resolved_url,
            "result": text_result,
            "text_length": len(extracted_text),
        }

    raise HTTPException(status_code=400, detail=f"Unsupported content type: {content_type or 'unknown'}")

"""Detection API endpoints."""

from __future__ import annotations

import asyncio
import html
import json
import re
import ssl
from urllib.parse import urljoin, urlparse

import certifi
import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
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
    ProviderEvidence,
    TextDetectionRequest,
    TextDetectionResponse,
    VideoDetectionResponse,
)
from app.services.analysis_store import analysis_store
from app.services.audit_events import audit_event_store
from app.services.provider_consensus import provider_consensus_engine

router = APIRouter()

# Initialize detectors (in production, these would be loaded at startup)
text_detector = TextDetector()
image_detector = ImageDetector()
audio_detector = AudioDetector()
video_detector = VideoDetector()

IMAGE_URL_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")
VIDEO_URL_EXTENSIONS = (".mp4", ".webm", ".mov", ".avi", ".mkv")
SOCIAL_MEDIA_HOST_SUFFIXES = (
    "instagram.com",
    "facebook.com",
    "tiktok.com",
    "x.com",
    "twitter.com",
    "threads.net",
)
OG_VIDEO_PROPERTIES = ("og:video", "og:video:url", "og:video:secure_url")
OG_IMAGE_PROPERTIES = ("og:image", "og:image:url", "og:image:secure_url")
OG_PLAYER_PROPERTIES = ("twitter:player", "twitter:player:stream")
PLATFORM_MEDIA_MISSING_DETAIL = "Platform page detected but no public direct media found"
URL_TLS_CERTIFICATE_VERIFY_DETAIL = (
    "TLS certificate validation failed while fetching URL. "
    "Ensure the target URL exposes a valid public certificate chain."
)
URL_FETCH_MAX_REDIRECTS = 5
URL_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}
SOCIAL_ACCESS_BARRIER_PATTERNS = (
    "this account is private",
    "private account",
    "challenge_required",
    "checkpoint",
    "log in",
    "login",
    "sign in",
    "create account",
)


class UrlDetectionRequest(BaseModel):
    """Request payload for URL-based detection."""

    url: HttpUrl = Field(..., description="Public URL to fetch and analyze")

    model_config = {
        "json_schema_extra": {"examples": [{"url": "https://example.com/article-to-check"}]}
    }


def _extract_text_from_html(html: str) -> str:
    """Extract readable text from raw HTML."""
    without_scripts = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    without_tags = re.sub(r"(?s)<[^>]+>", " ", without_scripts)
    return re.sub(r"\s+", " ", without_tags).strip()


def _filename_from_url(url: str) -> str:
    """Infer a filename from URL path."""
    path = urlparse(url).path.rstrip("/")
    if not path:
        return "downloaded_file"
    filename = path.split("/")[-1]
    return filename or "downloaded_file"


def _is_social_media_host(url: str) -> bool:
    hostname = (urlparse(url).hostname or "").strip().lower()
    if not hostname:
        return False
    return any(
        hostname == suffix or hostname.endswith(f".{suffix}")
        for suffix in SOCIAL_MEDIA_HOST_SUFFIXES
    )


def _extract_meta_tag_attributes(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for match in re.finditer(r"""([a-zA-Z_:][\w:.-]*)\s*=\s*(['"])(.*?)\2""", tag):
        attrs[match.group(1).lower()] = html.unescape(match.group(3).strip())
    return attrs


def _resolve_social_og_media_url(page_html: str, page_url: str) -> str | None:
    video_url: str | None = None
    image_url: str | None = None
    player_url: str | None = None
    for meta_tag in re.findall(r"(?is)<meta\b[^>]*>", page_html):
        attrs = _extract_meta_tag_attributes(meta_tag)
        prop = (attrs.get("property") or attrs.get("name") or "").strip().lower()
        content = (attrs.get("content") or "").strip()
        if not content:
            continue
        if prop in OG_VIDEO_PROPERTIES and not video_url:
            video_url = urljoin(page_url, content)
        if prop in OG_IMAGE_PROPERTIES and not image_url:
            image_url = urljoin(page_url, content)
        if prop in OG_PLAYER_PROPERTIES and not player_url:
            player_url = urljoin(page_url, content)
    return video_url or image_url or player_url


def _is_social_access_barrier_page(page_html: str) -> bool:
    normalized_html = re.sub(r"\s+", " ", page_html).lower()
    return any(pattern in normalized_html for pattern in SOCIAL_ACCESS_BARRIER_PATTERNS)


def _build_url_fetch_headers(*, accept: str | None = None) -> dict[str, str]:
    headers = dict(URL_FETCH_HEADERS)
    if accept:
        headers["Accept"] = accept
    return headers


def _infer_content_flags(content_type: str, resolved_url: str) -> tuple[bool, bool, bool]:
    normalized_content_type = content_type.split(";")[0].strip().lower()
    url_path = urlparse(resolved_url).path.lower()
    is_image = normalized_content_type.startswith("image/")
    is_video = normalized_content_type.startswith("video/")
    is_text = normalized_content_type.startswith("text/") or "json" in normalized_content_type
    is_text = is_text or "xml" in normalized_content_type
    if not normalized_content_type:
        is_image = url_path.endswith(IMAGE_URL_EXTENSIONS)
        is_video = url_path.endswith(VIDEO_URL_EXTENSIONS)
        is_text = not is_image and not is_video
    return is_image, is_video, is_text


def _build_url_fetch_ssl_context() -> ssl.SSLContext:
    ca_bundle_path = (settings.url_fetch_tls_ca_bundle or "").strip() or certifi.where()
    return ssl.create_default_context(cafile=ca_bundle_path)


def _is_tls_certificate_verification_error(exc: BaseException) -> bool:
    current: BaseException | None = exc
    while current is not None:
        if isinstance(current, ssl.SSLCertVerificationError):
            return True
        message = str(current).upper()
        if "CERTIFICATE_VERIFY_FAILED" in message:
            return True
        current = current.__cause__ or current.__context__
    return False


async def _analyze_image_from_url(
    *, image_data: bytes, resolved_url: str, max_image_size_bytes: int, source: str
) -> dict:
    if len(image_data) > max_image_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Image exceeds maximum size of {settings.max_image_size_mb}MB",
        )

    filename = _filename_from_url(resolved_url)
    image_result = await image_detector.detect(image_data, filename)
    image_result.model_version = f"image-detector:{settings.image_detection_model}"
    image_result.calibration_version = "image-heuristic-v1"
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
        source=source,
        source_url=resolved_url,
    )
    image_result.analysis_id = analysis_id
    await audit_event_store.safe_log_event(
        event_type="detection.completed",
        source=source,
        payload={
            "content_type": "image",
            "analysis_id": analysis_id,
            "source": source,
            "source_url": resolved_url,
            "filename": filename,
            "is_ai_generated": image_result.is_ai_generated,
            "confidence": image_result.confidence,
        },
    )

    return {
        "analysis_id": analysis_id,
        "content_type": "image",
        "url": resolved_url,
        "result": image_result,
    }


async def _analyze_video_from_url(
    *, video_data: bytes, resolved_url: str, max_video_size_bytes: int, source: str
) -> dict:
    if len(video_data) > max_video_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Video exceeds maximum size of {settings.max_video_size_mb}MB",
        )

    filename = _filename_from_url(resolved_url)
    video_result = await video_detector.detect(video_data, filename)
    video_result.model_version = "video-detector:heuristic-v1"
    video_result.calibration_version = "video-heuristic-v1"
    video_result = await _apply_consensus(
        content_type="video",
        result=video_result,
        binary=video_data,
        filename=filename,
    )
    analysis_id = await analysis_store.save_video_result(
        video_data=video_data,
        filename=filename,
        result=video_result,
        source=source,
        source_url=resolved_url,
    )
    video_result.analysis_id = analysis_id
    await audit_event_store.safe_log_event(
        event_type="detection.completed",
        source=source,
        payload={
            "content_type": "video",
            "analysis_id": analysis_id,
            "source": source,
            "source_url": resolved_url,
            "filename": filename,
            "is_ai_generated": video_result.is_ai_generated,
            "confidence": video_result.confidence,
        },
    )

    return {
        "analysis_id": analysis_id,
        "content_type": "video",
        "url": resolved_url,
        "result": video_result,
    }


def _format_sse(event: str, payload: dict) -> str:
    """Serialize one SSE event."""
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _provider_evidence_from_consensus(
    consensus: (
        TextDetectionResponse
        | ImageDetectionResponse
        | AudioDetectionResponse
        | VideoDetectionResponse
    ),
) -> list[ProviderEvidence]:
    if not consensus.consensus:
        return []
    return [
        ProviderEvidence(
            provider=vote.provider,
            probability=vote.probability,
            status=vote.status,
            rationale=vote.rationale,
            evidence_type=vote.evidence_type,
            evidence_ref=vote.evidence_ref,
            verification_status=vote.verification_status,
        )
        for vote in consensus.consensus.providers
    ]


async def _apply_consensus(
    *,
    content_type: str,
    result: TextDetectionResponse
    | ImageDetectionResponse
    | AudioDetectionResponse
    | VideoDetectionResponse,
    text: str | None = None,
    binary: bytes | None = None,
    filename: str | None = None,
) -> (
    TextDetectionResponse | ImageDetectionResponse | AudioDetectionResponse | VideoDetectionResponse
):
    consensus = await provider_consensus_engine.build_consensus(
        content_type=content_type,
        internal_probability=result.confidence,
        text=text,
        binary=binary,
        filename=filename,
    )
    result.consensus = consensus
    result.provider_evidence = _provider_evidence_from_consensus(result)
    result.confidence = consensus.final_probability
    if isinstance(result, TextDetectionResponse):
        word_count = None
        sentence_count = None
        if text:
            words = re.findall(r"\b\w+\b", text.lower())
            sentences = [
                segment.strip() for segment in re.split(r"[.!?]+", text) if segment.strip()
            ]
            word_count = len(words)
            sentence_count = len(sentences)
        decision_band, distance, reason = text_detector.apply_decision_band(
            confidence=result.confidence,
            threshold=consensus.threshold,
            word_count=word_count,
            sentence_count=sentence_count,
        )
        disagreement_limit = float(
            min(
                1.0,
                max(0.0, settings.text_consensus_disagreement_uncertain_threshold),
            )
        )
        uncertainty_flags = list(result.uncertainty_flags)
        if uncertainty_flags:
            decision_band = "uncertain"
        if consensus.disagreement >= disagreement_limit:
            disagreement_reason = (
                f"High provider disagreement ({consensus.disagreement:.3f}) exceeds "
                f"uncertainty threshold ({disagreement_limit:.3f})."
            )
            decision_band = "uncertain"
            if "provider_disagreement" not in uncertainty_flags:
                uncertainty_flags.append("provider_disagreement")
            if reason:
                reason = f"{reason} {disagreement_reason}"
            else:
                reason = disagreement_reason
        result.decision_band = decision_band
        result.distance_to_threshold = distance
        result.uncertainty_reason = reason
        result.uncertainty_flags = uncertainty_flags
        result.is_ai_generated = decision_band == "ai"
        if decision_band != "ai":
            result.model_prediction = None
    else:
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

    result = await text_detector.detect(request.text, domain=request.domain)
    result = await _apply_consensus(
        content_type="text",
        result=result,
        text=request.text,
    )
    result.analysis_id = await analysis_store.save_text_result(request.text, result, source="api")
    await audit_event_store.safe_log_event(
        event_type="detection.completed",
        source="api",
        payload={
            "content_type": "text",
            "analysis_id": result.analysis_id,
            "source": "api",
            "is_ai_generated": result.is_ai_generated,
            "confidence": result.confidence,
        },
    )
    return result


@router.post("/stream/text")
async def detect_text_stream(request: TextDetectionRequest) -> StreamingResponse:
    """Stream text detection progress and final result over SSE."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    if len(request.text) > settings.max_text_length:
        raise HTTPException(
            status_code=400,
            detail=f"Text exceeds maximum length of {settings.max_text_length:,} characters",
        )

    async def event_stream():
        text = request.text
        domain = request.domain
        yield _format_sse(
            "started",
            {
                "stage": "started",
                "text_length": len(text),
            },
        )

        try:
            internal_result = await text_detector.detect(text, domain=domain)
            yield _format_sse(
                "internal",
                {
                    "stage": "internal_scored",
                    "confidence": internal_result.confidence,
                    "is_ai_generated": internal_result.is_ai_generated,
                    "decision_band": internal_result.decision_band,
                    "model_prediction": internal_result.model_prediction.value
                    if internal_result.model_prediction
                    else None,
                },
            )
            await asyncio.sleep(0)

            final_result = await _apply_consensus(
                content_type="text",
                result=internal_result,
                text=text,
            )
            final_result.analysis_id = await analysis_store.save_text_result(
                text, final_result, source="api_stream"
            )
            await audit_event_store.safe_log_event(
                event_type="detection.completed",
                source="api_stream",
                payload={
                    "content_type": "text",
                    "analysis_id": final_result.analysis_id,
                    "source": "api_stream",
                    "is_ai_generated": final_result.is_ai_generated,
                    "confidence": final_result.confidence,
                },
            )

            if final_result.consensus:
                yield _format_sse(
                    "consensus",
                    {
                        "stage": "consensus_complete",
                        "final_probability": final_result.consensus.final_probability,
                        "threshold": final_result.consensus.threshold,
                        "is_ai_generated": final_result.consensus.is_ai_generated,
                        "disagreement": final_result.consensus.disagreement,
                    },
                )

            yield _format_sse(
                "result",
                final_result.model_dump(mode="json"),
            )
            yield _format_sse(
                "done",
                {
                    "stage": "done",
                    "analysis_id": final_result.analysis_id,
                },
            )
        except Exception as exc:  # pragma: no cover - defensive stream safety
            yield _format_sse(
                "error",
                {
                    "stage": "error",
                    "detail": str(exc),
                },
            )

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)


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
            status_code=400, detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
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
    result.model_version = f"image-detector:{settings.image_detection_model}"
    result.calibration_version = "image-heuristic-v1"
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
    await audit_event_store.safe_log_event(
        event_type="detection.completed",
        source="api",
        payload={
            "content_type": "image",
            "analysis_id": result.analysis_id,
            "source": "api",
            "filename": filename,
            "is_ai_generated": result.is_ai_generated,
            "confidence": result.confidence,
        },
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
    result.model_version = "audio-detector:heuristic-v1"
    result.calibration_version = "audio-heuristic-v1"
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
    await audit_event_store.safe_log_event(
        event_type="detection.completed",
        source="api",
        payload={
            "content_type": "audio",
            "analysis_id": result.analysis_id,
            "source": "api",
            "filename": filename,
            "is_ai_generated": result.is_ai_generated,
            "confidence": result.confidence,
        },
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
    result.model_version = "video-detector:heuristic-v1"
    result.calibration_version = "video-heuristic-v1"
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
    await audit_event_store.safe_log_event(
        event_type="detection.completed",
        source="api",
        payload={
            "content_type": "video",
            "analysis_id": result.analysis_id,
            "source": "api",
            "filename": filename,
            "is_ai_generated": result.is_ai_generated,
            "confidence": result.confidence,
        },
    )
    return result


@router.post("/url")
async def detect_from_url(request: UrlDetectionRequest) -> dict:
    return await analyze_url_content(str(request.url), source="url")


async def analyze_url_content(source_url: str, *, source: str = "url") -> dict:
    """
    Detect AI-generated content from a URL and persist analysis under the given source label.
    """
    max_image_size_bytes = settings.max_image_size_mb * 1024 * 1024
    max_video_size_bytes = settings.max_video_size_mb * 1024 * 1024

    try:
        ssl_context = _build_url_fetch_ssl_context()
    except (FileNotFoundError, ssl.SSLError, OSError) as exc:
        raise HTTPException(
            status_code=500,
            detail="URL fetch TLS configuration is invalid. Check URL_FETCH_TLS_CA_BUNDLE.",
        ) from exc

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=5.0),
            follow_redirects=True,
            max_redirects=URL_FETCH_MAX_REDIRECTS,
            verify=ssl_context,
        ) as client:
            response = await client.get(
                source_url,
                headers=_build_url_fetch_headers(),
            )
            if response.status_code >= 400:
                raise HTTPException(
                    status_code=400,
                    detail=f"URL returned status code {response.status_code}",
                )

            content_type = response.headers.get("content-type", "")
            content_type_lower = content_type.lower()
            resolved_url = str(response.url)
            is_image, is_video, is_text = _infer_content_flags(content_type, resolved_url)

            if is_image:
                return await _analyze_image_from_url(
                    image_data=response.content,
                    resolved_url=resolved_url,
                    max_image_size_bytes=max_image_size_bytes,
                    source=source,
                )

            if is_video:
                return await _analyze_video_from_url(
                    video_data=response.content,
                    resolved_url=resolved_url,
                    max_video_size_bytes=max_video_size_bytes,
                    source=source,
                )

            if is_text:
                raw_text = response.text
                if _is_social_media_host(resolved_url) and "html" in content_type_lower:
                    media_url = _resolve_social_og_media_url(raw_text, resolved_url)
                    if not media_url:
                        if _is_social_access_barrier_page(raw_text):
                            raise HTTPException(
                                status_code=400, detail=PLATFORM_MEDIA_MISSING_DETAIL
                            )
                        raise HTTPException(status_code=400, detail=PLATFORM_MEDIA_MISSING_DETAIL)

                    try:
                        media_response = await client.get(
                            media_url,
                            headers=_build_url_fetch_headers(accept="*/*"),
                        )
                    except httpx.HTTPError as exc:
                        raise HTTPException(
                            status_code=400, detail=PLATFORM_MEDIA_MISSING_DETAIL
                        ) from exc

                    if media_response.status_code >= 400:
                        raise HTTPException(status_code=400, detail=PLATFORM_MEDIA_MISSING_DETAIL)

                    resolved_media_url = str(media_response.url)
                    media_content_type = media_response.headers.get("content-type", "")
                    media_is_image, media_is_video, _ = _infer_content_flags(
                        media_content_type, resolved_media_url
                    )

                    if media_is_image:
                        return await _analyze_image_from_url(
                            image_data=media_response.content,
                            resolved_url=resolved_media_url,
                            max_image_size_bytes=max_image_size_bytes,
                            source=source,
                        )
                    if media_is_video:
                        return await _analyze_video_from_url(
                            video_data=media_response.content,
                            resolved_url=resolved_media_url,
                            max_video_size_bytes=max_video_size_bytes,
                            source=source,
                        )
                    raise HTTPException(status_code=400, detail=PLATFORM_MEDIA_MISSING_DETAIL)

                extracted_text = (
                    _extract_text_from_html(raw_text) if "html" in content_type_lower else raw_text
                )
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
                    source=source,
                    source_url=resolved_url,
                )
                text_result.analysis_id = analysis_id
                await audit_event_store.safe_log_event(
                    event_type="detection.completed",
                    source=source,
                    payload={
                        "content_type": "text",
                        "analysis_id": analysis_id,
                        "source": source,
                        "source_url": resolved_url,
                        "is_ai_generated": text_result.is_ai_generated,
                        "confidence": text_result.confidence,
                        "text_length": len(extracted_text),
                    },
                )

                return {
                    "analysis_id": analysis_id,
                    "content_type": "text",
                    "url": resolved_url,
                    "result": text_result,
                    "text_length": len(extracted_text),
                }

            raise HTTPException(
                status_code=400, detail=f"Unsupported content type: {content_type or 'unknown'}"
            )
    except httpx.HTTPError as exc:
        if _is_tls_certificate_verification_error(exc):
            raise HTTPException(status_code=400, detail=URL_TLS_CERTIFICATE_VERIFY_DETAIL) from exc
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {exc}") from exc

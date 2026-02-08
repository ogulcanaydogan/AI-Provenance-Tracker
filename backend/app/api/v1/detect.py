"""Detection API endpoints."""

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.detection.text.detector import TextDetector
from app.detection.image.detector import ImageDetector
from app.models.detection import (
    TextDetectionRequest,
    TextDetectionResponse,
    ImageDetectionResponse,
)

router = APIRouter()

# Initialize detectors (in production, these would be loaded at startup)
text_detector = TextDetector()
image_detector = ImageDetector()


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

    if len(request.text) > 50000:
        raise HTTPException(status_code=400, detail="Text exceeds maximum length of 50,000 characters")

    result = await text_detector.detect(request.text)
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
    allowed_types = ["image/png", "image/jpeg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )

    # Read file content
    content = await file.read()

    # Check file size (10MB limit)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image exceeds maximum size of 10MB")

    result = await image_detector.detect(content, file.filename or "unknown")
    return result


@router.post("/url")
async def detect_from_url(url: str) -> dict:
    """
    Detect AI-generated content from a URL.

    Fetches content from the URL and analyzes it.
    Supports text articles and images.
    """
    # TODO: Implement URL fetching and content detection
    raise HTTPException(status_code=501, detail="URL detection not yet implemented")

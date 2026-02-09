"""Detection request and response models."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ContentType(str, Enum):
      """Types of content that can be analyzed."""
      TEXT = "text"
      IMAGE = "image"
      AUDIO = "audio"
      VIDEO = "video"


class AIModel(str, Enum):
      """Known AI models for attribution."""
      GPT4 = "gpt-4"
      GPT35 = "gpt-3.5"
      CLAUDE = "claude"
      LLAMA = "llama"
      GEMINI = "gemini"
      DALLE = "dall-e"
      MIDJOURNEY = "midjourney"
      STABLE_DIFFUSION = "stable-diffusion"
      UNKNOWN = "unknown"


class TextAnalysis(BaseModel):
      """Detailed text analysis metrics."""
      perplexity: float = Field(..., description="Text perplexity score (lower = more AI-like)")
      burstiness: float = Field(..., description="Sentence complexity variation (lower = more AI-like)")
      vocabulary_richness: float = Field(..., description="Unique word ratio")
      average_sentence_length: float = Field(..., description="Mean words per sentence")
      repetition_score: float = Field(..., description="Phrase repetition detection")


class ImageAnalysis(BaseModel):
      """Detailed image analysis metrics."""
      frequency_anomaly: float = Field(..., description="FFT-based anomaly score")
      artifact_score: float = Field(..., description="AI artifact detection score")
      metadata_flags: list[str] = Field(default_factory=list, description="Suspicious metadata indicators")
      compression_analysis: Optional[str] = Field(None, description="Compression pattern notes")


class DetectionAnalysis(BaseModel):
      """Base detection analysis result."""
      signals: dict[str, float] = Field(default_factory=dict, description="Individual signal scores")
      explanation: str = Field(..., description="Human-readable explanation")


class TextDetectionRequest(BaseModel):
      """Request to detect AI-generated text."""
      text: str = Field(..., min_length=1, max_length=50000, description="Text to analyze")
      language: Optional[str] = Field(None, description="Language code (auto-detected if not provided)")


class TextDetectionResponse(BaseModel):
      """Response from text detection."""
      is_ai_generated: bool = Field(..., description="Whether text appears AI-generated")
      confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
      model_prediction: Optional[AIModel] = Field(None, description="Predicted AI model if detected")
      analysis: TextAnalysis = Field(..., description="Detailed analysis metrics")
      explanation: str = Field(..., description="Human-readable explanation of the detection")
      processing_time_ms: float = Field(..., description="Processing time in milliseconds")


class ImageDetectionResponse(BaseModel):
      """Response from image detection."""
      is_ai_generated: bool = Field(..., description="Whether image appears AI-generated")
      confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
      model_prediction: Optional[AIModel] = Field(None, description="Predicted AI model if detected")
      analysis: ImageAnalysis = Field(..., description="Detailed analysis metrics")
      explanation: str = Field(..., description="Human-readable explanation of the detection")
      filename: str = Field(..., description="Original filename")
      dimensions: tuple[int, int] = Field(..., description="Image dimensions (width, height)")
      processing_time_ms: float = Field(..., description="Processing time in milliseconds")

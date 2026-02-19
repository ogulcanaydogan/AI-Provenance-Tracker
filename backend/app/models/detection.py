"""Detection request and response models."""

from enum import Enum
from datetime import datetime
from typing import Literal, Optional

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


class AudioAnalysis(BaseModel):
      """Detailed audio analysis metrics."""
      sample_rate: int = Field(..., description="Audio sample rate in Hz")
      duration_seconds: float = Field(..., description="Audio duration in seconds")
      channel_count: int = Field(..., description="Number of audio channels")
      spectral_flatness: float = Field(..., description="Spectral flatness score")
      dynamic_range: float = Field(..., description="Signal dynamic range estimate")
      clipping_ratio: float = Field(..., description="Near-clipping sample ratio")
      zero_crossing_rate: float = Field(..., description="Zero-crossing rate")


class VideoAnalysis(BaseModel):
      """Detailed video analysis metrics."""
      file_size_mb: float = Field(..., description="Video file size in MB")
      entropy_score: float = Field(..., description="Byte entropy score (0-8)")
      byte_uniformity: float = Field(..., description="Byte distribution uniformity (0-1)")
      repeated_chunk_ratio: float = Field(..., description="Repeated chunk ratio (0-1)")
      signature_flags: list[str] = Field(default_factory=list, description="Container or metadata flags")


class DetectionAnalysis(BaseModel):
      """Base detection analysis result."""
      signals: dict[str, float] = Field(default_factory=dict, description="Individual signal scores")
      explanation: str = Field(..., description="Human-readable explanation")


class ProviderConsensusVote(BaseModel):
      """Per-provider vote used in weighted consensus."""
      provider: Literal["internal", "copyleaks", "reality_defender", "c2pa"]
      probability: float = Field(..., ge=0, le=1)
      weight: float = Field(..., ge=0)
      status: Literal["ok", "unavailable", "unsupported", "error"]
      rationale: str
      evidence_type: Optional[Literal["c2pa_manifest", "external_api", "heuristic"]] = None
      evidence_ref: Optional[str] = None
      verification_status: Optional[Literal["verified", "unverified", "unsupported", "error"]] = None


class ConsensusSummary(BaseModel):
      """Weighted consensus output across configured providers."""
      final_probability: float = Field(..., ge=0, le=1)
      threshold: float = Field(..., ge=0, le=1)
      is_ai_generated: bool
      disagreement: float = Field(..., ge=0, le=1)
      providers: list[ProviderConsensusVote] = Field(default_factory=list)


class TextDetectionRequest(BaseModel):
      """Request to detect AI-generated text."""
      text: str = Field(..., min_length=1, max_length=50000, description="Text to analyze")
      language: Optional[str] = Field(None, description="Language code (auto-detected if not provided)")

      model_config = {
          "json_schema_extra": {
              "examples": [
                  {
                      "text": (
                          "The integration of artificial intelligence into modern healthcare "
                          "systems represents a paradigm shift in how medical professionals "
                          "approach patient care and diagnosis."
                      ),
                      "language": "en",
                  }
              ]
          }
      }


class TextDetectionResponse(BaseModel):
      """Response from text detection."""
      analysis_id: Optional[str] = Field(None, description="Stored analysis identifier")
      is_ai_generated: bool = Field(..., description="Whether text appears AI-generated")
      confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
      model_prediction: Optional[AIModel] = Field(None, description="Predicted AI model if detected")
      analysis: TextAnalysis = Field(..., description="Detailed analysis metrics")
      explanation: str = Field(..., description="Human-readable explanation of the detection")
      processing_time_ms: float = Field(..., description="Processing time in milliseconds")
      consensus: Optional[ConsensusSummary] = Field(None, description="Multi-provider consensus details")


class ImageDetectionResponse(BaseModel):
      """Response from image detection."""
      analysis_id: Optional[str] = Field(None, description="Stored analysis identifier")
      is_ai_generated: bool = Field(..., description="Whether image appears AI-generated")
      confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
      model_prediction: Optional[AIModel] = Field(None, description="Predicted AI model if detected")
      analysis: ImageAnalysis = Field(..., description="Detailed analysis metrics")
      explanation: str = Field(..., description="Human-readable explanation of the detection")
      filename: str = Field(..., description="Original filename")
      dimensions: tuple[int, int] = Field(..., description="Image dimensions (width, height)")
      processing_time_ms: float = Field(..., description="Processing time in milliseconds")
      consensus: Optional[ConsensusSummary] = Field(None, description="Multi-provider consensus details")


class AudioDetectionResponse(BaseModel):
      """Response from audio detection."""
      analysis_id: Optional[str] = Field(None, description="Stored analysis identifier")
      is_ai_generated: bool = Field(..., description="Whether audio appears AI-generated")
      confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
      model_prediction: Optional[AIModel] = Field(None, description="Predicted AI model if detected")
      analysis: AudioAnalysis = Field(..., description="Detailed analysis metrics")
      explanation: str = Field(..., description="Human-readable explanation of the detection")
      filename: str = Field(..., description="Original filename")
      processing_time_ms: float = Field(..., description="Processing time in milliseconds")
      consensus: Optional[ConsensusSummary] = Field(None, description="Multi-provider consensus details")


class VideoDetectionResponse(BaseModel):
      """Response from video detection."""
      analysis_id: Optional[str] = Field(None, description="Stored analysis identifier")
      is_ai_generated: bool = Field(..., description="Whether video appears AI-generated")
      confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
      model_prediction: Optional[AIModel] = Field(None, description="Predicted AI model if detected")
      analysis: VideoAnalysis = Field(..., description="Detailed analysis metrics")
      explanation: str = Field(..., description="Human-readable explanation of the detection")
      filename: str = Field(..., description="Original filename")
      processing_time_ms: float = Field(..., description="Processing time in milliseconds")
      consensus: Optional[ConsensusSummary] = Field(None, description="Multi-provider consensus details")


class BatchTextItem(BaseModel):
      """Single text item in a batch request."""
      item_id: Optional[str] = Field(None, description="Client-provided item id")
      text: str = Field(..., min_length=1, max_length=50000, description="Text to analyze")


class BatchTextDetectionRequest(BaseModel):
      """Batch request for text detection."""
      items: list[BatchTextItem] = Field(..., min_length=1, max_length=1000)
      stop_on_error: bool = Field(
          default=False,
          description="Stop processing remaining items if one item fails",
      )

      model_config = {
          "json_schema_extra": {
              "examples": [
                  {
                      "items": [
                          {"item_id": "doc-1", "text": "Sample text for batch analysis..."},
                          {"item_id": "doc-2", "text": "Another document to check..."},
                      ],
                      "stop_on_error": False,
                  }
              ]
          }
      }


class BatchTextResultItem(BaseModel):
      """Per-item batch processing result."""
      item_id: str
      status: Literal["ok", "error"]
      result: Optional[TextDetectionResponse] = None
      error: Optional[str] = None


class BatchTextDetectionResponse(BaseModel):
      """Response for batch text detection."""
      batch_id: str
      total: int
      succeeded: int
      failed: int
      processed_at: datetime
      items: list[BatchTextResultItem]

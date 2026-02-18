from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DetectionSignal(BaseModel):
    name: str
    score: float = Field(ge=0.0, le=1.0, description="AI-likeness score (0=human, 1=AI)")
    weight: float = Field(ge=0.0, le=1.0, description="Contribution weight to final score")
    description: str


class DetectionResult(BaseModel):
    id: str
    content_type: Literal["text", "image"]
    confidence_score: float = Field(ge=0.0, le=100.0)
    verdict: Literal["human", "likely_human", "uncertain", "likely_ai", "ai_generated"]
    signals: list[DetectionSignal]
    summary: str
    analyzed_at: datetime


def compute_verdict(confidence: float) -> str:
    if confidence < 20:
        return "human"
    elif confidence < 40:
        return "likely_human"
    elif confidence < 60:
        return "uncertain"
    elif confidence < 80:
        return "likely_ai"
    else:
        return "ai_generated"

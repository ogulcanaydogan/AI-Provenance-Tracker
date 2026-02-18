from pydantic import BaseModel, Field

from app.config import settings


class TextDetectionRequest(BaseModel):
    text: str = Field(
        min_length=50,
        max_length=settings.max_text_length,
        description="Text content to analyze (minimum 50 characters)",
    )

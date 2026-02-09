"""Application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "AI Provenance Tracker"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # API
    api_prefix: str = "/api/v1"
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://provenance-detect.vercel.app",
    ]

    # Server
    host: str = "0.0.0.0"
    port: int = 8000  # Railway overrides this with PORT env var

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/provenance.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Detection settings
    text_detection_model: str = "roberta-base"
    image_detection_model: str = "resnet50"
    max_text_length: int = 50000
    max_image_size_mb: int = 10

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # API Keys (optional, for premium features)
    api_key_header: str = "X-API-Key"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

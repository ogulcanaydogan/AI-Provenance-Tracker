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
    max_audio_size_mb: int = 25
    max_video_size_mb: int = 150
    max_batch_items: int = 50

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    rate_limit_media_requests: int = 40
    rate_limit_batch_requests: int = 20
    rate_limit_intel_requests: int = 20

    # API Keys (optional, for premium features)
    require_api_key: bool = False
    api_key_header: str = "X-API-Key"
    api_keys: list[str] = []

    # Spend-control points (per client per day)
    daily_spend_cap_points: int = 1000
    spend_cost_text: int = 1
    spend_cost_image: int = 3
    spend_cost_audio: int = 4
    spend_cost_video: int = 6
    spend_cost_batch: int = 5
    spend_cost_intel: int = 8

    # X (Twitter) intelligence collection
    x_bearer_token: str = ""
    x_api_base_url: str = "https://api.x.com/2"
    x_request_timeout_seconds: float = 20.0
    x_max_pages: int = 6

    # Provider consensus layer
    consensus_enabled: bool = True
    consensus_threshold: float = 0.5
    provider_timeout_seconds: float = 8.0
    provider_internal_weight: float = 0.6
    provider_copyleaks_weight: float = 0.15
    provider_reality_defender_weight: float = 0.15
    provider_c2pa_weight: float = 0.1
    copyleaks_api_key: str = ""
    copyleaks_api_url: str = "https://api.copyleaks.com/v1/ai-content/detect"
    reality_defender_api_key: str = ""
    reality_defender_api_url: str = "https://api.realitydefender.com/v1/detect"
    c2pa_enabled: bool = True

    # Scheduled X pipeline
    scheduler_enabled: bool = False
    scheduler_handles: list[str] = []
    scheduler_interval_minutes: int = 1440
    scheduler_window_days: int = 14
    scheduler_max_posts: int = 250
    scheduler_query: str = ""
    scheduler_retry_attempts: int = 3
    scheduler_retry_backoff_seconds: float = 5.0
    scheduler_output_dir: str = "evidence/runs/scheduled"
    scheduler_send_webhooks: bool = True

    # Webhook delivery
    webhook_urls: list[str] = []
    webhook_timeout_seconds: float = 6.0
    webhook_secret: str = ""
    webhook_push_intel_alerts: bool = True

    # Calibration/evaluation tracking
    calibration_reports_dir: str = "evidence/calibration"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

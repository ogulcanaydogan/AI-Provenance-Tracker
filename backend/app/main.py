"""AI Provenance Tracker - Main application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as api_router
from app.core.config import settings
from app.db import close_database, init_database
from app.middleware.audit import audit_http_request
from app.middleware.cache_headers import cache_control_middleware
from app.middleware.error_handlers import register_error_handlers
from app.services.job_scheduler import x_pipeline_scheduler

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger.info("Starting AI Provenance Tracker", version=settings.app_version)
    await init_database()
    if settings.run_scheduler_in_api:
        await x_pipeline_scheduler.start()
    yield
    if settings.run_scheduler_in_api:
        await x_pipeline_scheduler.stop()
    await close_database()
    logger.info("Shutting down AI Provenance Tracker")


openapi_tags = [
    {
        "name": "detection",
        "description": "Detect AI-generated content across text, image, audio, and video modalities.",
    },
    {
        "name": "batch",
        "description": "Batch processing endpoints for high-throughput text analysis.",
    },
    {
        "name": "analysis",
        "description": (
            "Analysis history, aggregate statistics, dashboard analytics, "
            "audit events, and calibration/evaluation metrics."
        ),
    },
    {
        "name": "intel",
        "description": "X (Twitter) intelligence collection, trust reports, and cost estimation.",
    },
]

app = FastAPI(
    title=settings.app_name,
    description=(
        "Open-source multi-modal AI content detection platform. "
        "Analyse text, images, audio, and video for AI-generated signals "
        "with explainable scoring, multi-provider consensus, and full audit trail."
    ),
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    openapi_tags=openapi_tags,
)

# CORS middleware — hardened to explicit methods, headers, and preflight caching
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-API-Key",
        "X-Request-ID",
        "X-Actor-ID",
    ],
    expose_headers=[
        "X-Request-ID",
        "Retry-After",
        "X-RateLimit-Remaining",
    ],
    max_age=600,
)
app.middleware("http")(audit_http_request)
app.middleware("http")(cache_control_middleware)

# Global error handlers (structured JSON errors with request IDs)
register_error_handlers(app)

# Prometheus /metrics endpoint
if settings.enable_prometheus:
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=False,
        excluded_handlers=["/health", "/metrics", "/docs", "/redoc", "/openapi.json"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.get("/health")
async def health_check(deep: bool = False) -> dict:
    """Health check endpoint.

    Pass ?deep=true to verify database and Redis connectivity.
    """
    result: dict = {"status": "healthy", "version": settings.app_version}

    if not deep:
        return result

    checks: dict[str, str] = {}

    # Database connectivity
    try:
        from app.db.session import get_db_session
        from sqlalchemy import text

        async with get_db_session() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        result["status"] = "degraded"

    # Redis connectivity (optional — Redis may not be deployed)
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"unavailable: {exc}"
        # Redis is optional so this is non-fatal

    result["checks"] = checks
    return result


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with API info."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "api": settings.api_prefix,
    }


# Include API router
app.include_router(api_router, prefix=settings.api_prefix)

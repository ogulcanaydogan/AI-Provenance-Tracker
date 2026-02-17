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


app = FastAPI(
    title=settings.app_name,
    description="Detect AI-generated content, trace origins, verify authenticity",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(audit_http_request)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.app_version}


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

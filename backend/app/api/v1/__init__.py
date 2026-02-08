"""API v1 router."""

from fastapi import APIRouter

from app.api.v1.detect import router as detect_router
from app.api.v1.analyze import router as analyze_router

router = APIRouter()

router.include_router(detect_router, prefix="/detect", tags=["detection"])
router.include_router(analyze_router, prefix="/analyze", tags=["analysis"])

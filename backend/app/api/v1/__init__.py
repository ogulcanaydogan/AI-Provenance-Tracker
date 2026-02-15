"""API v1 router."""

from fastapi import APIRouter, Depends

from app.api.v1.batch import router as batch_router
from app.api.v1.detect import router as detect_router
from app.api.v1.analyze import router as analyze_router
from app.api.v1.intel import router as intel_router
from app.middleware.rate_limiter import rate_limit

router = APIRouter(dependencies=[Depends(rate_limit)])

router.include_router(detect_router, prefix="/detect", tags=["detection"])
router.include_router(batch_router, prefix="/batch", tags=["batch"])
router.include_router(analyze_router, prefix="/analyze", tags=["analysis"])
router.include_router(intel_router, prefix="/intel", tags=["intel"])

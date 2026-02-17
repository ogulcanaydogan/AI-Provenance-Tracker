"""Analysis API endpoints for detailed content inspection."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.analysis_store import analysis_store
from app.services.audit_events import audit_event_store
from app.services.evaluation_store import evaluation_store

router = APIRouter()


class AnalysisRequest(BaseModel):
    """Request for detailed analysis."""
    content_id: str
    include_metadata: bool = True
    include_timeline: bool = False


class AnalysisResponse(BaseModel):
    """Detailed analysis response."""
    content_id: str
    analysis_type: str
    details: dict
    metadata: dict | None = None


@router.post("/detailed", response_model=AnalysisResponse)
async def detailed_analysis(request: AnalysisRequest) -> AnalysisResponse:
    """
    Get detailed analysis of previously detected content.

    Provides in-depth breakdown of detection signals
    and metadata forensics.
    """
    record = await analysis_store.get_record(request.content_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    details = {
        "analysis_id": record.analysis_id,
        "content_type": record.content_type,
        "result": record.result,
    }

    metadata = None
    if request.include_metadata:
        metadata = {
            "created_at": record.created_at.isoformat(),
            "source": record.source,
            "source_url": record.source_url,
            "content_hash": record.content_hash,
            "input_size": record.input_size,
            "filename": record.filename,
        }

        if request.include_timeline:
            metadata["timeline"] = [
                {
                    "event": "content_analyzed",
                    "at": record.created_at.isoformat(),
                    "content_type": record.content_type,
                }
            ]

    return AnalysisResponse(
        content_id=record.analysis_id,
        analysis_type=record.content_type,
        details=details,
        metadata=metadata,
    )


@router.get("/history")
async def get_analysis_history(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """
    Get history of past analyses.

    Returns paginated list of previous detection results.
    """
    items, total = await analysis_store.get_history(limit=limit, offset=offset)
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/stats")
async def get_stats() -> dict:
    """
    Get aggregate statistics.

    Returns overall detection statistics and trends.
    """
    return await analysis_store.get_stats()


@router.get("/dashboard")
async def get_dashboard(days: int = Query(default=14, ge=1, le=90)) -> dict:
    """
    Get dashboard-ready analytics for recent activity.

    Returns windowed totals, source/type breakdown, top predicted models,
    and per-day timeline metrics.
    """
    return await analysis_store.get_dashboard(days=days)


@router.get("/evaluation")
async def get_evaluation(days: int = Query(default=90, ge=1, le=365)) -> dict:
    """
    Get calibration/evaluation trend metrics for dashboard.
    """
    return evaluation_store.get_summary(days=days)


@router.get("/audit-events")
async def get_audit_events(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    event_type: str = Query(default="", max_length=64),
    severity: str = Query(default="", max_length=16),
) -> dict:
    """
    Get paginated audit events for compliance and security analysis.
    """
    items, total = await audit_event_store.list_events(
        limit=limit,
        offset=offset,
        event_type=event_type.strip() or None,
        severity=severity.strip() or None,
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "event_type": event_type.strip() or None,
        "severity": severity.strip() or None,
    }

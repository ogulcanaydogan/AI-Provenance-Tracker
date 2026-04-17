"""Analysis API endpoints for detailed content inspection."""

from __future__ import annotations

import csv
import io
import json as json_lib

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.config import settings
from app.middleware.rate_limiter import _client_identifier, rate_limiter
from app.services.api_key_plan_store import api_key_plan_store
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


def _derive_verdict(record_result: dict) -> str:
    decision_band = str(record_result.get("decision_band") or "").strip().lower()
    if decision_band == "ai":
        return "likely_ai"
    if decision_band == "human":
        return "likely_human"
    if decision_band == "uncertain":
        return "uncertain"
    return "likely_ai" if bool(record_result.get("is_ai_generated")) else "likely_human"


def _build_evidence_payload(record) -> dict:
    result = record.result if isinstance(record.result, dict) else {}
    detector_versions = {
        "model_version": result.get("model_version"),
        "calibration_version": result.get("calibration_version"),
    }
    trace = {
        "route_profile": result.get("domain_profile"),
        "uncertainty_flags": result.get("uncertainty_flags", []),
        "chunk_summary": result.get("chunk_consistency"),
        "disagreement_reasons": [
            item
            for item in [result.get("uncertainty_reason")]
            if isinstance(item, str) and item.strip()
        ],
        "artifact_lineage": {
            "model_bundle_version": settings.text_model_bundle_version or None,
            "calibration_bundle_version": settings.text_calibration_bundle_version or None,
            "private_benchmark_manifest": settings.text_private_benchmark_manifest or None,
        },
    }
    return {
        "analysis_id": record.analysis_id,
        "content_type": record.content_type,
        "verdict": _derive_verdict(result),
        "confidence": float(result.get("confidence", 0.0) or 0.0),
        "decision_band": result.get("decision_band"),
        "uncertainty_reason": result.get("uncertainty_reason"),
        "timestamp": record.created_at.isoformat(),
        "source": record.source,
        "source_url": record.source_url,
        "explanation": result.get("explanation"),
        "detector_versions": detector_versions,
        "trace": trace,
    }


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


@router.get("/evidence/{analysis_id}")
async def get_evidence_pack(analysis_id: str) -> dict:
    """
    Return a machine-readable shareable evidence pack for a single analysis id.
    """
    record = await analysis_store.get_record(analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return _build_evidence_payload(record)


@router.get("/history")
async def get_analysis_history(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    content_type: str = Query(default="", max_length=16),
) -> dict:
    """
    Get history of past analyses.

    Returns paginated list of previous detection results.
    Optionally filter by content_type (text, image, audio, video).
    """
    items, total = await analysis_store.get_history(
        limit=limit,
        offset=offset,
        content_type=content_type.strip() or None,
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "content_type": content_type.strip() or None,
    }


@router.get("/usage")
async def get_usage_metering(request: Request) -> dict:
    """
    Return current usage metering for caller API key/IP and monthly leaderboard snapshot.
    """
    api_key = request.headers.get(settings.api_key_header)
    client_key = api_key or _client_identifier(request)
    plan = await api_key_plan_store.resolve_plan(api_key)
    current = await rate_limiter.get_client_usage(client_key, plan=plan)
    top_monthly = await rate_limiter.list_monthly_usage()
    return {
        "current": current,
        "top_monthly": top_monthly[:25],
    }


@router.get("/history/export")
async def export_history(
    format: str = Query(default="json", pattern="^(json|csv)$"),
    content_type: str = Query(default="", max_length=16),
) -> StreamingResponse:
    """
    Export analysis history as JSON or CSV download.

    Returns up to 10 000 records as a downloadable file.
    """
    items, _ = await analysis_store.get_history(
        limit=10_000,
        offset=0,
        content_type=content_type.strip() or None,
    )

    if format == "csv":
        output = io.StringIO()
        if items:
            writer = csv.DictWriter(output, fieldnames=list(items[0].keys()))
            writer.writeheader()
            writer.writerows(items)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=analysis_history.csv"},
        )

    return StreamingResponse(
        iter([json_lib.dumps(items, indent=2, default=str)]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=analysis_history.json"},
    )


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


@router.get("/dashboard/export")
async def export_dashboard(
    days: int = Query(default=14, ge=1, le=90),
    format: str = Query(default="json", pattern="^(json|csv)$"),
) -> StreamingResponse:
    """
    Export dashboard data as JSON or CSV download.
    """
    data = await analysis_store.get_dashboard(days=days)

    if format == "csv":
        output = io.StringIO()
        timeline = data.get("timeline", [])
        if timeline:
            writer = csv.DictWriter(
                output,
                fieldnames=list(timeline[0].keys()),
            )
            writer.writeheader()
            writer.writerows(timeline)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=dashboard_timeline.csv"},
        )

    return StreamingResponse(
        iter([json_lib.dumps(data, indent=2, default=str)]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=dashboard.json"},
    )


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

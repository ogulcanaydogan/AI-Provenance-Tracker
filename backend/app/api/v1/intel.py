"""Threat intelligence API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.x_intel import XIntelCollectionRequest, XIntelInput
from app.services.trust_report import generate_trust_report, generate_x_drilldown
from app.services.x_intel import XDataCollectionError, XIntelCollector

router = APIRouter()
collector = XIntelCollector()


@router.post("/x/collect", response_model=XIntelInput)
async def collect_x_intel(request: XIntelCollectionRequest) -> XIntelInput:
    """
    Collect and normalize X data for trust-and-safety report generation.

    Returns the exact input schema required by the downstream reputation analysis prompt.
    """
    try:
        return await collector.collect(
            target_handle=request.target_handle,
            window_days=request.window_days,
            max_posts=request.max_posts,
            query=request.query,
            user_context=request.user_context,
        )
    except XDataCollectionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/x/report")
async def generate_x_report(payload: XIntelInput) -> dict:
    """
    Generate trust-and-safety report JSON from normalized X intelligence input.
    """
    return generate_trust_report(payload)


@router.post("/x/drilldown")
async def generate_x_drilldown_view(payload: XIntelInput) -> dict:
    """
    Generate dashboard drill-down data (clusters, claims timeline, alerts).
    """
    return generate_x_drilldown(payload)

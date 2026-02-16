"""Threat intelligence API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.models.x_intel import (
    XIntelCollectionRequest,
    XIntelEstimateRequest,
    XIntelEstimateResponse,
    XIntelInput,
)
from app.services.job_scheduler import x_pipeline_scheduler
from app.services.trust_report import generate_trust_report, generate_x_drilldown
from app.services.webhook_dispatcher import webhook_dispatcher
from app.services.x_intel import XDataCollectionError, XIntelCollector

router = APIRouter()
collector = XIntelCollector()


def _recommended_max_posts(page_cap: int, request_cap: int, default_max: int) -> int:
    low = 20
    high = 1000
    best = low
    while low <= high:
        mid = (low + high) // 2
        estimate = XIntelCollector.estimate_request_plan(max_posts=mid, max_pages=page_cap)
        if estimate["estimated_requests"] <= request_cap:
            best = mid
            low = mid + 1
        else:
            high = mid - 1
    return min(best, default_max)


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


@router.post("/x/collect/estimate", response_model=XIntelEstimateResponse)
async def estimate_x_collect_cost(request: XIntelEstimateRequest) -> XIntelEstimateResponse:
    """
    Estimate X API request usage for a collect run without making any external API calls.
    """
    page_cap = request.max_pages if request.max_pages is not None else settings.x_max_pages
    plan = collector.estimate_request_plan(max_posts=request.max_posts, max_pages=page_cap)
    max_requests_per_run = max(1, settings.x_max_requests_per_run)
    within_budget = (
        plan["estimated_requests"] <= max_requests_per_run
        if settings.x_cost_guard_enabled
        else True
    )
    recommended_max_posts = _recommended_max_posts(
        page_cap=plan["page_cap"],
        request_cap=max_requests_per_run,
        default_max=request.max_posts,
    )
    return XIntelEstimateResponse(
        estimated_requests=plan["estimated_requests"],
        worst_case_requests=plan["worst_case_requests"],
        page_cap=plan["page_cap"],
        target_limit=plan["target_limit"],
        mention_limit=plan["mention_limit"],
        interaction_limit=plan["interaction_limit"],
        guard_enabled=settings.x_cost_guard_enabled,
        max_requests_per_run=max_requests_per_run,
        within_budget=within_budget,
        recommended_max_posts=recommended_max_posts,
    )


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
    drilldown = generate_x_drilldown(payload)
    if settings.webhook_push_intel_alerts and drilldown.get("alerts"):
        await webhook_dispatcher.dispatch(
            "intel_drilldown_alerts",
            {
                "target": drilldown.get("target"),
                "window": drilldown.get("window"),
                "alerts": drilldown.get("alerts"),
            },
        )
    return drilldown


@router.get("/x/scheduler/status")
async def get_scheduler_status() -> dict:
    """Return scheduler runtime status."""
    return x_pipeline_scheduler.status()


@router.post("/x/scheduler/run")
async def trigger_scheduler_run(handle: str | None = Query(default=None)) -> dict:
    """Trigger one immediate scheduled run (single handle or configured set)."""
    return await x_pipeline_scheduler.trigger_once(handle=handle)

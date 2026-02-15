"""Background scheduler for recurring X collection/report jobs."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any

import structlog

from app.core.config import settings
from app.models.x_intel import UserContext
from app.services.trust_report import generate_trust_report, generate_x_drilldown
from app.services.webhook_dispatcher import webhook_dispatcher
from app.services.x_intel import XIntelCollector

logger = structlog.get_logger()


def _slug_handle(handle: str) -> str:
    raw = handle.strip().lstrip("@").lower()
    slug = re.sub(r"[^a-z0-9_]+", "-", raw).strip("-")
    return slug or "target"


class XPipelineScheduler:
    """Runs scheduled collection/report tasks with retry and webhook delivery."""

    def __init__(self) -> None:
        self._collector = XIntelCollector()
        self._task: asyncio.Task[None] | None = None
        self._last_runs: dict[str, dict[str, Any]] = {}

    def _handles(self) -> list[str]:
        handles = []
        for handle in settings.scheduler_handles:
            cleaned = handle.strip()
            if cleaned:
                handles.append(cleaned if cleaned.startswith("@") else f"@{cleaned}")
        return handles

    async def start(self) -> None:
        if not settings.scheduler_enabled:
            return
        if not self._handles():
            logger.info("scheduler_start_skipped", reason="no_handles_configured")
            return
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._run_loop())
        logger.info("scheduler_started", handles=self._handles(), interval_minutes=settings.scheduler_interval_minutes)

    async def stop(self) -> None:
        if not self._task:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("scheduler_stopped")

    def status(self) -> dict[str, Any]:
        return {
            "enabled": settings.scheduler_enabled,
            "running": bool(self._task and not self._task.done()),
            "handles": self._handles(),
            "interval_minutes": settings.scheduler_interval_minutes,
            "last_runs": self._last_runs,
        }

    async def trigger_once(self, handle: str | None = None) -> dict[str, Any]:
        if handle:
            normalized = handle if handle.startswith("@") else f"@{handle}"
            return await self._run_for_handle(normalized)

        results = []
        for current in self._handles():
            results.append(await self._run_for_handle(current))
        return {"triggered": len(results), "results": results}

    async def _run_loop(self) -> None:
        interval_seconds = max(60, settings.scheduler_interval_minutes * 60)
        while True:
            for handle in self._handles():
                await self._run_for_handle(handle)
            await asyncio.sleep(interval_seconds)

    async def _run_for_handle(self, handle: str) -> dict[str, Any]:
        started_at = datetime.now(UTC)
        attempts = max(1, settings.scheduler_retry_attempts)
        backoff = max(0.1, settings.scheduler_retry_backoff_seconds)
        slug = _slug_handle(handle)

        for attempt in range(1, attempts + 1):
            try:
                user_context = UserContext(
                    sector="unknown",
                    risk_tolerance="medium",
                    preferred_language="tr",
                    user_profile="brand",
                    legal_pr_capacity="basic",
                    goal="reputation_protection",
                )
                intel_input = await self._collector.collect(
                    target_handle=handle,
                    window_days=settings.scheduler_window_days,
                    max_posts=settings.scheduler_max_posts,
                    query=settings.scheduler_query or None,
                    user_context=user_context,
                )
                payload = intel_input.model_dump(mode="json")
                report = generate_trust_report(payload)
                drilldown = generate_x_drilldown(payload)

                timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
                run_dir = Path(settings.scheduler_output_dir).expanduser().resolve() / f"{slug}_{timestamp}"
                run_dir.mkdir(parents=True, exist_ok=True)
                input_path = run_dir / "x_intel_input.json"
                report_path = run_dir / "x_trust_report.json"
                drilldown_path = run_dir / "x_drilldown.json"
                manifest_path = run_dir / "manifest.json"

                input_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                drilldown_path.write_text(json.dumps(drilldown, ensure_ascii=False, indent=2), encoding="utf-8")

                result = {
                    "handle": handle,
                    "status": "success",
                    "attempt": attempt,
                    "started_at": started_at.isoformat(),
                    "finished_at": datetime.now(UTC).isoformat(),
                    "run_dir": str(run_dir),
                    "alerts": len(drilldown.get("alerts", [])),
                }
                manifest_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                self._last_runs[handle.lower()] = result
                logger.info("scheduler_run_success", **result)

                if settings.scheduler_send_webhooks:
                    await webhook_dispatcher.dispatch("scheduled_pipeline_success", result)
                    if drilldown.get("alerts"):
                        await webhook_dispatcher.dispatch(
                            "scheduled_pipeline_alerts",
                            {
                                "handle": handle,
                                "alerts": drilldown["alerts"],
                                "run_dir": str(run_dir),
                            },
                        )
                return result
            except Exception as exc:  # noqa: BLE001
                logger.warning("scheduler_run_failed", handle=handle, attempt=attempt, error=str(exc))
                if attempt < attempts:
                    await asyncio.sleep(backoff * (2 ** (attempt - 1)))
                    continue

                failure = {
                    "handle": handle,
                    "status": "failed",
                    "attempt": attempt,
                    "started_at": started_at.isoformat(),
                    "finished_at": datetime.now(UTC).isoformat(),
                    "error": str(exc),
                }
                self._last_runs[handle.lower()] = failure
                if settings.scheduler_send_webhooks:
                    await webhook_dispatcher.dispatch("scheduled_pipeline_failed", failure)
                return failure


x_pipeline_scheduler = XPipelineScheduler()


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
        self._auto_disabled = False
        self._usage_state = self._load_usage_state()

    @staticmethod
    def _usage_file_path() -> Path:
        return Path(settings.scheduler_usage_file).expanduser().resolve()

    @staticmethod
    def _month_key(now: datetime | None = None) -> str:
        current = now or datetime.now(UTC)
        return current.strftime("%Y-%m")

    def _load_usage_state(self) -> dict[str, Any]:
        path = self._usage_file_path()
        if not path.exists():
            return {"months": {}}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"months": {}}
        if not isinstance(payload, dict):
            return {"months": {}}
        months = payload.get("months")
        if not isinstance(months, dict):
            return {"months": {}}
        return {"months": months}

    def _save_usage_state(self) -> None:
        path = self._usage_file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self._usage_state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _month_record(self, month_key: str | None = None) -> dict[str, Any]:
        key = month_key or self._month_key()
        months = self._usage_state.setdefault("months", {})
        raw = months.setdefault(
            key,
            {
                "requests_used": 0,
                "runs": 0,
                "blocked_runs": 0,
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )
        raw["requests_used"] = int(raw.get("requests_used", 0) or 0)
        raw["runs"] = int(raw.get("runs", 0) or 0)
        raw["blocked_runs"] = int(raw.get("blocked_runs", 0) or 0)
        raw["updated_at"] = str(raw.get("updated_at") or datetime.now(UTC).isoformat())
        return raw

    def _monthly_budget(self) -> dict[str, Any]:
        month = self._month_key()
        record = self._month_record(month)
        cap_requests = max(0, int(settings.scheduler_monthly_request_cap))
        used_requests = int(record.get("requests_used", 0) or 0)
        remaining_requests = None if cap_requests == 0 else max(0, cap_requests - used_requests)
        return {
            "month": month,
            "cap_requests": cap_requests,
            "used_requests": used_requests,
            "remaining_requests": remaining_requests,
            "blocked_runs": int(record.get("blocked_runs", 0) or 0),
            "usage_file": str(self._usage_file_path()),
        }

    def _record_consumed_requests(self, requests_used: int) -> None:
        if requests_used <= 0:
            return
        record = self._month_record()
        record["requests_used"] = int(record.get("requests_used", 0)) + int(requests_used)
        record["runs"] = int(record.get("runs", 0)) + 1
        record["updated_at"] = datetime.now(UTC).isoformat()
        self._save_usage_state()

    def _record_blocked_run(self) -> None:
        record = self._month_record()
        record["blocked_runs"] = int(record.get("blocked_runs", 0)) + 1
        record["updated_at"] = datetime.now(UTC).isoformat()
        self._save_usage_state()

    async def _activate_kill_switch(self, reason: str, budget: dict[str, Any]) -> None:
        if self._auto_disabled:
            return
        self._auto_disabled = True
        logger.warning("scheduler_kill_switch_activated", reason=reason, budget=budget)

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
        if self._auto_disabled:
            logger.info("scheduler_start_skipped", reason="kill_switch_active")
            return
        if not self._handles():
            logger.info("scheduler_start_skipped", reason="no_handles_configured")
            return
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "scheduler_started",
            handles=self._handles(),
            interval_minutes=settings.scheduler_interval_minutes,
        )

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
            "enabled": settings.scheduler_enabled and not self._auto_disabled,
            "configured_enabled": settings.scheduler_enabled,
            "auto_disabled": self._auto_disabled,
            "running": bool(self._task and not self._task.done()),
            "handles": self._handles(),
            "interval_minutes": settings.scheduler_interval_minutes,
            "last_runs": self._last_runs,
            "monthly_budget": self._monthly_budget(),
        }

    async def trigger_once(self, handle: str | None = None) -> dict[str, Any]:
        if self._auto_disabled:
            if handle:
                normalized = handle if handle.startswith("@") else f"@{handle}"
                return {
                    "handle": normalized,
                    "status": "blocked",
                    "reason": "kill_switch_active",
                    "monthly_budget": self._monthly_budget(),
                }
            return {
                "triggered": 0,
                "results": [],
                "status": "blocked",
                "reason": "kill_switch_active",
                "monthly_budget": self._monthly_budget(),
            }

        if handle:
            normalized = handle if handle.startswith("@") else f"@{handle}"
            return await self._run_for_handle(normalized)

        results = []
        for current in self._handles():
            results.append(await self._run_for_handle(current))
        return {
            "triggered": len(results),
            "results": results,
            "monthly_budget": self._monthly_budget(),
        }

    async def _run_loop(self) -> None:
        interval_seconds = max(60, settings.scheduler_interval_minutes * 60)
        while True:
            if self._auto_disabled:
                logger.warning("scheduler_loop_stopped", reason="kill_switch_active")
                return
            for handle in self._handles():
                if self._auto_disabled:
                    break
                await self._run_for_handle(handle)
            if self._auto_disabled:
                logger.warning("scheduler_loop_stopped", reason="kill_switch_active")
                return
            await asyncio.sleep(interval_seconds)

    async def _run_for_handle(self, handle: str) -> dict[str, Any]:
        started_at = datetime.now(UTC)
        attempts = max(1, settings.scheduler_retry_attempts)
        backoff = max(0.1, settings.scheduler_retry_backoff_seconds)
        slug = _slug_handle(handle)
        requests_consumed_total = 0

        plan = self._collector.estimate_request_plan(max_posts=settings.scheduler_max_posts)
        budget = self._monthly_budget()
        projected_requests = budget["used_requests"] + plan["estimated_requests"]
        if budget["cap_requests"] > 0 and projected_requests > budget["cap_requests"]:
            self._record_blocked_run()
            failure = {
                "handle": handle,
                "status": "blocked",
                "reason": "monthly_request_cap",
                "started_at": started_at.isoformat(),
                "finished_at": datetime.now(UTC).isoformat(),
                "estimated_requests": plan["estimated_requests"],
                "monthly_cap": budget["cap_requests"],
                "monthly_used": budget["used_requests"],
            }
            if settings.scheduler_kill_switch_on_cap:
                await self._activate_kill_switch(
                    "monthly_request_cap_exceeded", self._monthly_budget()
                )
                failure["kill_switch_activated"] = True
            self._last_runs[handle.lower()] = failure
            logger.warning("scheduler_run_blocked", **failure)
            if settings.scheduler_send_webhooks:
                await webhook_dispatcher.dispatch("scheduled_pipeline_blocked", failure)
            return failure

        for attempt in range(1, attempts + 1):
            attempt_requests = 0
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
                attempt_requests = self._collector.request_count

                payload = intel_input.model_dump(mode="json")
                report = generate_trust_report(payload)
                drilldown = generate_x_drilldown(payload)

                timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
                run_dir = (
                    Path(settings.scheduler_output_dir).expanduser().resolve()
                    / f"{slug}_{timestamp}"
                )
                run_dir.mkdir(parents=True, exist_ok=True)
                input_path = run_dir / "x_intel_input.json"
                report_path = run_dir / "x_trust_report.json"
                drilldown_path = run_dir / "x_drilldown.json"
                manifest_path = run_dir / "manifest.json"

                input_path.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                report_path.write_text(
                    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                drilldown_path.write_text(
                    json.dumps(drilldown, ensure_ascii=False, indent=2), encoding="utf-8"
                )

                requests_consumed_total += attempt_requests
                self._record_consumed_requests(requests_consumed_total)
                budget_after = self._monthly_budget()

                result = {
                    "handle": handle,
                    "status": "success",
                    "attempt": attempt,
                    "started_at": started_at.isoformat(),
                    "finished_at": datetime.now(UTC).isoformat(),
                    "run_dir": str(run_dir),
                    "alerts": len(drilldown.get("alerts", [])),
                    "requests_used": requests_consumed_total,
                    "monthly_used": budget_after["used_requests"],
                    "monthly_remaining": budget_after["remaining_requests"],
                }
                manifest_path.write_text(
                    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
                )
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

                if (
                    settings.scheduler_kill_switch_on_cap
                    and budget_after["cap_requests"] > 0
                    and budget_after["remaining_requests"] == 0
                ):
                    await self._activate_kill_switch("monthly_request_cap_reached", budget_after)
                    result["kill_switch_activated"] = True

                return result
            except Exception as exc:  # noqa: BLE001
                if attempt_requests == 0:
                    attempt_requests = self._collector.request_count
                requests_consumed_total += attempt_requests
                logger.warning(
                    "scheduler_run_failed",
                    handle=handle,
                    attempt=attempt,
                    error=str(exc),
                    requests_used=requests_consumed_total,
                )
                if attempt < attempts:
                    await asyncio.sleep(backoff * (2 ** (attempt - 1)))
                    continue

                self._record_consumed_requests(requests_consumed_total)
                budget_after = self._monthly_budget()
                failure = {
                    "handle": handle,
                    "status": "failed",
                    "attempt": attempt,
                    "started_at": started_at.isoformat(),
                    "finished_at": datetime.now(UTC).isoformat(),
                    "error": str(exc),
                    "requests_used": requests_consumed_total,
                    "monthly_used": budget_after["used_requests"],
                    "monthly_remaining": budget_after["remaining_requests"],
                }
                if (
                    settings.scheduler_kill_switch_on_cap
                    and budget_after["cap_requests"] > 0
                    and budget_after["remaining_requests"] == 0
                ):
                    await self._activate_kill_switch("monthly_request_cap_reached", budget_after)
                    failure["kill_switch_activated"] = True

                self._last_runs[handle.lower()] = failure
                if settings.scheduler_send_webhooks:
                    await webhook_dispatcher.dispatch("scheduled_pipeline_failed", failure)
                return failure


x_pipeline_scheduler = XPipelineScheduler()

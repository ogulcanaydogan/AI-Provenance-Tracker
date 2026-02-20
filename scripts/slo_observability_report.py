#!/usr/bin/env python3
"""Build an observability report from GitHub workflow history."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class Alert:
    level: str
    source: str
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute SLO proxies from workflow run history.")
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", ""), help="GitHub repo owner/name")
    parser.add_argument(
        "--gh-token",
        default=os.getenv("GH_TOKEN", os.getenv("GITHUB_TOKEN", "")),
        help="GitHub token (defaults to GH_TOKEN or GITHUB_TOKEN)",
    )
    parser.add_argument("--window-days", type=int, default=7, help="Rolling window in days")
    parser.add_argument(
        "--smoke-workflow-name",
        default="Production Smoke Tests",
        help="Workflow name used for production smoke checks",
    )
    parser.add_argument(
        "--deploy-workflow-name",
        default="Deploy Spark Runtime",
        help="Workflow name used for deploy operations",
    )
    parser.add_argument("--smoke-success-slo", type=float, default=0.98)
    parser.add_argument("--deploy-success-slo", type=float, default=0.95)
    parser.add_argument("--output-json", default="ops/reports/slo_observability_report.json")
    parser.add_argument("--output-md", default="ops/reports/slo_observability_report.md")
    parser.add_argument(
        "--fail-on-alert-level",
        choices=("none", "warn", "critical"),
        default="none",
    )
    return parser.parse_args()


def _parse_repo(repo: str) -> tuple[str, str]:
    if "/" not in repo:
        raise ValueError("Invalid --repo value. Expected owner/name.")
    owner, name = repo.split("/", 1)
    owner = owner.strip()
    name = name.strip()
    if not owner or not name:
        raise ValueError("Invalid --repo value. Expected owner/name.")
    return owner, name


def _iso_to_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _request_json(url: str, token: str) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-provenance-slo-report/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=30) as response:
        text = response.read().decode("utf-8")
    return json.loads(text) if text else {}


def _fetch_runs(owner: str, repo: str, token: str, since: datetime) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    page = 1
    per_page = 100
    while page <= 10:
        url = (
            f"https://api.github.com/repos/{owner}/{repo}/actions/runs?"
            f"per_page={per_page}&page={page}"
        )
        payload = _request_json(url, token)
        batch = payload.get("workflow_runs", [])
        if not isinstance(batch, list) or not batch:
            break

        stop = False
        for run in batch:
            created_raw = run.get("created_at")
            if not isinstance(created_raw, str):
                continue
            if _iso_to_dt(created_raw) < since:
                stop = True
                continue
            runs.append(run)

        if stop or len(batch) < per_page:
            break
        page += 1
    return runs


def _duration_minutes(run: dict[str, Any]) -> float:
    started_raw = run.get("run_started_at") or run.get("created_at")
    completed_raw = run.get("updated_at")
    if not isinstance(started_raw, str) or not isinstance(completed_raw, str):
        return 0.0
    started = _iso_to_dt(started_raw)
    completed = _iso_to_dt(completed_raw)
    return max((completed - started).total_seconds(), 0.0) / 60.0


def _summarize_named_runs(runs: list[dict[str, Any]], workflow_name: str) -> dict[str, Any]:
    selected = [run for run in runs if str(run.get("name") or "") == workflow_name]
    total = len(selected)
    success = 0
    failed = 0
    cancelled = 0
    minutes = 0.0
    for run in selected:
        minutes += _duration_minutes(run)
        conclusion = str(run.get("conclusion") or "")
        if conclusion == "success":
            success += 1
        elif conclusion in {"failure", "timed_out", "action_required"}:
            failed += 1
        elif conclusion in {"cancelled", "skipped"}:
            cancelled += 1

    success_rate = (success / total) if total else 0.0
    failure_rate = (failed / total) if total else 0.0
    return {
        "workflow_name": workflow_name,
        "runs": total,
        "success_runs": success,
        "failed_runs": failed,
        "cancelled_runs": cancelled,
        "success_rate": round(success_rate, 4),
        "failure_rate": round(failure_rate, 4),
        "runtime_minutes": round(minutes, 2),
    }


def _level_rank(level: str) -> int:
    return {"none": 0, "warn": 1, "critical": 2}.get(level, 0)


def _build_alerts(
    smoke: dict[str, Any],
    deploy: dict[str, Any],
    smoke_slo: float,
    deploy_slo: float,
) -> list[Alert]:
    alerts: list[Alert] = []
    if smoke["runs"] == 0:
        alerts.append(
            Alert(level="warn", source="smoke", message="No smoke runs found in selected window.")
        )
    elif float(smoke["success_rate"]) < smoke_slo:
        alerts.append(
            Alert(
                level="critical",
                source="smoke",
                message=(
                    f"Smoke success rate {float(smoke['success_rate']):.2%} is below SLO "
                    f"{smoke_slo:.2%}."
                ),
            )
        )

    if deploy["runs"] == 0:
        alerts.append(
            Alert(level="warn", source="deploy", message="No deploy runs found in selected window.")
        )
    elif float(deploy["success_rate"]) < deploy_slo:
        alerts.append(
            Alert(
                level="warn",
                source="deploy",
                message=(
                    f"Deploy success rate {float(deploy['success_rate']):.2%} is below SLO "
                    f"{deploy_slo:.2%}."
                ),
            )
        )
    return alerts


def _build_markdown(
    generated_at: str,
    repo: str,
    window_days: int,
    smoke: dict[str, Any],
    deploy: dict[str, Any],
    alerts: list[Alert],
) -> str:
    lines = [
        "# SLO Observability Report",
        "",
        f"- Repository: `{repo}`",
        f"- Generated: `{generated_at}`",
        f"- Window: `{window_days} days`",
        "",
        "## Service Proxies",
        "",
        "| Signal | Runs | Success | Failed | Success Rate | Runtime Minutes |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        (
            f"| {smoke['workflow_name']} | {smoke['runs']} | {smoke['success_runs']} | "
            f"{smoke['failed_runs']} | {float(smoke['success_rate']):.2%} | "
            f"{smoke['runtime_minutes']} |"
        ),
        (
            f"| {deploy['workflow_name']} | {deploy['runs']} | {deploy['success_runs']} | "
            f"{deploy['failed_runs']} | {float(deploy['success_rate']):.2%} | "
            f"{deploy['runtime_minutes']} |"
        ),
        "",
        "## Alerts",
        "",
    ]
    if not alerts:
        lines.append("- None")
    else:
        for alert in alerts:
            lines.append(f"- [{alert.level.upper()}] {alert.source}: {alert.message}")
    lines.append("")
    return "\n".join(lines)


def run() -> int:
    args = parse_args()
    if not args.gh_token:
        raise RuntimeError("Missing GitHub token. Set --gh-token or GITHUB_TOKEN.")
    owner, repo = _parse_repo(args.repo)
    now = datetime.now(UTC)
    since = now - timedelta(days=max(args.window_days, 1))
    generated_at = now.isoformat()

    runs = _fetch_runs(owner, repo, args.gh_token, since)
    smoke = _summarize_named_runs(runs, args.smoke_workflow_name)
    deploy = _summarize_named_runs(runs, args.deploy_workflow_name)
    alerts = _build_alerts(smoke, deploy, args.smoke_success_slo, args.deploy_success_slo)

    payload = {
        "generated_at": generated_at,
        "repo": args.repo,
        "window_days": args.window_days,
        "slo_targets": {
            "smoke_success_slo": args.smoke_success_slo,
            "deploy_success_slo": args.deploy_success_slo,
        },
        "signals": {
            "smoke": smoke,
            "deploy": deploy,
        },
        "alerts": [
            {"level": alert.level, "source": alert.source, "message": alert.message}
            for alert in alerts
        ],
    }

    output_json = Path(args.output_json).expanduser().resolve()
    output_md = Path(args.output_md).expanduser().resolve()
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(
        _build_markdown(
            generated_at=generated_at,
            repo=args.repo,
            window_days=args.window_days,
            smoke=smoke,
            deploy=deploy,
            alerts=alerts,
        ),
        encoding="utf-8",
    )
    print(f"Wrote JSON: {output_json}")
    print(f"Wrote Markdown: {output_md}")

    if args.fail_on_alert_level != "none":
        threshold = _level_rank(args.fail_on_alert_level)
        if any(_level_rank(alert.level) >= threshold for alert in alerts):
            print(f"Failing due to alerts at or above '{args.fail_on_alert_level}'.")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

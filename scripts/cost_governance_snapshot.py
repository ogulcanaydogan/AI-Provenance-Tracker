#!/usr/bin/env python3
"""Generate a cost governance snapshot for GitHub Actions and optional Vercel usage."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


DEFAULT_POLICY: dict[str, Any] = {
    "policy_version": "2026-03-03.hybrid-v1",
    "monthly_cap_usd": 50.0,
    "warn_threshold_pct": 80.0,
    "block_threshold_pct": 95.0,
    "override_label": "cost-override-approved",
    "non_essential_workflows": [
        "Public Provenance Benchmark",
        "Publish Service Images",
        "Deploy Spark Runtime",
    ],
    "cost_model": {
        "github_actions_usd_per_minute": 0.008,
        "vercel_usd_per_deployment": 0.02,
    },
}


@dataclass(slots=True)
class Alert:
    level: str
    source: str
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build governance snapshot for CI/CD spend signals.")
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", ""), help="GitHub repo: owner/name")
    parser.add_argument("--window-days", type=int, default=30, help="Rolling window in days")
    parser.add_argument(
        "--gh-token",
        default=os.getenv("GH_TOKEN", os.getenv("GITHUB_TOKEN", "")),
        help="GitHub token (defaults to GH_TOKEN or GITHUB_TOKEN)",
    )
    parser.add_argument(
        "--vercel-token",
        default=os.getenv("VERCEL_TOKEN", ""),
        help="Optional Vercel token for deployment usage proxy",
    )
    parser.add_argument(
        "--vercel-project-id",
        default=os.getenv("VERCEL_PROJECT_ID", ""),
        help="Optional Vercel project ID",
    )
    parser.add_argument(
        "--vercel-team-id",
        default=os.getenv("VERCEL_TEAM_ID", ""),
        help="Optional Vercel team ID",
    )
    parser.add_argument("--warn-actions-minutes", type=float, default=1200.0)
    parser.add_argument("--critical-actions-minutes", type=float, default=2400.0)
    parser.add_argument("--warn-failure-rate", type=float, default=0.20)
    parser.add_argument("--warn-vercel-deployments", type=int, default=120)
    parser.add_argument("--critical-vercel-deployments", type=int, default=200)
    parser.add_argument(
        "--policy-file",
        default="config/cost_policy.yaml",
        help="Cost policy file (YAML/JSON-compatible).",
    )
    parser.add_argument(
        "--workflow-name",
        default=os.getenv("GITHUB_WORKFLOW", ""),
        help="Current workflow name used for non-essential workflow gating.",
    )
    parser.add_argument(
        "--output-json",
        default="ops/reports/cost_governance_snapshot.json",
        help="Snapshot JSON output path",
    )
    parser.add_argument(
        "--output-md",
        default="ops/reports/cost_governance_snapshot.md",
        help="Human-readable markdown output path",
    )
    parser.add_argument(
        "--fail-on-alert-level",
        choices=("none", "warn", "critical"),
        default="none",
        help="Exit non-zero when alerts at or above this level exist",
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


def _request_json(url: str, token: str, accept: str = "application/vnd.github+json") -> dict[str, Any]:
    headers = {"Accept": accept, "User-Agent": "ai-provenance-cost-governance/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=30) as response:
        text = response.read().decode("utf-8")
    return json.loads(text) if text else {}


def _fetch_github_runs(owner: str, repo: str, token: str, since: datetime) -> list[dict[str, Any]]:
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

        stop_paging = False
        for run in batch:
            created_raw = run.get("created_at")
            if not isinstance(created_raw, str):
                continue
            created_at = _iso_to_dt(created_raw)
            if created_at < since:
                stop_paging = True
                continue
            runs.append(run)

        if stop_paging or len(batch) < per_page:
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
    seconds = (completed - started).total_seconds()
    return max(seconds, 0.0) / 60.0


def _summarize_github(runs: list[dict[str, Any]]) -> dict[str, Any]:
    totals: dict[str, Any] = {
        "total_runs": len(runs),
        "success_runs": 0,
        "failed_runs": 0,
        "cancelled_runs": 0,
        "other_runs": 0,
        "failure_rate": 0.0,
        "total_runtime_minutes": 0.0,
        "workflows": [],
    }
    by_workflow: dict[str, dict[str, Any]] = {}

    for run in runs:
        name = str(run.get("name") or "unknown")
        conclusion = str(run.get("conclusion") or "unknown")
        runtime = _duration_minutes(run)
        totals["total_runtime_minutes"] += runtime

        if conclusion == "success":
            totals["success_runs"] += 1
        elif conclusion in {"failure", "timed_out", "action_required"}:
            totals["failed_runs"] += 1
        elif conclusion in {"cancelled", "skipped"}:
            totals["cancelled_runs"] += 1
        else:
            totals["other_runs"] += 1

        entry = by_workflow.setdefault(
            name,
            {
                "workflow": name,
                "runs": 0,
                "failed_runs": 0,
                "runtime_minutes": 0.0,
            },
        )
        entry["runs"] += 1
        entry["runtime_minutes"] += runtime
        if conclusion in {"failure", "timed_out", "action_required"}:
            entry["failed_runs"] += 1

    total_runs = totals["total_runs"] or 1
    totals["failure_rate"] = totals["failed_runs"] / total_runs
    totals["total_runtime_minutes"] = round(float(totals["total_runtime_minutes"]), 2)

    rows = list(by_workflow.values())
    rows.sort(key=lambda item: float(item["runtime_minutes"]), reverse=True)
    for item in rows:
        runs_count = int(item["runs"]) or 1
        item["failure_rate"] = round(float(item["failed_runs"]) / runs_count, 4)
        item["runtime_minutes"] = round(float(item["runtime_minutes"]), 2)
    totals["workflows"] = rows[:12]
    totals["failure_rate"] = round(float(totals["failure_rate"]), 4)
    return totals


def _fetch_vercel_summary(
    token: str,
    project_id: str,
    team_id: str,
    since: datetime,
) -> dict[str, Any]:
    if not token or not project_id:
        return {
            "status": "unavailable",
            "reason": "missing_token_or_project",
            "total_deployments": 0,
            "failed_deployments": 0,
            "production_deployments": 0,
        }

    params = {
        "projectId": project_id,
        "limit": "100",
        "from": str(int(since.timestamp() * 1000)),
    }
    if team_id:
        params["teamId"] = team_id
    query = urllib.parse.urlencode(params)
    url = f"https://api.vercel.com/v6/deployments?{query}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "ai-provenance-cost-governance/1.0",
    }
    request = urllib.request.Request(url, headers=headers, method="GET")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        return {
            "status": "error",
            "reason": f"http_{exc.code}",
            "error": body[:300],
            "total_deployments": 0,
            "failed_deployments": 0,
            "production_deployments": 0,
        }
    except Exception as exc:  # pragma: no cover - IO guard
        return {
            "status": "error",
            "reason": "request_error",
            "error": str(exc),
            "total_deployments": 0,
            "failed_deployments": 0,
            "production_deployments": 0,
        }

    deployments = payload.get("deployments")
    if not isinstance(deployments, list):
        deployments = []

    failed = 0
    production = 0
    for dep in deployments:
        if not isinstance(dep, dict):
            continue
        state = str(dep.get("readyState") or "")
        target = str(dep.get("target") or "")
        if state and state.lower() not in {"ready", "succeeded"}:
            failed += 1
        if target == "production":
            production += 1

    return {
        "status": "ok",
        "reason": "",
        "total_deployments": len(deployments),
        "failed_deployments": failed,
        "production_deployments": production,
    }


def _coerce_yaml_scalar(raw: str) -> Any:
    value = raw.strip()
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none", "~"}:
        return None
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_key: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            if current_key is None:
                continue
            data.setdefault(current_key, [])
            if isinstance(data[current_key], list):
                data[current_key].append(_coerce_yaml_scalar(stripped[2:]))
            continue
        if ":" not in stripped:
            continue
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not raw_value:
            data[key] = []
            current_key = key
            continue
        data[key] = _coerce_yaml_scalar(raw_value)
        current_key = key
    return data


def _load_policy(path: Path) -> dict[str, Any]:
    policy: dict[str, Any] = json.loads(json.dumps(DEFAULT_POLICY))
    if not path.exists():
        policy["policy_source"] = "default"
        return policy

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        policy["policy_source"] = f"{path} (empty -> default)"
        return policy

    parsed: dict[str, Any]
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = _parse_simple_yaml(text)

    if not isinstance(parsed, dict):
        policy["policy_source"] = f"{path} (invalid -> default)"
        return policy

    for key in (
        "policy_version",
        "monthly_cap_usd",
        "warn_threshold_pct",
        "block_threshold_pct",
        "override_label",
        "non_essential_workflows",
    ):
        if key in parsed:
            policy[key] = parsed[key]

    if isinstance(parsed.get("cost_model"), dict):
        policy["cost_model"].update(parsed["cost_model"])

    policy["policy_source"] = str(path)
    return policy


def _evaluate_budget_status(
    github_summary: dict[str, Any],
    vercel_summary: dict[str, Any],
    policy: dict[str, Any],
    workflow_name: str,
) -> dict[str, Any]:
    gh_rate = float(policy.get("cost_model", {}).get("github_actions_usd_per_minute", 0.008))
    vercel_rate = float(policy.get("cost_model", {}).get("vercel_usd_per_deployment", 0.02))

    runtime_minutes = float(github_summary.get("total_runtime_minutes") or 0.0)
    deployments = int(vercel_summary.get("total_deployments") or 0) if vercel_summary.get("status") == "ok" else 0

    estimated = round((runtime_minutes * gh_rate) + (deployments * vercel_rate), 4)
    cap = float(policy.get("monthly_cap_usd") or 0.0)
    utilization_pct = round((estimated / cap) * 100.0, 2) if cap > 0 else 0.0

    warn_pct = float(policy.get("warn_threshold_pct") or 80.0)
    block_pct = float(policy.get("block_threshold_pct") or 95.0)
    if utilization_pct >= block_pct:
        status = "block"
    elif utilization_pct >= warn_pct:
        status = "warn"
    else:
        status = "ok"

    non_essential = {
        str(item).strip()
        for item in (policy.get("non_essential_workflows") or [])
        if str(item).strip()
    }
    is_non_essential_workflow = workflow_name.strip() in non_essential if workflow_name else False
    non_essential_allowed = not (status == "block" and is_non_essential_workflow)

    return {
        "status": status,
        "remaining_budget": round(max(cap - estimated, 0.0), 4),
        "estimated_spend_usd": estimated,
        "monthly_cap_usd": cap,
        "budget_utilization_pct": utilization_pct,
        "policy_version": str(policy.get("policy_version") or "unknown"),
        "workflow_name": workflow_name,
        "is_non_essential_workflow": is_non_essential_workflow,
        "non_essential_allowed": non_essential_allowed,
    }


def _level_rank(level: str) -> int:
    mapping = {"none": 0, "warn": 1, "critical": 2}
    return mapping.get(level, 0)


def _build_alerts(
    github_summary: dict[str, Any],
    vercel_summary: dict[str, Any],
    args: argparse.Namespace,
    budget_state: dict[str, Any],
) -> list[Alert]:
    alerts: list[Alert] = []

    minutes = float(github_summary.get("total_runtime_minutes") or 0.0)
    if minutes >= args.critical_actions_minutes:
        alerts.append(
            Alert(
                level="critical",
                source="github_actions",
                message=(
                    f"GitHub runtime minutes reached {minutes:.2f} "
                    f"(>= critical threshold {args.critical_actions_minutes:.2f})."
                ),
            )
        )
    elif minutes >= args.warn_actions_minutes:
        alerts.append(
            Alert(
                level="warn",
                source="github_actions",
                message=(
                    f"GitHub runtime minutes reached {minutes:.2f} "
                    f"(>= warning threshold {args.warn_actions_minutes:.2f})."
                ),
            )
        )

    failure_rate = float(github_summary.get("failure_rate") or 0.0)
    if failure_rate >= args.warn_failure_rate:
        alerts.append(
            Alert(
                level="warn",
                source="github_actions",
                message=(
                    f"GitHub workflow failure rate is {failure_rate:.2%} "
                    f"(>= warning threshold {args.warn_failure_rate:.2%})."
                ),
            )
        )

    if vercel_summary.get("status") == "ok":
        total_deployments = int(vercel_summary.get("total_deployments") or 0)
        if total_deployments >= args.critical_vercel_deployments:
            alerts.append(
                Alert(
                    level="critical",
                    source="vercel",
                    message=(
                        f"Vercel deployment volume is {total_deployments} in the window "
                        f"(>= critical threshold {args.critical_vercel_deployments})."
                    ),
                )
            )
        elif total_deployments >= args.warn_vercel_deployments:
            alerts.append(
                Alert(
                    level="warn",
                    source="vercel",
                    message=(
                        f"Vercel deployment volume is {total_deployments} in the window "
                        f"(>= warning threshold {args.warn_vercel_deployments})."
                    ),
                )
            )

    if budget_state["status"] == "warn":
        alerts.append(
            Alert(
                level="warn",
                source="cost_policy",
                message=(
                    f"Budget utilization is {budget_state['budget_utilization_pct']:.2f}% "
                    f"(warn threshold reached)."
                ),
            )
        )
    elif budget_state["status"] == "block":
        alerts.append(
            Alert(
                level="critical",
                source="cost_policy",
                message=(
                    f"Budget utilization is {budget_state['budget_utilization_pct']:.2f}% "
                    "(block threshold reached)."
                ),
            )
        )

    return alerts


def _to_json_alerts(alerts: list[Alert]) -> list[dict[str, str]]:
    return [{"level": alert.level, "source": alert.source, "message": alert.message} for alert in alerts]


def _build_markdown(
    repo: str,
    generated_at: str,
    window_days: int,
    github_summary: dict[str, Any],
    vercel_summary: dict[str, Any],
    budget_state: dict[str, Any],
    policy: dict[str, Any],
    alerts: list[Alert],
) -> str:
    lines = [
        "# Cost Governance Snapshot",
        "",
        f"- Repository: `{repo}`",
        f"- Generated: `{generated_at}`",
        f"- Window: `{window_days} days`",
        "",
        "## Cost Policy",
        "",
        f"- Policy version: `{budget_state['policy_version']}`",
        f"- Policy source: `{policy.get('policy_source', 'default')}`",
        f"- Monthly cap (USD): `{budget_state['monthly_cap_usd']}`",
        f"- Estimated spend (USD): `{budget_state['estimated_spend_usd']}`",
        f"- Remaining budget (USD): `{budget_state['remaining_budget']}`",
        f"- Utilization: `{budget_state['budget_utilization_pct']:.2f}%`",
        f"- Status: `{budget_state['status']}`",
        f"- Workflow under evaluation: `{budget_state['workflow_name'] or 'n/a'}`",
        f"- Non-essential workflow: `{budget_state['is_non_essential_workflow']}`",
        f"- Non-essential allowed: `{budget_state['non_essential_allowed']}`",
        "",
        "## GitHub Actions",
        "",
        f"- Total runs: `{github_summary['total_runs']}`",
        f"- Success runs: `{github_summary['success_runs']}`",
        f"- Failed runs: `{github_summary['failed_runs']}`",
        f"- Failure rate: `{github_summary['failure_rate']:.2%}`",
        f"- Runtime minutes (proxy): `{github_summary['total_runtime_minutes']}`",
        "",
        "| Workflow | Runs | Failed | Failure Rate | Runtime Minutes |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in github_summary.get("workflows", []):
        lines.append(
            f"| {row['workflow']} | {row['runs']} | {row['failed_runs']} | "
            f"{float(row['failure_rate']):.2%} | {row['runtime_minutes']} |"
        )

    lines.extend(["", "## Vercel (Deploy Volume Proxy)", ""])
    status = str(vercel_summary.get("status", "unavailable"))
    if status == "ok":
        lines.extend(
            [
                f"- Total deployments: `{vercel_summary['total_deployments']}`",
                f"- Failed/non-ready deployments: `{vercel_summary['failed_deployments']}`",
                f"- Production deployments: `{vercel_summary['production_deployments']}`",
            ]
        )
    else:
        lines.append(f"- Status: `{status}` ({vercel_summary.get('reason', 'unknown')})")
        if vercel_summary.get("error"):
            lines.append(f"- Error: `{vercel_summary['error']}`")

    lines.extend(["", "## Alerts", ""])
    if not alerts:
        lines.append("- None")
    else:
        for alert in alerts:
            lines.append(f"- [{alert.level.upper()}] {alert.source}: {alert.message}")

    lines.append("")
    return "\n".join(lines)


def run() -> int:
    args = parse_args()
    owner, repo = _parse_repo(args.repo)

    now = datetime.now(UTC)
    since = now - timedelta(days=max(args.window_days, 1))
    generated_at = now.isoformat()

    if not args.gh_token:
        raise RuntimeError("Missing GitHub token. Set --gh-token or GITHUB_TOKEN.")

    policy_path = Path(args.policy_file).expanduser().resolve()
    policy = _load_policy(policy_path)

    github_runs = _fetch_github_runs(owner, repo, args.gh_token, since)
    github_summary = _summarize_github(github_runs)
    vercel_summary = _fetch_vercel_summary(
        token=args.vercel_token,
        project_id=args.vercel_project_id,
        team_id=args.vercel_team_id,
        since=since,
    )

    budget_state = _evaluate_budget_status(
        github_summary=github_summary,
        vercel_summary=vercel_summary,
        policy=policy,
        workflow_name=args.workflow_name,
    )

    alerts = _build_alerts(github_summary, vercel_summary, args, budget_state)

    snapshot = {
        "generated_at": generated_at,
        "repo": args.repo,
        "window_days": args.window_days,
        "status": budget_state["status"],
        "remaining_budget": budget_state["remaining_budget"],
        "policy_version": budget_state["policy_version"],
        "policy": policy,
        "budget": budget_state,
        "github_actions": github_summary,
        "vercel": vercel_summary,
        "thresholds": {
            "warn_actions_minutes": args.warn_actions_minutes,
            "critical_actions_minutes": args.critical_actions_minutes,
            "warn_failure_rate": args.warn_failure_rate,
            "warn_vercel_deployments": args.warn_vercel_deployments,
            "critical_vercel_deployments": args.critical_vercel_deployments,
        },
        "alerts": _to_json_alerts(alerts),
    }

    output_json = Path(args.output_json).expanduser().resolve()
    output_md = Path(args.output_md).expanduser().resolve()
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    output_json.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(
        _build_markdown(
            repo=args.repo,
            generated_at=generated_at,
            window_days=args.window_days,
            github_summary=github_summary,
            vercel_summary=vercel_summary,
            budget_state=budget_state,
            policy=policy,
            alerts=alerts,
        ),
        encoding="utf-8",
    )

    print(f"Wrote JSON: {output_json}")
    print(f"Wrote Markdown: {output_md}")

    failure_level = args.fail_on_alert_level
    if failure_level != "none":
        threshold = _level_rank(failure_level)
        if any(_level_rank(alert.level) >= threshold for alert in alerts):
            print(f"Failing due to alerts at or above '{failure_level}'.")
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(run())

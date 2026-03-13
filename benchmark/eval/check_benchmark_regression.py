#!/usr/bin/env python3
"""Fail CI when benchmark metrics regress beyond allowed drop thresholds."""

from __future__ import annotations

import argparse
import json
import re
import shlex
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

WINDOWS_ABS_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
URL_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")

QUALITY_REQUIRED_DOMAIN_KEYS = ("code", "finance", "legal", "science")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check benchmark regression against a snapshot.")
    parser.add_argument(
        "--current",
        default="benchmark/results/ci/benchmark_results.json",
        help="Current benchmark results JSON path.",
    )
    parser.add_argument(
        "--baseline",
        default="benchmark/baselines/public_benchmark_snapshot.json",
        help="Baseline snapshot JSON path.",
    )
    parser.add_argument(
        "--report-json",
        default="benchmark/results/ci/regression_check.json",
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--report-md",
        default="benchmark/results/ci/regression_check.md",
        help="Output Markdown report path.",
    )
    parser.add_argument(
        "--targets-config",
        default="",
        help="Optional benchmark targets config path to load absolute quality limits.",
    )
    parser.add_argument(
        "--target-profile",
        default="",
        help="Optional target profile key (for example full_v3) used with --targets-config.",
    )
    parser.add_argument(
        "--previous",
        default="",
        help="Optional previous benchmark results JSON used for drift comparison.",
    )
    parser.add_argument(
        "--max-ece-drift",
        type=float,
        default=0.02,
        help="Maximum allowed positive drift delta for calibration_ece metrics.",
    )
    parser.add_argument(
        "--max-domain-fp-drift",
        type=float,
        default=0.05,
        help="Maximum allowed positive drift delta for false_positive_rate_by_domain metrics.",
    )
    parser.add_argument(
        "--max-generated-age-hours",
        type=float,
        default=0.0,
        help="Maximum allowed age for current benchmark generated_at. <=0 disables freshness check.",
    )
    parser.add_argument(
        "--require-quality-metrics",
        action="store_true",
        help="Require calibration_ece and domain FP metrics for ai_vs_human_detection task.",
    )
    parser.add_argument(
        "--forbid-absolute-paths",
        action="store_true",
        help="Fail if benchmark payload contains absolute file-system paths outside repository root.",
    )
    return parser.parse_args()


def _value_at_path(payload: dict[str, Any], path: str) -> float:
    node: Any = payload
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            raise KeyError(path)
        node = node[key]
    return float(node)


def _try_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_iso8601(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _collect_missing_quality_metrics(current_payload: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    tasks_node = current_payload.get("tasks", {})
    if not isinstance(tasks_node, dict):
        return [
            "tasks.ai_vs_human_detection.calibration_ece",
            "tasks.ai_vs_human_detection.false_positive_rate_by_domain",
        ]
    detection_node = tasks_node.get("ai_vs_human_detection", {})
    if not isinstance(detection_node, dict):
        return [
            "tasks.ai_vs_human_detection.calibration_ece",
            "tasks.ai_vs_human_detection.false_positive_rate_by_domain",
        ]

    ece_path = "tasks.ai_vs_human_detection.calibration_ece"
    if "calibration_ece" not in detection_node:
        missing.append(ece_path)
    else:
        ece = _try_float(detection_node.get("calibration_ece"))
        if ece is None:
            missing.append(ece_path)

    domain_node = detection_node.get("false_positive_rate_by_domain")
    if not isinstance(domain_node, dict):
        missing.append("tasks.ai_vs_human_detection.false_positive_rate_by_domain")
        return missing

    for domain in QUALITY_REQUIRED_DOMAIN_KEYS:
        path = f"tasks.ai_vs_human_detection.false_positive_rate_by_domain.{domain}"
        if domain not in domain_node:
            missing.append(path)
            continue
        if _try_float(domain_node.get(domain)) is None:
            missing.append(path)
    return missing


def _iter_strings(node: Any) -> list[str]:
    values: list[str] = []
    if isinstance(node, str):
        values.append(node)
        return values
    if isinstance(node, dict):
        for value in node.values():
            values.extend(_iter_strings(value))
        return values
    if isinstance(node, list):
        for item in node:
            values.extend(_iter_strings(item))
    return values


def _looks_like_url(value: str) -> bool:
    return bool(URL_SCHEME_RE.match(value.strip()))


def _is_absolute_path(value: str) -> bool:
    stripped = value.strip()
    return stripped.startswith("/") or bool(WINDOWS_ABS_PATH_RE.match(stripped))


def _extract_path_candidates(value: str) -> set[str]:
    candidates: set[str] = set()
    stripped = value.strip()
    if not stripped or _looks_like_url(stripped):
        return candidates

    def add_if_path(candidate: str) -> None:
        token = candidate.strip().strip("\"'`,;()[]{}")
        if not token or _looks_like_url(token):
            return
        if "=" in token and not token.startswith("/") and not WINDOWS_ABS_PATH_RE.match(token):
            # Support --flag=/abs/path patterns.
            token = token.split("=", 1)[1].strip().strip("\"'`,;()[]{}")
        if _is_absolute_path(token):
            candidates.add(token)

    add_if_path(stripped)
    if " " in stripped or "\t" in stripped:
        try:
            tokens = shlex.split(stripped)
        except ValueError:
            tokens = stripped.split()
        for token in tokens:
            add_if_path(token)
    return candidates


def _is_path_inside_repo(path_value: str, repo_root: Path) -> bool:
    if WINDOWS_ABS_PATH_RE.match(path_value):
        return False
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        return True
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(repo_root)
        return True
    except ValueError:
        pass

    # Allow CI absolute paths when they clearly map to an existing repo-relative path.
    parts = list(resolved.parts)
    repo_anchor_dirs = {
        ".github",
        "backend",
        "benchmark",
        "config",
        "deploy",
        "docs",
        "frontend",
        "scripts",
        "tests",
    }
    for idx, part in enumerate(parts):
        if part not in repo_anchor_dirs:
            continue
        candidate_rel = Path(*parts[idx:])
        if candidate_rel == Path("."):
            continue
        if (repo_root / candidate_rel).exists():
            return True

    return False


def _collect_invalid_absolute_paths(current_payload: dict[str, Any], repo_root: Path) -> list[str]:
    invalid: list[str] = []
    for raw in _iter_strings(current_payload):
        for candidate in _extract_path_candidates(raw):
            if not _is_path_inside_repo(candidate, repo_root):
                invalid.append(candidate)
    return sorted(set(invalid))


def _load_quality_limits(targets_config_path: Path, target_profile: str) -> list[dict[str, Any]]:
    if not target_profile or not targets_config_path.exists():
        return []
    try:
        payload = json.loads(targets_config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, dict):
        return []

    targets_node = payload.get("targets", payload)
    if not isinstance(targets_node, dict):
        return []
    profile_payload = targets_node.get(target_profile, {})
    if not isinstance(profile_payload, dict):
        return []
    quality_targets = profile_payload.get("quality_targets", {})
    if not isinstance(quality_targets, dict):
        return []

    limits: list[dict[str, Any]] = []
    for task_name, task_payload in quality_targets.items():
        if not isinstance(task_name, str) or not isinstance(task_payload, dict):
            continue
        calibration_ece_max = task_payload.get("calibration_ece_max")
        if calibration_ece_max is not None:
            try:
                limits.append(
                    {
                        "path": f"tasks.{task_name}.calibration_ece",
                        "limit": float(calibration_ece_max),
                        "constraint": "max",
                        "source": f"targets:{target_profile}",
                    }
                )
            except (TypeError, ValueError):
                pass

        domain_max = task_payload.get("false_positive_rate_by_domain_max", {})
        if isinstance(domain_max, dict):
            for domain, raw_limit in domain_max.items():
                if not isinstance(domain, str):
                    continue
                try:
                    limits.append(
                        {
                            "path": f"tasks.{task_name}.false_positive_rate_by_domain.{domain}",
                            "limit": float(raw_limit),
                            "constraint": "max",
                            "source": f"targets:{target_profile}",
                        }
                    )
                except (TypeError, ValueError):
                    continue
    return limits


def _drift_limit_for_path(path: str, *, max_ece_drift: float, max_domain_fp_drift: float) -> float | None:
    if path.endswith(".calibration_ece"):
        return max_ece_drift
    if ".false_positive_rate_by_domain." in path:
        return max_domain_fp_drift
    return None


def _build_drift_summary(
    checks: list[dict[str, Any]],
    previous_payload: dict[str, Any] | None,
    *,
    max_ece_drift: float,
    max_domain_fp_drift: float,
) -> tuple[list[dict[str, Any]], int]:
    summary: list[dict[str, Any]] = []
    drift_failures = 0
    for check in checks:
        if check.get("constraint") != "max":
            continue
        path = str(check.get("path", ""))
        drift_limit = _drift_limit_for_path(
            path,
            max_ece_drift=max_ece_drift,
            max_domain_fp_drift=max_domain_fp_drift,
        )
        if drift_limit is None:
            continue

        current_value = check.get("current")
        entry: dict[str, Any] = {
            "path": path,
            "current": current_value,
            "previous": None,
            "delta": None,
            "limit": drift_limit,
            "status": "no_baseline",
        }
        if previous_payload is None:
            summary.append(entry)
            continue
        if current_value is None:
            entry["status"] = "missing_current_metric"
            summary.append(entry)
            continue

        try:
            previous_value = _value_at_path(previous_payload, path)
        except KeyError:
            entry["status"] = "no_previous_metric"
            summary.append(entry)
            continue

        delta = float(current_value) - previous_value
        status = "pass" if delta <= drift_limit else "fail"
        if status == "fail":
            drift_failures += 1
        entry.update(
            {
                "previous": previous_value,
                "delta": delta,
                "status": status,
            }
        )
        summary.append(entry)
    return summary, drift_failures


def _fail_reasons_from_report(
    checks: list[dict[str, Any]], drift_summary: list[dict[str, Any]]
) -> list[str]:
    reasons: list[str] = []
    for check in checks:
        if check.get("passed", False):
            continue
        path = str(check.get("path", ""))
        constraint = str(check.get("constraint", ""))
        if constraint == "max_age_hours" and "stale_current_results" not in reasons:
            reasons.append("stale_current_results")
        if constraint == "present" and "missing_quality_metrics" not in reasons:
            reasons.append("missing_quality_metrics")
        if constraint == "repo_path" and "invalid_path_reference" not in reasons:
            reasons.append("invalid_path_reference")
        if (
            constraint == "max"
            and path.endswith(".calibration_ece")
            and "ece_limit_breach" not in reasons
        ):
            reasons.append("ece_limit_breach")
        elif (
            constraint == "max"
            and ".false_positive_rate_by_domain." in path
            and "domain_fp_breach" not in reasons
        ):
            reasons.append("domain_fp_breach")
    if any(item.get("status") == "fail" for item in drift_summary):
        reasons.append("drift_spike")
    return reasons


def _build_markdown(report: dict[str, Any]) -> str:
    rows = report["checks"]
    drift_rows = report.get("drift_summary", [])
    lines = [
        "# Benchmark Regression Check",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Baseline snapshot: `{report['baseline_snapshot']}`",
        f"- Current benchmark: `{report['current_benchmark']}`",
        f"- Previous benchmark: `{report.get('previous_benchmark') or 'n/a'}`",
        f"- Targets config: `{report.get('targets_config') or 'n/a'}`",
        f"- Target profile: `{report.get('target_profile') or 'n/a'}`",
        f"- Fail reasons: `{', '.join(report.get('fail_reasons', [])) or 'none'}`",
        f"- Status: `{'pass' if report['passed'] else 'fail'}`",
        "",
        "| Metric | Constraint | Current | Limit | Delta | Source | Result |",
        "| --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for item in rows:
        constraint_kind = item.get("constraint")
        constraint = "n/a"
        current_text = "n/a"
        limit_text = "n/a"
        delta_text = "n/a"
        if constraint_kind == "min":
            constraint = ">="
            if item["current"] is not None:
                current_text = f"{item['current']:.4f}"
            if item["limit"] is not None:
                limit_text = f"{item['limit']:.4f}"
            if item["current"] is not None and item["limit"] is not None:
                delta_text = f"{item['current'] - item['limit']:+.4f}"
        elif constraint_kind == "max":
            constraint = "<="
            if item["current"] is not None:
                current_text = f"{item['current']:.4f}"
            if item["limit"] is not None:
                limit_text = f"{item['limit']:.4f}"
            if item["current"] is not None and item["limit"] is not None:
                delta_text = f"{item['current'] - item['limit']:+.4f}"
        elif constraint_kind == "max_age_hours":
            constraint = "<= age(h)"
            if item["current"] is not None:
                current_text = f"{float(item['current']):.2f}"
            if item["limit"] is not None:
                limit_text = f"{float(item['limit']):.2f}"
            if item["current"] is not None and item["limit"] is not None:
                delta_text = f"{float(item['current']) - float(item['limit']):+.2f}"
        elif constraint_kind == "present":
            constraint = "present"
            current_text = "yes" if item.get("current") else "no"
            limit_text = "required"
        elif constraint_kind == "repo_path":
            constraint = "within_repo"
            current_text = str(item.get("current", "n/a"))
            limit_text = str(item.get("limit", "n/a"))

        lines.append(
            "| {metric} | {constraint} | {current} | {limit} | {delta} | {source} | {result} |".format(
                metric=item["path"],
                constraint=constraint,
                current=current_text,
                limit=limit_text,
                delta=delta_text,
                source=item.get("source", "baseline"),
                result="PASS" if item["passed"] else "FAIL",
            )
        )
    if drift_rows:
        lines.extend(
            [
                "",
                "## Drift Summary",
                "",
                "| Metric | Current | Previous | Delta | Limit | Status |",
                "| --- | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for item in drift_rows:
            current_value = item.get("current")
            previous_value = item.get("previous")
            delta_value = item.get("delta")
            limit_value = item.get("limit")
            lines.append(
                "| {metric} | {current} | {previous} | {delta} | {limit} | {status} |".format(
                    metric=item.get("path", "n/a"),
                    current="n/a" if current_value is None else f"{float(current_value):.4f}",
                    previous="n/a" if previous_value is None else f"{float(previous_value):.4f}",
                    delta="n/a" if delta_value is None else f"{float(delta_value):+.4f}",
                    limit="n/a" if limit_value is None else f"{float(limit_value):.4f}",
                    status=str(item.get("status", "unknown")).upper(),
                )
            )
    lines.append("")
    return "\n".join(lines)


def run() -> int:
    args = parse_args()
    current_path = Path(args.current).expanduser().resolve()
    baseline_path = Path(args.baseline).expanduser().resolve()
    report_json_path = Path(args.report_json).expanduser().resolve()
    report_md_path = Path(args.report_md).expanduser().resolve()
    targets_config_path = Path(args.targets_config).expanduser().resolve() if args.targets_config else None
    previous_path = Path(args.previous).expanduser().resolve() if args.previous else None
    repo_root = Path.cwd().resolve()

    current_payload = json.loads(current_path.read_text(encoding="utf-8"))
    baseline_payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    previous_payload: dict[str, Any] | None = None
    if previous_path is not None and previous_path.exists():
        previous_payload = json.loads(previous_path.read_text(encoding="utf-8"))

    checks: list[dict[str, Any]] = []
    failures = 0
    for metric in baseline_payload.get("metrics", []):
        path = str(metric["path"])
        baseline_value = float(metric["baseline"])
        max_drop = float(metric["max_drop"])
        current_value = _value_at_path(current_payload, path)
        min_allowed = baseline_value - max_drop
        passed = current_value >= min_allowed
        if not passed:
            failures += 1
        checks.append(
            {
                "path": path,
                "constraint": "min",
                "limit": min_allowed,
                "source": "baseline_snapshot",
                "baseline": baseline_value,
                "current": current_value,
                "max_drop": max_drop,
                "min_allowed": min_allowed,
                "delta": current_value - baseline_value,
                "passed": passed,
            }
        )

    if targets_config_path is not None and args.target_profile:
        quality_limits = _load_quality_limits(targets_config_path, str(args.target_profile))
        for item in quality_limits:
            path = str(item["path"])
            limit = float(item["limit"])
            try:
                current_value = _value_at_path(current_payload, path)
            except KeyError:
                current_value = None
            passed = current_value is not None and current_value <= limit
            if not passed:
                failures += 1
            checks.append(
                {
                    "path": path,
                    "constraint": "max",
                    "limit": limit,
                    "source": str(item.get("source", "targets")),
                    "baseline": None,
                    "current": current_value,
                    "max_drop": None,
                    "min_allowed": None,
                    "delta": (current_value - limit) if current_value is not None else None,
                    "passed": passed,
                }
            )

    if args.max_generated_age_hours > 0:
        generated_at_raw = str(current_payload.get("generated_at", "")).strip()
        generated_at = _parse_iso8601(generated_at_raw) if generated_at_raw else None
        age_hours: float | None = None
        freshness_passed = False
        if generated_at is not None:
            age_hours = (datetime.now(UTC) - generated_at).total_seconds() / 3600.0
            freshness_passed = age_hours <= float(args.max_generated_age_hours)
        checks.append(
            {
                "path": "generated_at",
                "constraint": "max_age_hours",
                "limit": float(args.max_generated_age_hours),
                "source": "freshness_guard",
                "baseline": None,
                "current": age_hours,
                "max_drop": None,
                "min_allowed": None,
                "delta": (age_hours - float(args.max_generated_age_hours)) if age_hours is not None else None,
                "passed": freshness_passed,
            }
        )
        if not freshness_passed:
            failures += 1

    if args.require_quality_metrics:
        missing_metrics = _collect_missing_quality_metrics(current_payload)
        for metric_path in missing_metrics:
            checks.append(
                {
                    "path": metric_path,
                    "constraint": "present",
                    "limit": "required",
                    "source": "quality_required",
                    "baseline": None,
                    "current": False,
                    "max_drop": None,
                    "min_allowed": None,
                    "delta": None,
                    "passed": False,
                }
            )
        failures += len(missing_metrics)

    if args.forbid_absolute_paths:
        invalid_paths = _collect_invalid_absolute_paths(current_payload, repo_root=repo_root)
        for invalid_path in invalid_paths:
            checks.append(
                {
                    "path": "run_metadata.path_reference",
                    "constraint": "repo_path",
                    "limit": str(repo_root),
                    "source": "path_guard",
                    "baseline": None,
                    "current": invalid_path,
                    "max_drop": None,
                    "min_allowed": None,
                    "delta": None,
                    "passed": False,
                }
            )
        failures += len(invalid_paths)

    drift_summary, drift_failures = _build_drift_summary(
        checks,
        previous_payload,
        max_ece_drift=float(args.max_ece_drift),
        max_domain_fp_drift=float(args.max_domain_fp_drift),
    )
    failures += drift_failures
    fail_reasons = _fail_reasons_from_report(checks, drift_summary)

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "baseline_snapshot": str(baseline_path),
        "current_benchmark": str(current_path),
        "previous_benchmark": str(previous_path) if previous_path is not None and previous_path.exists() else "",
        "targets_config": str(targets_config_path) if targets_config_path is not None else "",
        "target_profile": str(args.target_profile or ""),
        "strict_config": {
            "max_generated_age_hours": float(args.max_generated_age_hours),
            "require_quality_metrics": bool(args.require_quality_metrics),
            "forbid_absolute_paths": bool(args.forbid_absolute_paths),
        },
        "total_checks": len(checks),
        "failed_checks": failures,
        "passed": failures == 0,
        "fail_reasons": fail_reasons,
        "drift_config": {
            "max_ece_drift": float(args.max_ece_drift),
            "max_domain_fp_drift": float(args.max_domain_fp_drift),
        },
        "drift_total_checks": len(drift_summary),
        "drift_failed_checks": drift_failures,
        "drift_summary": drift_summary,
        "checks": checks,
    }

    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    report_md_path.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md_path.write_text(_build_markdown(report), encoding="utf-8")

    print(f"Wrote regression JSON report: {report_json_path}")
    print(f"Wrote regression Markdown report: {report_md_path}")
    if failures:
        for item in checks:
            if item.get("passed", False):
                continue
            constraint_kind = item.get("constraint")
            if constraint_kind == "max":
                constraint = "<="
            elif constraint_kind == "min":
                constraint = ">="
            elif constraint_kind == "max_age_hours":
                constraint = "<= age(h)"
            elif constraint_kind == "present":
                constraint = "present"
            elif constraint_kind == "repo_path":
                constraint = "within_repo"
            else:
                constraint = str(constraint_kind or "n/a")
            current_value = item.get("current")
            limit_value = item.get("limit")
            if isinstance(current_value, bool):
                current_text = "yes" if current_value else "no"
            elif isinstance(current_value, (int, float)):
                current_text = f"{float(current_value):.4f}"
            elif current_value is None:
                current_text = "n/a"
            else:
                current_text = str(current_value)
            if isinstance(limit_value, bool):
                limit_text = "yes" if limit_value else "no"
            elif isinstance(limit_value, (int, float)):
                limit_text = f"{float(limit_value):.4f}"
            elif limit_value is None:
                limit_text = "n/a"
            else:
                limit_text = str(limit_value)
            print(
                "FAILED_METRIC "
                f"path={item.get('path')} "
                f"constraint={constraint} "
                f"current={current_text} "
                f"limit={limit_text} "
                f"source={item.get('source', 'unknown')}"
            )
        for item in drift_summary:
            if item.get("status") != "fail":
                continue
            current_value = item.get("current")
            previous_value = item.get("previous")
            delta_value = item.get("delta")
            limit_value = item.get("limit")
            print(
                "FAILED_DRIFT "
                f"path={item.get('path')} "
                f"current={'n/a' if current_value is None else f'{float(current_value):.4f}'} "
                f"previous={'n/a' if previous_value is None else f'{float(previous_value):.4f}'} "
                f"delta={'n/a' if delta_value is None else f'{float(delta_value):+.4f}'} "
                f"limit={'n/a' if limit_value is None else f'{float(limit_value):.4f}'}"
            )
        print(f"Regression check failed: {failures} metric(s) below allowed threshold.")
        return 1
    print("Regression check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

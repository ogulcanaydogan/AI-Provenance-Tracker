#!/usr/bin/env python3
"""Fail CI when benchmark metrics regress beyond allowed drop thresholds."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


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
    return parser.parse_args()


def _value_at_path(payload: dict[str, Any], path: str) -> float:
    node: Any = payload
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            raise KeyError(path)
        node = node[key]
    return float(node)


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


def _build_markdown(report: dict[str, Any]) -> str:
    rows = report["checks"]
    lines = [
        "# Benchmark Regression Check",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Baseline snapshot: `{report['baseline_snapshot']}`",
        f"- Current benchmark: `{report['current_benchmark']}`",
        f"- Targets config: `{report.get('targets_config') or 'n/a'}`",
        f"- Target profile: `{report.get('target_profile') or 'n/a'}`",
        f"- Status: `{'pass' if report['passed'] else 'fail'}`",
        "",
        "| Metric | Constraint | Current | Limit | Delta | Source | Result |",
        "| --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for item in rows:
        constraint = ">=" if item["constraint"] == "min" else "<="
        delta = (
            item["current"] - item["limit"]
            if item["current"] is not None and item["limit"] is not None
            else 0.0
        )
        current_text = f"{item['current']:.4f}" if item["current"] is not None else "n/a"
        limit_text = f"{item['limit']:.4f}" if item["limit"] is not None else "n/a"
        lines.append(
            "| {metric} | {constraint} | {current} | {limit} | {delta:+.4f} | {source} | {result} |".format(
                metric=item["path"],
                constraint=constraint,
                current=current_text,
                limit=limit_text,
                delta=delta,
                source=item.get("source", "baseline"),
                result="PASS" if item["passed"] else "FAIL",
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

    current_payload = json.loads(current_path.read_text(encoding="utf-8"))
    baseline_payload = json.loads(baseline_path.read_text(encoding="utf-8"))

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

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "baseline_snapshot": str(baseline_path),
        "current_benchmark": str(current_path),
        "targets_config": str(targets_config_path) if targets_config_path is not None else "",
        "target_profile": str(args.target_profile or ""),
        "total_checks": len(checks),
        "failed_checks": failures,
        "passed": failures == 0,
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
            constraint = "<=" if item.get("constraint") == "max" else ">="
            current_value = item.get("current")
            limit_value = item.get("limit")
            current_text = "n/a" if current_value is None else f"{float(current_value):.4f}"
            limit_text = "n/a" if limit_value is None else f"{float(limit_value):.4f}"
            print(
                "FAILED_METRIC "
                f"path={item.get('path')} "
                f"constraint={constraint} "
                f"current={current_text} "
                f"limit={limit_text} "
                f"source={item.get('source', 'unknown')}"
            )
        print(f"Regression check failed: {failures} metric(s) below allowed threshold.")
        return 1
    print("Regression check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

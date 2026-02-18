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
    return parser.parse_args()


def _value_at_path(payload: dict[str, Any], path: str) -> float:
    node: Any = payload
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            raise KeyError(path)
        node = node[key]
    return float(node)


def _build_markdown(report: dict[str, Any]) -> str:
    rows = report["checks"]
    lines = [
        "# Benchmark Regression Check",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Baseline snapshot: `{report['baseline_snapshot']}`",
        f"- Current benchmark: `{report['current_benchmark']}`",
        f"- Status: `{'pass' if report['passed'] else 'fail'}`",
        "",
        "| Metric | Baseline | Current | Min Allowed | Delta | Result |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in rows:
        lines.append(
            "| {metric} | {baseline:.4f} | {current:.4f} | {min_allowed:.4f} | {delta:+.4f} | {result} |".format(
                metric=item["path"],
                baseline=item["baseline"],
                current=item["current"],
                min_allowed=item["min_allowed"],
                delta=item["delta"],
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
                "baseline": baseline_value,
                "current": current_value,
                "max_drop": max_drop,
                "min_allowed": min_allowed,
                "delta": current_value - baseline_value,
                "passed": passed,
            }
        )

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "baseline_snapshot": str(baseline_path),
        "current_benchmark": str(current_path),
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
        print(f"Regression check failed: {failures} metric(s) below allowed threshold.")
        return 1
    print("Regression check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

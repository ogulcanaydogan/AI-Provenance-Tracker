#!/usr/bin/env python3
"""Quality gate for text calibration outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate text calibration quality thresholds.")
    parser.add_argument(
        "--report",
        default="backend/evidence/calibration/text/latest_text_calibration.json",
        help="Calibration report JSON produced by evaluate_detection_calibration.py",
    )
    parser.add_argument("--max-fp-rate", type=float, default=0.08)
    parser.add_argument("--max-ece", type=float, default=0.08)
    parser.add_argument("--min-sample-count", type=int, default=100)
    parser.add_argument("--max-uncertainty-margin", type=float, default=0.18)
    parser.add_argument(
        "--output-json", default="backend/evidence/calibration/text/quality_gate.json"
    )
    parser.add_argument("--output-md", default="backend/evidence/calibration/text/quality_gate.md")
    return parser.parse_args()


def _failures(payload: dict[str, Any], args: argparse.Namespace) -> list[str]:
    failures: list[str] = []

    sample_count = int(payload.get("sample_count", 0) or 0)
    if sample_count < int(args.min_sample_count):
        failures.append(f"sample_count {sample_count} < minimum {int(args.min_sample_count)}")

    best_metrics = (
        payload.get("best_metrics", {}) if isinstance(payload.get("best_metrics"), dict) else {}
    )
    fp_rate = float(best_metrics.get("fp_rate", 1.0) or 1.0)
    if fp_rate > float(args.max_fp_rate):
        failures.append(f"fp_rate {fp_rate:.4f} > max_fp_rate {float(args.max_fp_rate):.4f}")

    ece = float(payload.get("ece", 1.0) or 1.0)
    if ece > float(args.max_ece):
        failures.append(f"ece {ece:.4f} > max_ece {float(args.max_ece):.4f}")

    margin = float(payload.get("recommended_uncertainty_margin", 1.0) or 1.0)
    if margin > float(args.max_uncertainty_margin):
        failures.append(
            f"uncertainty_margin {margin:.4f} > max_uncertainty_margin {float(args.max_uncertainty_margin):.4f}"
        )

    return failures


def _markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Text Quality Gate",
        "",
        f"- Status: **{summary['status'].upper()}**",
        f"- Report: `{summary['report']}`",
        f"- Sample count: `{summary['sample_count']}`",
        f"- FP rate: `{summary['fp_rate']:.4f}`",
        f"- ECE: `{summary['ece']:.4f}`",
        f"- Uncertainty margin: `{summary['uncertainty_margin']:.4f}`",
        "",
    ]

    if summary["failures"]:
        lines.append("## Failures")
        lines.append("")
        for failure in summary["failures"]:
            lines.append(f"- {failure}")
    else:
        lines.append("All gate checks passed.")

    lines.append("")
    return "\n".join(lines)


def run() -> int:
    args = parse_args()

    report_path = Path(args.report).expanduser().resolve()
    if not report_path.exists():
        raise SystemExit(f"Report not found: {report_path}")

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Invalid report payload")

    best_metrics = (
        payload.get("best_metrics", {}) if isinstance(payload.get("best_metrics"), dict) else {}
    )
    summary = {
        "report": str(report_path),
        "status": "ok",
        "sample_count": int(payload.get("sample_count", 0) or 0),
        "fp_rate": float(best_metrics.get("fp_rate", 1.0) or 1.0),
        "ece": float(payload.get("ece", 1.0) or 1.0),
        "uncertainty_margin": float(payload.get("recommended_uncertainty_margin", 1.0) or 1.0),
        "failures": _failures(payload, args),
    }
    if summary["failures"]:
        summary["status"] = "fail"

    output_json = Path(args.output_json).expanduser().resolve()
    output_md = Path(args.output_md).expanduser().resolve()
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(_markdown(summary), encoding="utf-8")

    print(_markdown(summary))
    return 1 if summary["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(run())

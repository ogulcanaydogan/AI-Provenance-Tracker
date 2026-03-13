#!/usr/bin/env python3
"""Quality gate for text calibration outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROBLEM_DOMAINS = ("code", "finance", "legal", "science")
DOMAIN_ALIASES: dict[str, tuple[str, ...]] = {
    "code": ("code", "code-doc"),
    "finance": ("finance", "marketing"),
    "legal": ("legal", "academic"),
    "science": ("science", "academic"),
}


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
        "--max-domain-fp-rate",
        type=float,
        default=0.30,
        help="Maximum allowed false positive rate for risk domains.",
    )
    parser.add_argument(
        "--min-domain-sample-count",
        type=int,
        default=30,
        help="Minimum samples required before enforcing per-domain FP checks.",
    )
    parser.add_argument(
        "--output-json", default="backend/evidence/calibration/text/quality_gate.json"
    )
    parser.add_argument("--output-md", default="backend/evidence/calibration/text/quality_gate.md")
    return parser.parse_args()


def _to_float(value: Any, default: float) -> float:
    """Parse numeric values without treating 0.0 as missing."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _lookup_domain_metric(container: dict[str, Any], domain: str) -> Any:
    for candidate in DOMAIN_ALIASES.get(domain, (domain,)):
        if candidate in container:
            return container[candidate]
    return None


def _domain_checks(payload: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    fp_by_domain = (
        payload.get("false_positive_rate_by_domain", {})
        if isinstance(payload.get("false_positive_rate_by_domain"), dict)
        else {}
    )
    sample_by_domain = (
        payload.get("domain_sample_count_by_domain", {})
        if isinstance(payload.get("domain_sample_count_by_domain"), dict)
        else {}
    )
    human_sample_by_domain = (
        payload.get("domain_human_sample_count_by_domain", {})
        if isinstance(payload.get("domain_human_sample_count_by_domain"), dict)
        else {}
    )
    domain_profiles = (
        payload.get("domain_profiles", {}) if isinstance(payload.get("domain_profiles"), dict) else {}
    )

    checks: list[dict[str, Any]] = []
    for domain in PROBLEM_DOMAINS:
        raw_sample_count = _lookup_domain_metric(sample_by_domain, domain)
        sample_count = int(raw_sample_count) if raw_sample_count is not None else 0
        if sample_count == 0:
            profile_fallback = _lookup_domain_metric(domain_profiles, domain)
            if isinstance(profile_fallback, dict):
                sample_count = int(profile_fallback.get("sample_count", 0) or 0)

        raw_human_count = _lookup_domain_metric(human_sample_by_domain, domain)
        human_sample_count = int(raw_human_count) if raw_human_count is not None else None

        raw_fp_rate = _lookup_domain_metric(fp_by_domain, domain)
        fp_rate = _to_float(raw_fp_rate, -1.0) if raw_fp_rate is not None else None
        if fp_rate is None or fp_rate < 0:
            profile_fallback = _lookup_domain_metric(domain_profiles, domain)
            if isinstance(profile_fallback, dict):
                best_metrics = (
                    profile_fallback.get("best_metrics", {})
                    if isinstance(profile_fallback.get("best_metrics"), dict)
                    else {}
                )
                fallback_rate = best_metrics.get("fp_rate")
                fp_rate = _to_float(fallback_rate, -1.0) if fallback_rate is not None else None
                if fp_rate is not None and fp_rate < 0:
                    fp_rate = None

        result = {
            "domain": domain,
            "sample_count": sample_count,
            "human_sample_count": human_sample_count,
            "fp_rate": fp_rate,
            "max_allowed_fp_rate": float(args.max_domain_fp_rate),
            "status": "pass",
            "reason": "",
        }

        if sample_count < int(args.min_domain_sample_count):
            result["status"] = "skipped"
            result["reason"] = (
                f"sample_count {sample_count} < minimum {int(args.min_domain_sample_count)}"
            )
        elif fp_rate is None:
            result["status"] = "skipped"
            result["reason"] = "false_positive_rate_by_domain value missing in report"
        elif fp_rate > float(args.max_domain_fp_rate):
            result["status"] = "fail"
            result["reason"] = (
                f"fp_rate {fp_rate:.4f} > max_domain_fp_rate {float(args.max_domain_fp_rate):.4f}"
            )

        checks.append(result)
    return checks


def _failures(payload: dict[str, Any], args: argparse.Namespace, domain_checks: list[dict[str, Any]]) -> list[str]:
    failures: list[str] = []

    sample_count = int(payload.get("sample_count", 0) or 0)
    if sample_count < int(args.min_sample_count):
        failures.append(f"sample_count {sample_count} < minimum {int(args.min_sample_count)}")

    best_metrics = (
        payload.get("best_metrics", {}) if isinstance(payload.get("best_metrics"), dict) else {}
    )
    fp_rate = _to_float(best_metrics.get("fp_rate"), 1.0)
    if fp_rate > float(args.max_fp_rate):
        failures.append(f"fp_rate {fp_rate:.4f} > max_fp_rate {float(args.max_fp_rate):.4f}")

    ece = _to_float(payload.get("ece"), 1.0)
    if ece > float(args.max_ece):
        failures.append(f"ece {ece:.4f} > max_ece {float(args.max_ece):.4f}")

    margin = _to_float(payload.get("recommended_uncertainty_margin"), 1.0)
    if margin > float(args.max_uncertainty_margin):
        failures.append(
            f"uncertainty_margin {margin:.4f} > max_uncertainty_margin {float(args.max_uncertainty_margin):.4f}"
        )

    for item in domain_checks:
        if item["status"] == "fail":
            failures.append(f"domain[{item['domain']}] {item['reason']}")

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
        f"- Max domain FP rate: `{summary['max_domain_fp_rate']:.4f}`",
        f"- Min domain sample count: `{summary['min_domain_sample_count']}`",
        "",
        "## Domain Gate",
        "",
        "| Domain | Status | Samples | Human Samples | FP Rate | Max Allowed | Reason |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
        "",
    ]
    for item in summary["domain_checks"]:
        human_sample = item["human_sample_count"] if item["human_sample_count"] is not None else "-"
        fp_rate = f"{item['fp_rate']:.4f}" if isinstance(item["fp_rate"], float) else "-"
        reason = item["reason"] or "-"
        lines.append(
            f"| {item['domain']} | {item['status']} | {item['sample_count']} | {human_sample} | "
            f"{fp_rate} | {item['max_allowed_fp_rate']:.4f} | {reason} |"
        )

    lines.append("")

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
    domain_checks = _domain_checks(payload, args)
    summary = {
        "report": str(report_path),
        "status": "ok",
        "sample_count": int(payload.get("sample_count", 0) or 0),
        "fp_rate": _to_float(best_metrics.get("fp_rate"), 1.0),
        "ece": _to_float(payload.get("ece"), 1.0),
        "uncertainty_margin": _to_float(payload.get("recommended_uncertainty_margin"), 1.0),
        "max_domain_fp_rate": float(args.max_domain_fp_rate),
        "min_domain_sample_count": int(args.min_domain_sample_count),
        "domain_checks": domain_checks,
        "failures": _failures(payload, args, domain_checks),
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

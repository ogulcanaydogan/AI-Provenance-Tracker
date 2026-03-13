#!/usr/bin/env python3
"""Build a public parity report from latest benchmark results and leaderboard."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a public parity report.")
    parser.add_argument(
        "--benchmark-results",
        default="benchmark/results/latest/benchmark_results.json",
        help="Path to benchmark results JSON.",
    )
    parser.add_argument(
        "--leaderboard",
        default="benchmark/leaderboard/leaderboard.json",
        help="Path to leaderboard JSON.",
    )
    parser.add_argument(
        "--output-json",
        default="benchmark/results/latest/public_parity_report.json",
        help="Output parity report JSON path.",
    )
    parser.add_argument(
        "--output-md",
        default="benchmark/results/latest/public_parity_report.md",
        help="Output parity report Markdown path.",
    )
    parser.add_argument(
        "--model-id",
        default="",
        help="Override model id. Defaults to benchmark run_metadata.model_id.",
    )
    return parser.parse_args()


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _text_domain_fp_max(detection: dict[str, Any]) -> float:
    node = detection.get("false_positive_rate_by_domain")
    if not isinstance(node, dict):
        return 0.0
    focused_domains = ("code", "finance", "legal", "science")
    focused = [
        float(node[key])
        for key in focused_domains
        if isinstance(node.get(key), (int, float))
    ]
    if focused:
        return max(focused)
    values = [
        float(value) for value in node.values() if isinstance(value, (int, float))
    ]
    return max(values) if values else 0.0


def _compute_overall(tasks: dict[str, Any]) -> float:
    detection = tasks.get("ai_vs_human_detection", {})
    attribution = tasks.get("source_attribution", {})
    tamper = tasks.get("tamper_detection", {})
    audio = tasks.get("audio_ai_vs_human_detection", {})
    video = tasks.get("video_ai_vs_human_detection", {})
    detection_f1 = _as_float(detection.get("f1")) or 0.0
    roc_auc = _as_float(detection.get("roc_auc")) or 0.0
    attribution_accuracy = _as_float(attribution.get("accuracy")) or 0.0
    robustness = _as_float(tamper.get("robustness_score")) or 0.0
    audio_f1 = _as_float(audio.get("f1")) or 0.0
    video_f1 = _as_float(video.get("f1")) or 0.0
    return round(
        (0.34 * detection_f1)
        + (0.2 * roc_auc)
        + (0.18 * attribution_accuracy)
        + (0.16 * robustness)
        + (0.06 * audio_f1)
        + (0.06 * video_f1),
        4,
    )


def _extract_current_payload(results: dict[str, Any], model_id: str) -> dict[str, Any]:
    tasks = results.get("tasks", {})
    if not isinstance(tasks, dict):
        tasks = {}
    detection = tasks.get("ai_vs_human_detection", {})
    if not isinstance(detection, dict):
        detection = {}

    return {
        "model_id": model_id,
        "benchmark_profile": str(results.get("profile", "unknown")),
        "overall_score": _compute_overall(tasks),
        "text_calibration_ece": _as_float(detection.get("calibration_ece")),
        "text_domain_fp_max": _text_domain_fp_max(detection),
    }


def _find_current_entry(
    entries: list[dict[str, Any]], model_id: str
) -> dict[str, Any] | None:
    for entry in entries:
        if entry.get("model_id") == model_id:
            return entry
    return None


def _best_reference_entry(
    entries: list[dict[str, Any]], current_model_id: str
) -> dict[str, Any] | None:
    candidates = [
        entry for entry in entries if entry.get("model_id") != current_model_id
    ]
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: float(item.get("overall_score", 0.0)), reverse=True
    )
    return candidates[0]


def _delta(current: float | None, reference: float | None) -> float | None:
    if current is None or reference is None:
        return None
    return round(current - reference, 4)


def _label_for_delta(delta: float | None, lower_is_better: bool) -> str:
    if delta is None:
        return "insufficient_reference"
    if abs(delta) < 1e-9:
        return "tie"
    if lower_is_better:
        return "better" if delta < 0 else "worse"
    return "ahead" if delta > 0 else "behind"


def _to_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _build_markdown(report: dict[str, Any]) -> str:
    current = report["current_model"]
    reference = report.get("reference_model")
    deltas = report["deltas"]
    status = report["position_summary"]

    lines = [
        "# Public Parity Report",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Current model: `{current.get('model_id', 'n/a')}` (rank `{current.get('rank', 'n/a')}`)",
        (
            f"- Reference model: `{reference.get('model_id')}` (rank `{reference.get('rank')}`)"
            if isinstance(reference, dict)
            else "- Reference model: `n/a`"
        ),
        "",
        "| Metric | Current | Reference | Delta | Status |",
        "| --- | ---: | ---: | ---: | --- |",
        "| Overall Score | {cur} | {ref} | {delta} | {status} |".format(
            cur=current.get("overall_score", "n/a"),
            ref=(reference or {}).get("overall_score", "n/a"),
            delta=deltas.get("overall_score", "n/a"),
            status=status.get("overall_score", "n/a"),
        ),
        "| Text Calibration ECE | {cur} | {ref} | {delta} | {status} |".format(
            cur=current.get("text_calibration_ece", "n/a"),
            ref=(reference or {}).get("text_calibration_ece", "n/a"),
            delta=deltas.get("text_calibration_ece", "n/a"),
            status=status.get("text_calibration_ece", "n/a"),
        ),
        "| Text Domain FP Max | {cur} | {ref} | {delta} | {status} |".format(
            cur=current.get("text_domain_fp_max", "n/a"),
            ref=(reference or {}).get("text_domain_fp_max", "n/a"),
            delta=deltas.get("text_domain_fp_max", "n/a"),
            status=status.get("text_domain_fp_max", "n/a"),
        ),
        "",
    ]
    return "\n".join(lines)


def run() -> int:
    args = parse_args()
    benchmark_results_path = Path(args.benchmark_results).expanduser().resolve()
    leaderboard_path = Path(args.leaderboard).expanduser().resolve()
    output_json_path = Path(args.output_json).expanduser().resolve()
    output_md_path = Path(args.output_md).expanduser().resolve()

    results = json.loads(benchmark_results_path.read_text(encoding="utf-8"))
    leaderboard = json.loads(leaderboard_path.read_text(encoding="utf-8"))
    entries = leaderboard.get("entries", [])
    if not isinstance(entries, list):
        entries = []

    model_id = (
        args.model_id
        or str(results.get("run_metadata", {}).get("model_id", "")).strip()
    )
    if not model_id:
        raise ValueError(
            "Could not resolve model_id. Provide --model-id or include run_metadata.model_id."
        )

    current = _extract_current_payload(results, model_id=model_id)
    current_entry = _find_current_entry(entries, model_id=model_id)
    if current_entry is not None:
        current["rank"] = (
            int(current_entry.get("rank", 0))
            if _to_number(current_entry.get("rank"))
            else None
        )
        current["overall_score"] = (
            _to_number(current_entry.get("overall_score")) or current["overall_score"]
        )
        if _to_number(current_entry.get("text_calibration_ece")) is not None:
            current["text_calibration_ece"] = _to_number(
                current_entry.get("text_calibration_ece")
            )
        if _to_number(current_entry.get("text_domain_fp_max")) is not None:
            current["text_domain_fp_max"] = _to_number(
                current_entry.get("text_domain_fp_max")
            )
        current["benchmark_profile"] = str(
            current_entry.get(
                "benchmark_profile", current.get("benchmark_profile", "unknown")
            )
        )
    else:
        all_scores = sorted(
            [
                float(entry.get("overall_score", 0.0))
                for entry in entries
                if isinstance(entry, dict)
            ],
            reverse=True,
        )
        rank = 1 + sum(
            1 for score in all_scores if score > float(current["overall_score"])
        )
        current["rank"] = rank

    reference = _best_reference_entry(entries, current_model_id=model_id)
    reference_payload: dict[str, Any] | None = None
    if reference is not None:
        reference_payload = {
            "model_id": reference.get("model_id"),
            "rank": int(reference.get("rank", 0))
            if _to_number(reference.get("rank"))
            else None,
            "overall_score": _to_number(reference.get("overall_score")),
            "text_calibration_ece": _to_number(reference.get("text_calibration_ece")),
            "text_domain_fp_max": _to_number(reference.get("text_domain_fp_max")),
            "benchmark_profile": reference.get("benchmark_profile", "legacy"),
            "updated_at": reference.get("updated_at"),
        }

    deltas = {
        "overall_score": _delta(
            _to_number(current.get("overall_score")),
            _to_number((reference_payload or {}).get("overall_score")),
        ),
        "text_calibration_ece": _delta(
            _to_number(current.get("text_calibration_ece")),
            _to_number((reference_payload or {}).get("text_calibration_ece")),
        ),
        "text_domain_fp_max": _delta(
            _to_number(current.get("text_domain_fp_max")),
            _to_number((reference_payload or {}).get("text_domain_fp_max")),
        ),
    }

    position_summary = {
        "overall_score": _label_for_delta(
            deltas["overall_score"], lower_is_better=False
        ),
        "text_calibration_ece": _label_for_delta(
            deltas["text_calibration_ece"], lower_is_better=True
        ),
        "text_domain_fp_max": _label_for_delta(
            deltas["text_domain_fp_max"], lower_is_better=True
        ),
    }

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "benchmark_results_path": str(benchmark_results_path),
        "leaderboard_path": str(leaderboard_path),
        "current_model": current,
        "reference_model": reference_payload,
        "deltas": deltas,
        "position_summary": position_summary,
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    output_md_path.write_text(_build_markdown(report), encoding="utf-8")
    print(f"Wrote parity report JSON: {output_json_path}")
    print(f"Wrote parity report Markdown: {output_md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

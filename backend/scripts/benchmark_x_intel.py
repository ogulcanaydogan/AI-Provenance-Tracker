"""Benchmark trust report outputs against optional labeled truth data."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark x trust report quality.")
    parser.add_argument("--report", required=True, help="Path to x_trust_report JSON")
    parser.add_argument(
        "--labels",
        default="",
        help="Optional labels JSON with bot_labels and claim_labels",
    )
    parser.add_argument("--bot-threshold", type=float, default=0.5, help="Bot decision threshold")
    parser.add_argument(
        "--output",
        default="x_trust_benchmark.json",
        help="Benchmark output JSON path",
    )
    return parser.parse_args()


def _safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def _bot_metrics(
    suspected_clusters: list[dict[str, Any]],
    labels: dict[str, Any],
    threshold: float,
) -> dict[str, Any]:
    predictions: dict[str, bool] = {}
    for cluster in suspected_clusters:
        for account in cluster.get("top_accounts", []):
            handle = account.get("handle", "").lower()
            if not handle:
                continue
            probability = float(account.get("bot_probability", 0.0))
            predictions[handle] = predictions.get(handle, False) or probability >= threshold

    truth = {item["handle"].lower(): bool(item["is_bot"]) for item in labels.get("bot_labels", [])}
    if not truth:
        return {
            "evaluated_accounts": 0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "note": "No bot_labels provided.",
        }

    tp = fp = fn = tn = 0
    for handle, is_bot in truth.items():
        pred = predictions.get(handle, False)
        if pred and is_bot:
            tp += 1
        elif pred and not is_bot:
            fp += 1
        elif (not pred) and is_bot:
            fn += 1
        else:
            tn += 1

    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall) if precision + recall else 0.0
    return {
        "evaluated_accounts": len(truth),
        "threshold": threshold,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def _claim_metrics(claims: list[dict[str, Any]], labels: dict[str, Any]) -> dict[str, Any]:
    expected = {
        item["topic_label"].lower(): item["recommended_response"]
        for item in labels.get("claim_labels", [])
    }
    if not expected:
        return {
            "evaluated_topics": 0,
            "accuracy": 0.0,
            "note": "No claim_labels provided.",
        }

    observed = {item["topic_label"].lower(): item["recommended_response"] for item in claims}
    correct = 0
    for topic, expected_response in expected.items():
        if observed.get(topic) == expected_response:
            correct += 1

    accuracy = _safe_div(correct, len(expected))
    return {
        "evaluated_topics": len(expected),
        "correct": correct,
        "accuracy": round(accuracy, 4),
    }


def main() -> int:
    args = parse_args()

    report_path = Path(args.report).expanduser().resolve()
    if not report_path.exists():
        print(f"Report file not found: {report_path}")
        return 1

    report = json.loads(report_path.read_text(encoding="utf-8"))
    labels: dict[str, Any] = {}
    if args.labels:
        labels_path = Path(args.labels).expanduser().resolve()
        if not labels_path.exists():
            print(f"Labels file not found: {labels_path}")
            return 1
        labels = json.loads(labels_path.read_text(encoding="utf-8"))

    suspected_clusters = report.get("bot_activity", {}).get("suspected_clusters", [])
    claims = report.get("claims_and_narratives", [])
    timeline = report.get("timeline", [])
    top_spike = max((len(item.get("spikes", [])) for item in timeline), default=0)

    output = {
        "generated_at": datetime.now(UTC).isoformat(),
        "report_summary": {
            "risk_level": report.get("executive_summary", {}).get("risk_level", "low"),
            "confidence_overall": report.get("confidence_overall", "low"),
            "timeline_days": len(timeline),
            "suspected_clusters": len(suspected_clusters),
            "narrative_topics": len(claims),
            "spike_days": sum(1 for item in timeline if item.get("spikes")),
            "top_spike_markers": top_spike,
        },
        "metrics": {
            "bot_detection": _bot_metrics(suspected_clusters, labels, args.bot_threshold),
            "claim_response": _claim_metrics(claims, labels),
        },
    }

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote benchmark JSON to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

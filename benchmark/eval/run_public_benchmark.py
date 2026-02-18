#!/usr/bin/env python3
"""Run the public provenance benchmark and produce leaderboard-ready artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run public benchmark baseline.")
    parser.add_argument(
        "--datasets-dir",
        default="benchmark/datasets",
        help="Directory containing benchmark JSONL datasets.",
    )
    parser.add_argument(
        "--output-dir",
        default="benchmark/results/latest",
        help="Directory to write benchmark result artifacts.",
    )
    parser.add_argument(
        "--leaderboard-output",
        default="benchmark/leaderboard/leaderboard.json",
        help="Leaderboard JSON output path.",
    )
    parser.add_argument(
        "--model-id",
        default="baseline-heuristic-v0.1",
        help="Model/system identifier for leaderboard entry.",
    )
    parser.add_argument(
        "--decision-threshold",
        type=float,
        default=0.5,
        help="Threshold used to binarize scores.",
    )
    return parser.parse_args()


def _safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def _round(value: float, digits: int = 4) -> float:
    return round(float(value), digits)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        rows.append(json.loads(raw))
    return rows


def _load_optional_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return _load_jsonl(path)


def _roc_auc(labels: list[int], scores: list[float]) -> float:
    positives = [score for label, score in zip(labels, scores, strict=False) if label == 1]
    negatives = [score for label, score in zip(labels, scores, strict=False) if label == 0]
    if not positives or not negatives:
        return 0.0

    wins = 0.0
    total = len(positives) * len(negatives)
    for pos_score in positives:
        for neg_score in negatives:
            if pos_score > neg_score:
                wins += 1.0
            elif pos_score == neg_score:
                wins += 0.5
    return wins / total


def _calibration_ece(labels: list[int], scores: list[float], bins: int = 10) -> float:
    if not labels:
        return 0.0

    n = len(labels)
    ece = 0.0
    for bin_index in range(bins):
        low = bin_index / bins
        high = (bin_index + 1) / bins
        selected = [
            idx
            for idx, score in enumerate(scores)
            if score >= low and (score < high or (bin_index == bins - 1 and score <= high))
        ]
        if not selected:
            continue

        avg_conf = mean(scores[idx] for idx in selected)
        avg_acc = mean(labels[idx] for idx in selected)
        ece += (len(selected) / n) * abs(avg_conf - avg_acc)

    return ece


def _brier_score(labels: list[int], scores: list[float]) -> float:
    if not labels:
        return 0.0
    return mean((score - label) ** 2 for label, score in zip(labels, scores, strict=False))


def _binary_metrics(labels: list[int], scores: list[float], threshold: float) -> dict[str, float | int]:
    predictions = [1 if score >= threshold else 0 for score in scores]

    tp = fp = fn = tn = 0
    for label, prediction in zip(labels, predictions, strict=False):
        if label == 1 and prediction == 1:
            tp += 1
        elif label == 0 and prediction == 1:
            fp += 1
        elif label == 1 and prediction == 0:
            fn += 1
        else:
            tn += 1

    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall) if precision + recall else 0.0
    accuracy = _safe_div(tp + tn, len(labels))

    return {
        "threshold": threshold,
        "samples": len(labels),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": _round(precision),
        "recall": _round(recall),
        "f1": _round(f1),
        "accuracy": _round(accuracy),
    }


def _false_positive_by_domain(
    rows: list[dict[str, Any]],
    threshold: float,
) -> dict[str, float]:
    totals: dict[str, int] = {}
    false_positives: dict[str, int] = {}

    for row in rows:
        label = int(row["label_is_ai"])
        if label != 0:
            continue

        domain = str(row["domain"])
        totals[domain] = totals.get(domain, 0) + 1
        if float(row["baseline_score"]) >= threshold:
            false_positives[domain] = false_positives.get(domain, 0) + 1

    return {
        domain: _round(_safe_div(false_positives.get(domain, 0), total))
        for domain, total in sorted(totals.items())
    }


def _evaluate_detection(rows: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    labels = [int(row["label_is_ai"]) for row in rows]
    scores = [float(row["baseline_score"]) for row in rows]

    metrics = _binary_metrics(labels, scores, threshold)
    metrics.update(
        {
            "roc_auc": _round(_roc_auc(labels, scores)),
            "calibration_ece": _round(_calibration_ece(labels, scores)),
            "brier_score": _round(_brier_score(labels, scores)),
            "false_positive_rate_by_domain": _false_positive_by_domain(rows, threshold),
        }
    )
    return metrics


def _evaluate_attribution(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    correct = 0
    per_family_total: dict[str, int] = {}
    per_family_correct: dict[str, int] = {}

    for row in rows:
        truth = str(row["true_model_family"])
        pred = str(row["predicted_model_family_baseline"])

        per_family_total[truth] = per_family_total.get(truth, 0) + 1
        if truth == pred:
            correct += 1
            per_family_correct[truth] = per_family_correct.get(truth, 0) + 1

    per_family_accuracy = {
        family: _round(_safe_div(per_family_correct.get(family, 0), count))
        for family, count in sorted(per_family_total.items())
    }

    return {
        "samples": total,
        "correct": correct,
        "accuracy": _round(_safe_div(correct, total)),
        "per_family_accuracy": per_family_accuracy,
    }


def _evaluate_tamper(rows: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    by_transform: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        transform = str(row["transform"])
        by_transform.setdefault(transform, []).append(row)

    transform_metrics: dict[str, dict[str, Any]] = {}
    transform_f1: dict[str, float] = {}
    for transform, group_rows in sorted(by_transform.items()):
        labels = [int(row["label_is_ai"]) for row in group_rows]
        scores = [float(row["baseline_score"]) for row in group_rows]
        metrics = _binary_metrics(labels, scores, threshold)
        transform_metrics[transform] = metrics
        transform_f1[transform] = float(metrics["f1"])

    clean_f1 = transform_f1.get("clean", 0.0)
    attacked = [
        score for name, score in transform_f1.items() if name in {"paraphrase", "translate", "human_edit"}
    ]
    attacked_avg_f1 = mean(attacked) if attacked else 0.0
    robustness_score = _safe_div(attacked_avg_f1, clean_f1) if clean_f1 else 0.0

    return {
        "samples": len(rows),
        "per_transform": transform_metrics,
        "clean_f1": _round(clean_f1),
        "attacked_avg_f1": _round(attacked_avg_f1),
        "robustness_score": _round(robustness_score),
    }


def _write_markdown_summary(path: Path, results: dict[str, Any], model_id: str) -> None:
    detection = results["tasks"]["ai_vs_human_detection"]
    attribution = results["tasks"]["source_attribution"]
    tamper = results["tasks"]["tamper_detection"]
    audio_detection = results["tasks"].get("audio_ai_vs_human_detection", {})
    video_detection = results["tasks"].get("video_ai_vs_human_detection", {})

    lines = [
        "# Public Benchmark Baseline Results",
        "",
        f"- Model ID: `{model_id}`",
        f"- Generated: `{results['generated_at']}`",
        "",
        "## Baseline Table",
        "",
        "| Task | Primary Metric | Value |",
        "| --- | --- | ---: |",
        f"| AI vs Human Detection | F1 | {detection['f1']} |",
        f"| AI vs Human Detection | ROC-AUC | {detection['roc_auc']} |",
        f"| Audio AI vs Human Detection | F1 | {audio_detection.get('f1', 'n/a')} |",
        f"| Video AI vs Human Detection | F1 | {video_detection.get('f1', 'n/a')} |",
        f"| Source Attribution | Accuracy | {attribution['accuracy']} |",
        f"| Tamper Robustness | Robustness Score | {tamper['robustness_score']} |",
        "",
        "## Trust Report Metrics",
        "",
        f"- Calibration ECE: `{detection['calibration_ece']}`",
        f"- Brier Score: `{detection['brier_score']}`",
        f"- False Positive Rate by Domain: `{json.dumps(detection['false_positive_rate_by_domain'])}`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _upsert_leaderboard_entry(
    leaderboard_path: Path,
    model_id: str,
    results: dict[str, Any],
) -> dict[str, Any]:
    detection = results["tasks"]["ai_vs_human_detection"]
    attribution = results["tasks"]["source_attribution"]
    tamper = results["tasks"]["tamper_detection"]
    audio_detection = results["tasks"].get("audio_ai_vs_human_detection", {})
    video_detection = results["tasks"].get("video_ai_vs_human_detection", {})
    audio_f1 = float(audio_detection.get("f1", 0.0))
    video_f1 = float(video_detection.get("f1", 0.0))

    overall = (
        0.34 * float(detection["f1"])
        + 0.2 * float(detection["roc_auc"])
        + 0.18 * float(attribution["accuracy"])
        + 0.16 * float(tamper["robustness_score"])
        + 0.06 * audio_f1
        + 0.06 * video_f1
    )

    entry = {
        "model_id": model_id,
        "updated_at": results["generated_at"],
        "detection_f1": detection["f1"],
        "roc_auc": detection["roc_auc"],
        "audio_detection_f1": _round(audio_f1),
        "video_detection_f1": _round(video_f1),
        "attribution_accuracy": attribution["accuracy"],
        "robustness_score": tamper["robustness_score"],
        "overall_score": _round(overall),
    }

    if leaderboard_path.exists():
        board = json.loads(leaderboard_path.read_text(encoding="utf-8"))
    else:
        board = {
            "updated_at": results["generated_at"],
            "columns": [
                "rank",
                "model_id",
                "detection_f1",
                "roc_auc",
                "audio_detection_f1",
                "video_detection_f1",
                "attribution_accuracy",
                "robustness_score",
                "overall_score",
                "updated_at",
            ],
            "entries": [],
        }

    board["columns"] = [
        "rank",
        "model_id",
        "detection_f1",
        "roc_auc",
        "audio_detection_f1",
        "video_detection_f1",
        "attribution_accuracy",
        "robustness_score",
        "overall_score",
        "updated_at",
    ]

    existing = [
        item
        for item in board.get("entries", [])
        if item.get("model_id") != model_id
        and "audio_detection_f1" in item
        and "video_detection_f1" in item
    ]
    existing.append(entry)
    existing.sort(key=lambda item: float(item.get("overall_score", 0.0)), reverse=True)

    ranked_entries = []
    for index, item in enumerate(existing, start=1):
        item["rank"] = index
        ranked_entries.append(item)

    board["updated_at"] = results["generated_at"]
    board["entries"] = ranked_entries
    leaderboard_path.parent.mkdir(parents=True, exist_ok=True)
    leaderboard_path.write_text(json.dumps(board, ensure_ascii=False, indent=2), encoding="utf-8")
    return board


def run() -> int:
    args = parse_args()

    datasets_dir = Path(args.datasets_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    leaderboard_path = Path(args.leaderboard_output).expanduser().resolve()

    detection_rows = _load_jsonl(datasets_dir / "detection_multidomain.jsonl")
    attribution_rows = _load_jsonl(datasets_dir / "source_attribution.jsonl")
    tamper_rows = _load_jsonl(datasets_dir / "tamper_robustness.jsonl")
    audio_rows = _load_optional_jsonl(datasets_dir / "audio_detection.jsonl")
    video_rows = _load_optional_jsonl(datasets_dir / "video_detection.jsonl")

    results = {
        "generated_at": datetime.now(UTC).isoformat(),
        "benchmark_version": "v0.2",
        "datasets": {
            "detection_multidomain": len(detection_rows),
            "source_attribution": len(attribution_rows),
            "tamper_robustness": len(tamper_rows),
            "audio_detection": len(audio_rows),
            "video_detection": len(video_rows),
        },
        "tasks": {
            "ai_vs_human_detection": _evaluate_detection(
                detection_rows, threshold=args.decision_threshold
            ),
            "source_attribution": _evaluate_attribution(attribution_rows),
            "tamper_detection": _evaluate_tamper(tamper_rows, threshold=args.decision_threshold),
            "audio_ai_vs_human_detection": _evaluate_detection(
                audio_rows, threshold=args.decision_threshold
            )
            if audio_rows
            else {"status": "not_available", "samples": 0},
            "video_ai_vs_human_detection": _evaluate_detection(
                video_rows, threshold=args.decision_threshold
            )
            if video_rows
            else {"status": "not_available", "samples": 0},
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    result_json_path = output_dir / "benchmark_results.json"
    result_json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_path = output_dir / "baseline_results.md"
    _write_markdown_summary(summary_path, results, model_id=args.model_id)

    board = _upsert_leaderboard_entry(leaderboard_path, args.model_id, results)

    print(f"Wrote benchmark results JSON: {result_json_path}")
    print(f"Wrote benchmark summary Markdown: {summary_path}")
    print(f"Updated leaderboard JSON: {leaderboard_path}")
    print(f"Leaderboard entries: {len(board.get('entries', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

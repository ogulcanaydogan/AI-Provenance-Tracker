"""Evaluate detector threshold calibration on labeled samples."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.detection.audio.detector import AudioDetector  # noqa: E402
from app.detection.image.detector import ImageDetector  # noqa: E402
from app.detection.text.detector import TextDetector  # noqa: E402
from app.detection.video.detector import VideoDetector  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate confidence threshold calibration.")
    parser.add_argument("--input", required=True, help="Path to labeled JSONL samples")
    parser.add_argument(
        "--content-type",
        choices=["text", "image", "audio", "video"],
        required=True,
        help="Detector modality to evaluate",
    )
    parser.add_argument("--output", default="calibration_report.json")
    parser.add_argument(
        "--register",
        action="store_true",
        help="Also copy report into registry directory for dashboard trend tracking.",
    )
    parser.add_argument(
        "--registry-dir",
        default="evidence/calibration",
        help="Directory used to store historical calibration reports.",
    )
    return parser.parse_args()


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _threshold_metrics(scores: list[tuple[float, bool]], threshold: float) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    for score, label_is_ai in scores:
        pred = score >= threshold
        if pred and label_is_ai:
            tp += 1
        elif pred and not label_is_ai:
            fp += 1
        elif not pred and not label_is_ai:
            tn += 1
        else:
            fn += 1

    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    accuracy = _safe_div(tp + tn, tp + tn + fp + fn)
    return {
        "threshold": round(threshold, 2),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }


def _resolve_sample_path(sample: dict[str, Any], content_type: str) -> Path | None:
    key_candidates = {
        "image": ("image_path", "path", "file_path"),
        "audio": ("audio_path", "path", "file_path"),
        "video": ("video_path", "path", "file_path"),
    }
    for key in key_candidates.get(content_type, ()):
        raw_path = str(sample.get(key, "")).strip()
        if raw_path:
            return Path(raw_path).expanduser()
    return None


async def _score_samples(
    samples: list[dict[str, Any]], content_type: str
) -> tuple[list[tuple[float, bool]], int]:
    scores: list[tuple[float, bool]] = []
    if content_type == "text":
        detector = TextDetector()
        for sample in samples:
            text = str(sample.get("text", "")).strip()
            if not text:
                continue
            result = await detector.detect(text)
            scores.append((float(result.confidence), bool(sample.get("label_is_ai"))))
        return scores, len(samples) - len(scores)

    if content_type == "image":
        detector = ImageDetector()
    elif content_type == "audio":
        detector = AudioDetector()
    else:
        detector = VideoDetector()

    skipped_samples = 0
    for sample in samples:
        file_path = _resolve_sample_path(sample, content_type)
        if file_path is None or not file_path.exists():
            skipped_samples += 1
            continue
        media_bytes = file_path.read_bytes()
        if not media_bytes:
            skipped_samples += 1
            continue
        try:
            result = await detector.detect(media_bytes, file_path.name)
        except ValueError:
            skipped_samples += 1
            continue
        scores.append((float(result.confidence), bool(sample.get("label_is_ai"))))
    return scores, skipped_samples


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        items.append(json.loads(line))
    return items


async def run() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        return 1

    samples = _load_jsonl(input_path)
    if not samples:
        print("No labeled samples found.")
        return 1

    scores, skipped_samples = await _score_samples(samples, args.content_type)
    if not scores:
        print("No valid samples were scored.")
        return 1

    thresholds = [i / 20 for i in range(4, 19)]  # 0.20 .. 0.90
    metrics = [_threshold_metrics(scores, threshold) for threshold in thresholds]
    best = max(metrics, key=lambda item: (item["f1"], item["accuracy"]))

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "content_type": args.content_type,
        "input_sample_count": len(samples),
        "sample_count": len(scores),
        "skipped_samples": skipped_samples,
        "recommended_threshold": best["threshold"],
        "best_metrics": best,
        "all_thresholds": metrics,
    }

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote calibration report to {output_path}")

    if args.register:
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        registry_path = (
            Path(args.registry_dir).expanduser().resolve() / args.content_type / f"{timestamp}.json"
        )
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Registered calibration report at {registry_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))

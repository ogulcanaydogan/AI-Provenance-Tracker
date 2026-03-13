"""Evaluate detector threshold calibration on labeled samples."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression

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
        "--profile-output",
        default="app/detection/text/calibration_profile.json",
        help="Text detector calibration profile output path (used with --write-profile).",
    )
    parser.add_argument(
        "--write-profile",
        action="store_true",
        help="Write recommended threshold/margin back to calibration profile for text modality.",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=100,
        help="Minimum scored samples required to accept calibration output.",
    )
    parser.add_argument(
        "--min-domain-samples",
        type=int,
        default=40,
        help="Minimum scored samples required before emitting per-domain calibration entries.",
    )
    parser.add_argument(
        "--include-domain-profiles",
        action="store_true",
        help="For text modality, compute per-domain threshold and uncertainty profiles.",
    )
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
    fp_rate = _safe_div(fp, fp + tn)
    fn_rate = _safe_div(fn, fn + tp)
    return {
        "threshold": round(threshold, 2),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4),
        "fp_rate": round(fp_rate, 4),
        "fn_rate": round(fn_rate, 4),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }


def _calibration_error_metrics(
    scores: list[tuple[float, bool]],
    *,
    bins: int = 10,
) -> dict[str, float]:
    if not scores:
        return {"ece": 0.0, "brier_score": 0.0}

    probabilities = np.array([score for score, _ in scores], dtype=float)
    labels = np.array([1.0 if is_ai else 0.0 for _, is_ai in scores], dtype=float)
    probabilities = np.clip(probabilities, 0.0, 1.0)
    brier = float(np.mean((probabilities - labels) ** 2))

    bin_edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    sample_count = len(scores)
    for index in range(bins):
        lower = bin_edges[index]
        upper = bin_edges[index + 1]
        if index == bins - 1:
            mask = (probabilities >= lower) & (probabilities <= upper)
        else:
            mask = (probabilities >= lower) & (probabilities < upper)
        if not np.any(mask):
            continue
        confidence_bin = float(np.mean(probabilities[mask]))
        accuracy_bin = float(np.mean(labels[mask]))
        weight = float(np.sum(mask)) / sample_count
        ece += abs(confidence_bin - accuracy_bin) * weight

    return {
        "ece": round(float(ece), 4),
        "brier_score": round(brier, 4),
    }


def _fit_platt_scaler(scores: list[tuple[float, bool]]) -> dict[str, Any] | None:
    if len(scores) < 2:
        return None

    x = np.array([score for score, _ in scores], dtype=float).reshape(-1, 1)
    y = np.array([1 if is_ai else 0 for _, is_ai in scores], dtype=int)

    if len(np.unique(y)) < 2 or len(np.unique(x)) < 2:
        return None

    model = LogisticRegression(solver="lbfgs", C=1000.0, max_iter=2000)
    model.fit(x, y)
    coef = float(model.coef_[0][0])
    intercept = float(model.intercept_[0])
    return {
        "type": "platt",
        "coef": round(coef, 6),
        "intercept": round(intercept, 6),
        "sample_count": len(scores),
    }


def _apply_calibration_map(score: float, calibration_map: dict[str, Any] | None) -> float:
    clipped = float(np.clip(score, 0.0, 1.0))
    if not isinstance(calibration_map, dict):
        return clipped
    if str(calibration_map.get("type", "")).lower() != "platt":
        return clipped

    try:
        coef = float(calibration_map["coef"])
        intercept = float(calibration_map["intercept"])
    except (KeyError, TypeError, ValueError):
        return clipped

    logit = float(np.clip((coef * clipped) + intercept, -60.0, 60.0))
    calibrated = 1.0 / (1.0 + math.exp(-logit))
    return float(np.clip(calibrated, 0.0, 1.0))


def _apply_calibration_to_scores(
    scores: list[tuple[float, bool]],
    calibration_map: dict[str, Any] | None,
) -> list[tuple[float, bool]]:
    return [(_apply_calibration_map(score, calibration_map), label_is_ai) for score, label_is_ai in scores]


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


def _resolve_text_sample(sample: dict[str, Any]) -> str:
    direct_text = str(sample.get("text", "")).strip()
    if direct_text:
        return direct_text

    input_ref = str(sample.get("input_ref", "")).strip()
    if not input_ref:
        return ""

    input_path = Path(input_ref).expanduser()
    if not input_path.is_absolute():
        repo_root = BACKEND_ROOT.parent
        input_path = (repo_root / input_ref).resolve()
    if not input_path.exists():
        return ""
    try:
        return input_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return ""


def _estimate_uncertainty_margin(scores: list[tuple[float, bool]], threshold: float) -> float:
    misclassified_distances = [
        abs(score - threshold)
        for score, label_is_ai in scores
        if (score >= threshold) != label_is_ai
    ]
    if misclassified_distances:
        raw_margin = float(np.percentile(misclassified_distances, 75))
    else:
        all_distances = sorted(abs(score - threshold) for score, _ in scores)
        if not all_distances:
            return 0.08
        pivot = max(3, len(all_distances) // 10)
        raw_margin = float(np.mean(all_distances[:pivot]))

    return round(float(np.clip(raw_margin, 0.04, 0.18)), 3)


def _normalize_domain(value: Any) -> str:
    if not isinstance(value, str):
        return "general"
    normalized = value.strip().lower().replace("_", "-")
    aliases = {
        "news": "news",
        "social": "social",
        "marketing": "marketing",
        "finance": "marketing",
        "code": "code-doc",
        "code-doc": "code-doc",
        "codedoc": "code-doc",
        "academic": "academic",
        "education": "academic",
        "science": "academic",
        "legal": "academic",
        "health": "general",
        "general": "general",
    }
    return aliases.get(normalized, "general")


async def _score_samples(
    samples: list[dict[str, Any]], content_type: str
) -> tuple[list[tuple[float, bool]], int]:
    scores, skipped, _metadata = await _score_samples_with_metadata(samples, content_type)
    return scores, skipped


async def _score_samples_with_metadata(
    samples: list[dict[str, Any]], content_type: str
) -> tuple[list[tuple[float, bool]], int, dict[str, str | None]]:
    scores: list[tuple[float, bool]] = []
    metadata: dict[str, str | None] = {"model_version": None, "calibration_version": None}
    if content_type == "text":
        detector = TextDetector()
        for sample in samples:
            modality = str(sample.get("modality", "text")).strip().lower()
            if modality and modality != "text":
                continue
            text = _resolve_text_sample(sample)
            if not text:
                continue
            domain_hint = _normalize_domain(sample.get("domain"))
            result = await detector.detect(text, domain=domain_hint)
            scores.append((float(result.confidence), bool(sample.get("label_is_ai"))))
            metadata["model_version"] = metadata["model_version"] or result.model_version
            metadata["calibration_version"] = (
                metadata["calibration_version"] or result.calibration_version
            )
        return scores, len(samples) - len(scores), metadata

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
        metadata["model_version"] = metadata["model_version"] or result.model_version
        metadata["calibration_version"] = metadata["calibration_version"] or result.calibration_version
    return scores, skipped_samples, metadata


async def _score_text_samples_by_domain(
    samples: list[dict[str, Any]],
) -> tuple[dict[str, list[tuple[float, bool]]], int]:
    detector = TextDetector()
    domain_scores: dict[str, list[tuple[float, bool]]] = {}
    skipped = 0
    for sample in samples:
        modality = str(sample.get("modality", "text")).strip().lower()
        if modality and modality != "text":
            continue
        text = _resolve_text_sample(sample)
        if not text:
            skipped += 1
            continue
        domain_hint = _normalize_domain(sample.get("domain"))
        result = await detector.detect(text, domain=domain_hint)
        domain = _normalize_domain(sample.get("domain"))
        domain_scores.setdefault(domain, []).append(
            (float(result.confidence), bool(sample.get("label_is_ai")))
        )
    return domain_scores, skipped


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

    scores, skipped_samples, version_meta = await _score_samples_with_metadata(samples, args.content_type)
    if not scores:
        print("No valid samples were scored.")
        return 1
    if len(scores) < args.min_samples:
        print(
            f"Insufficient scored samples: {len(scores)} < required minimum {args.min_samples}. "
            "Calibration aborted."
        )
        return 1

    calibration_map: dict[str, Any] | None = None
    evaluated_scores = scores
    if args.content_type == "text":
        calibration_map = _fit_platt_scaler(scores)
        evaluated_scores = _apply_calibration_to_scores(scores, calibration_map)

    thresholds = [i / 20 for i in range(4, 19)]  # 0.20 .. 0.90
    metrics = [_threshold_metrics(evaluated_scores, threshold) for threshold in thresholds]
    best = max(
        metrics,
        key=lambda item: (
            item["f1"] - (item["fp_rate"] * 0.35),
            item["accuracy"],
            -item["fp_rate"],
        ),
    )
    uncertainty_margin = _estimate_uncertainty_margin(evaluated_scores, best["threshold"])
    calibration_errors = _calibration_error_metrics(evaluated_scores)

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "content_type": args.content_type,
        "input_sample_count": len(samples),
        "sample_count": len(evaluated_scores),
        "skipped_samples": skipped_samples,
        "recommended_threshold": best["threshold"],
        "recommended_uncertainty_margin": uncertainty_margin,
        "ece": calibration_errors["ece"],
        "brier_score": calibration_errors["brier_score"],
        "model_version": version_meta.get("model_version"),
        "calibration_version": version_meta.get("calibration_version"),
        "best_metrics": best,
        "all_thresholds": metrics,
    }
    if calibration_map:
        report["calibration_map"] = calibration_map

    if args.content_type == "text" and args.include_domain_profiles:
        domain_scores, _domain_skipped = await _score_text_samples_by_domain(samples)
        domain_profiles: dict[str, dict[str, Any]] = {}
        for domain, domain_values in sorted(domain_scores.items()):
            if len(domain_values) < args.min_domain_samples:
                continue
            domain_evaluated = _apply_calibration_to_scores(domain_values, calibration_map)
            domain_metrics = [
                _threshold_metrics(domain_evaluated, threshold) for threshold in thresholds
            ]
            domain_best = max(
                domain_metrics,
                key=lambda item: (
                    item["f1"] - (item["fp_rate"] * 0.35),
                    item["accuracy"],
                    -item["fp_rate"],
                ),
            )
            domain_profiles[domain] = {
                "sample_count": len(domain_evaluated),
                "recommended_threshold": domain_best["threshold"],
                "recommended_uncertainty_margin": _estimate_uncertainty_margin(
                    domain_evaluated, domain_best["threshold"]
                ),
                **_calibration_error_metrics(domain_evaluated),
                "best_metrics": domain_best,
            }
        report["domain_profiles"] = domain_profiles

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote calibration report to {output_path}")

    if args.write_profile and args.content_type == "text":
        detector = TextDetector()
        profile_payload = {
            **detector._calibration_profile,  # noqa: SLF001 - internal profile baseline
            "version": f"calibrated-{datetime.now(UTC).strftime('%Y%m%d')}",
            "source": str(input_path),
            "sample_count": len(evaluated_scores),
            "decision_threshold": best["threshold"],
            "uncertainty_margin": uncertainty_margin,
            "calibrated_at": datetime.now(UTC).isoformat(),
        }
        if calibration_map:
            profile_payload["calibration_map"] = calibration_map
        if args.include_domain_profiles and isinstance(report.get("domain_profiles"), dict):
            profile_payload["domain_profiles"] = {
                domain: {
                    "decision_threshold": details["recommended_threshold"],
                    "uncertainty_margin": details["recommended_uncertainty_margin"],
                    "sample_count": details["sample_count"],
                }
                for domain, details in report["domain_profiles"].items()
            }
        profile_path = Path(args.profile_output).expanduser()
        if not profile_path.is_absolute():
            profile_path = (BACKEND_ROOT / profile_path).resolve()
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(
            json.dumps(profile_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Wrote calibration profile to {profile_path}")

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

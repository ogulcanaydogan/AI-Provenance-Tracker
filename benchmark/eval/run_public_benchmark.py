#!/usr/bin/env python3
"""Run the public provenance benchmark and produce leaderboard-ready artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import subprocess
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any
from uuid import uuid4


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
        default=0.45,
        help="Threshold used to binarize scores.",
    )
    parser.add_argument(
        "--backend-url",
        default="http://127.0.0.1:8000",
        help="Backend base URL used for live detector scoring.",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="Optional API key used for benchmark API requests.",
    )
    parser.add_argument(
        "--api-key-header",
        default="X-API-Key",
        help="Header name used when --api-key is provided.",
    )
    parser.add_argument(
        "--live-mode",
        default="true",
        help="Use live backend detector scoring (true/false).",
    )
    return parser.parse_args()


def _to_bool(value: str) -> bool:
    normalized = (value or "").strip().lower()
    return normalized not in {"0", "false", "no", "off"}


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


def _validate_required_fields(
    rows: list[dict[str, Any]],
    dataset_name: str,
    required_fields: tuple[str, ...],
) -> None:
    for index, row in enumerate(rows, start=1):
        missing = [field for field in required_fields if field not in row]
        if missing:
            sample_id = row.get("sample_id", f"row#{index}")
            raise ValueError(
                f"{dataset_name} sample {sample_id} is missing required fields: {', '.join(missing)}"
            )


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def _is_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def _resolve_input_ref(input_ref: str, repo_root: Path) -> str:
    if _is_url(input_ref):
        return input_ref
    return str((repo_root / input_ref).resolve())


def _read_text_input(input_ref: str, repo_root: Path) -> str:
    resolved = _resolve_input_ref(input_ref, repo_root)
    if _is_url(resolved):
        with urllib.request.urlopen(resolved, timeout=20) as response:
            return response.read().decode("utf-8")
    return Path(resolved).read_text(encoding="utf-8")


def _read_binary_input(input_ref: str, repo_root: Path) -> bytes:
    resolved = _resolve_input_ref(input_ref, repo_root)
    if _is_url(resolved):
        with urllib.request.urlopen(resolved, timeout=20) as response:
            return response.read()
    return Path(resolved).read_bytes()


def _http_json_post(
    url: str,
    payload: dict[str, Any],
    *,
    api_key: str,
    api_key_header: str,
) -> tuple[int, dict[str, Any] | None, str]:
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers[api_key_header] = api_key
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    return _execute_request(request)


def _multipart_body(
    field_name: str,
    filename: str,
    content: bytes,
    content_type: str,
) -> tuple[bytes, str]:
    boundary = f"benchmark-{uuid4().hex}"
    lines: list[bytes] = [
        f"--{boundary}".encode("utf-8"),
        (
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"'
        ).encode("utf-8"),
        f"Content-Type: {content_type}".encode("utf-8"),
        b"",
        content,
        f"--{boundary}--".encode("utf-8"),
        b"",
    ]
    body = b"\r\n".join(lines)
    return body, boundary


def _http_file_post(
    url: str,
    *,
    filename: str,
    file_content: bytes,
    content_type: str,
    api_key: str,
    api_key_header: str,
) -> tuple[int, dict[str, Any] | None, str]:
    body, boundary = _multipart_body("file", filename, file_content, content_type)
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    if api_key:
        headers[api_key_header] = api_key
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    return _execute_request(request)


def _execute_request(request: urllib.request.Request) -> tuple[int, dict[str, Any] | None, str]:
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            text = response.read().decode("utf-8")
            payload = json.loads(text) if text else {}
            return response.status, payload, ""
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        try:
            payload = json.loads(body) if body else None
        except json.JSONDecodeError:
            payload = None
        error = body[:300] if body else f"http_error:{exc.code}"
        return exc.code, payload, error
    except Exception as exc:  # pragma: no cover - defensive IO guard
        return 0, None, f"request_error:{exc}"


def _guess_content_type(input_ref: str, modality: str) -> str:
    guessed, _encoding = mimetypes.guess_type(input_ref)
    if guessed:
        return guessed
    fallback = {
        "image": "image/png",
        "audio": "audio/wav",
        "video": "video/mp4",
    }
    return fallback.get(modality, "application/octet-stream")


def _consensus_provider_statuses(payload: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {}
    consensus = payload.get("consensus")
    if not isinstance(consensus, dict):
        return {}
    providers = consensus.get("providers")
    if not isinstance(providers, list):
        return {}

    statuses: dict[str, str] = {}
    for item in providers:
        if not isinstance(item, dict):
            continue
        provider = item.get("provider")
        status = item.get("status")
        if isinstance(provider, str) and isinstance(status, str):
            statuses[provider] = status
    return statuses


def _provider_availability_matrix(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_provider: dict[str, dict[str, int]] = {}
    for row in rows:
        statuses = row.get("provider_statuses")
        if not isinstance(statuses, dict):
            continue
        for provider, status in statuses.items():
            if not isinstance(provider, str) or not isinstance(status, str):
                continue
            by_provider.setdefault(provider, {})
            by_provider[provider][status] = by_provider[provider].get(status, 0) + 1

    result: dict[str, Any] = {}
    for provider, counts in sorted(by_provider.items()):
        ordered = sorted(counts.items(), key=lambda item: item[1], reverse=True)
        primary = ordered[0][0] if ordered else "unknown"
        result[provider] = {
            "primary_status": primary,
            "observed_statuses": counts,
        }
    return result


def _git_commit_sha(repo_root: Path) -> str:
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return output
    except Exception:  # pragma: no cover - optional metadata
        return ""


def _score_sample_live(
    row: dict[str, Any],
    *,
    backend_url: str,
    api_key: str,
    api_key_header: str,
    repo_root: Path,
) -> dict[str, Any]:
    modality = str(row.get("modality", "text"))
    input_ref = str(row["input_ref"])
    task = str(row.get("task", "unknown"))
    endpoint_root = backend_url.rstrip("/") + "/api/v1/detect"
    result: dict[str, Any] = {
        "sample_id": str(row["sample_id"]),
        "task": task,
        "modality": modality,
        "domain": str(row.get("domain", "")),
        "transform": row.get("transform"),
        "label_is_ai": int(row["label_is_ai"]),
        "input_ref": input_ref,
        "status": "ok",
        "score": None,
        "prediction": None,
        "provider_statuses": {},
        "http_status": None,
        "error": "",
    }

    if modality == "text":
        text_payload = _read_text_input(input_ref, repo_root)
        status_code, payload, error = _http_json_post(
            endpoint_root + "/text",
            {"text": text_payload},
            api_key=api_key,
            api_key_header=api_key_header,
        )
    else:
        file_bytes = _read_binary_input(input_ref, repo_root)
        filename = Path(input_ref).name or f"sample-{modality}.bin"
        content_type = _guess_content_type(filename, modality)
        status_code, payload, error = _http_file_post(
            endpoint_root + f"/{modality}",
            filename=filename,
            file_content=file_bytes,
            content_type=content_type,
            api_key=api_key,
            api_key_header=api_key_header,
        )

    result["http_status"] = status_code
    if status_code != 200 or not isinstance(payload, dict):
        result["status"] = "error"
        result["error"] = error or f"http_status:{status_code}"
        return result

    confidence = payload.get("confidence")
    prediction = payload.get("is_ai_generated")
    if not isinstance(confidence, (int, float)) or not isinstance(prediction, bool):
        result["status"] = "error"
        result["error"] = "missing_or_invalid_detection_fields"
        return result

    result["score"] = float(confidence)
    result["prediction"] = int(prediction)
    result["provider_statuses"] = _consensus_provider_statuses(payload)
    return result


def _score_rows_live(
    rows: list[dict[str, Any]],
    *,
    backend_url: str,
    api_key: str,
    api_key_header: str,
    repo_root: Path,
) -> list[dict[str, Any]]:
    scored_rows: list[dict[str, Any]] = []
    cache: dict[tuple[str, str], dict[str, Any]] = {}

    for row in rows:
        modality = str(row.get("modality", "text"))
        input_ref = str(row["input_ref"])
        cache_key = (modality, input_ref)

        if cache_key not in cache:
            cache[cache_key] = _score_sample_live(
                row,
                backend_url=backend_url,
                api_key=api_key,
                api_key_header=api_key_header,
                repo_root=repo_root,
            )

        cached = cache[cache_key]
        scored_rows.append(
            {
                **cached,
                "sample_id": str(row["sample_id"]),
                "task": str(row.get("task", cached.get("task", ""))),
                "domain": str(row.get("domain", cached.get("domain", ""))),
                "transform": row.get("transform"),
                "label_is_ai": int(row["label_is_ai"]),
                "input_ref": str(row["input_ref"]),
            }
        )
    return scored_rows


def _score_rows_precomputed(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored_rows: list[dict[str, Any]] = []
    for row in rows:
        score = row.get("score")
        status = "ok" if isinstance(score, (int, float)) else "error"
        scored_rows.append(
            {
                "sample_id": str(row["sample_id"]),
                "task": str(row.get("task", "unknown")),
                "modality": str(row.get("modality", "text")),
                "domain": str(row.get("domain", "")),
                "transform": row.get("transform"),
                "label_is_ai": int(row["label_is_ai"]),
                "input_ref": str(row["input_ref"]),
                "status": status,
                "score": float(score) if isinstance(score, (int, float)) else None,
                "prediction": int(float(score) >= 0.5) if isinstance(score, (int, float)) else None,
                "http_status": None,
                "provider_statuses": {},
                "error": "" if status == "ok" else "missing_precomputed_score",
            }
        )
    return scored_rows


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
        if row["status"] != "ok" or row["score"] is None:
            continue
        label = int(row["label_is_ai"])
        if label != 0:
            continue

        domain = str(row.get("domain", "unknown"))
        totals[domain] = totals.get(domain, 0) + 1
        if float(row["score"]) >= threshold:
            false_positives[domain] = false_positives.get(domain, 0) + 1

    return {
        domain: _round(_safe_div(false_positives.get(domain, 0), total))
        for domain, total in sorted(totals.items())
    }


def _evaluate_detection(rows: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    valid_rows = [row for row in rows if row["status"] == "ok" and row["score"] is not None]
    labels = [int(row["label_is_ai"]) for row in valid_rows]
    scores = [float(row["score"]) for row in valid_rows]
    failed_count = len(rows) - len(valid_rows)

    if not valid_rows:
        return {
            "status": "not_available",
            "samples": len(rows),
            "evaluated_samples": 0,
            "failed_samples": failed_count,
        }

    metrics = _binary_metrics(labels, scores, threshold)
    metrics.update(
        {
            "evaluated_samples": len(valid_rows),
            "failed_samples": failed_count,
            "roc_auc": _round(_roc_auc(labels, scores)),
            "calibration_ece": _round(_calibration_ece(labels, scores)),
            "brier_score": _round(_brier_score(labels, scores)),
            "false_positive_rate_by_domain": _false_positive_by_domain(valid_rows, threshold),
        }
    )
    return metrics


def _evaluate_attribution(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    correct = 0
    per_family_total: dict[str, int] = {}
    per_family_correct: dict[str, int] = {}

    for row in rows:
        truth = str(row.get("true_model_family") or row.get("source_model_family") or "")
        pred = str(row.get("predicted_model_family_baseline") or "")
        if not truth or not pred:
            continue

        per_family_total[truth] = per_family_total.get(truth, 0) + 1
        if truth == pred:
            correct += 1
            per_family_correct[truth] = per_family_correct.get(truth, 0) + 1

    evaluated = sum(per_family_total.values())
    per_family_accuracy = {
        family: _round(_safe_div(per_family_correct.get(family, 0), count))
        for family, count in sorted(per_family_total.items())
    }

    return {
        "samples": total,
        "evaluated_samples": evaluated,
        "correct": correct,
        "accuracy": _round(_safe_div(correct, evaluated)),
        "per_family_accuracy": per_family_accuracy,
        "method": "heuristic_attribution_baseline",
    }


def _evaluate_tamper(rows: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    by_transform: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        transform = str(row.get("transform", "unknown"))
        by_transform.setdefault(transform, []).append(row)

    transform_metrics: dict[str, dict[str, Any]] = {}
    transform_f1: dict[str, float] = {}
    for transform, group_rows in sorted(by_transform.items()):
        metrics = _evaluate_detection(group_rows, threshold)
        transform_metrics[transform] = metrics
        transform_f1[transform] = float(metrics.get("f1", 0.0))

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
        f"- Live mode: `{results['live_mode']}`",
        "",
        "## Baseline Table",
        "",
        "| Task | Primary Metric | Value |",
        "| --- | --- | ---: |",
        f"| AI vs Human Detection | F1 | {detection.get('f1', 'n/a')} |",
        f"| AI vs Human Detection | ROC-AUC | {detection.get('roc_auc', 'n/a')} |",
        f"| Audio AI vs Human Detection | F1 | {audio_detection.get('f1', 'n/a')} |",
        f"| Video AI vs Human Detection | F1 | {video_detection.get('f1', 'n/a')} |",
        f"| Source Attribution (heuristic baseline) | Accuracy | {attribution.get('accuracy', 'n/a')} |",
        f"| Tamper Robustness | Robustness Score | {tamper.get('robustness_score', 'n/a')} |",
        "",
        "## Trust Report Metrics",
        "",
        f"- Calibration ECE: `{detection.get('calibration_ece', 'n/a')}`",
        f"- Brier Score: `{detection.get('brier_score', 'n/a')}`",
        (
            f"- False Positive Rate by Domain: "
            f"`{json.dumps(detection.get('false_positive_rate_by_domain', {}))}`"
        ),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _as_float(task: dict[str, Any], key: str) -> float:
    value = task.get(key)
    return float(value) if isinstance(value, (int, float)) else 0.0


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
    audio_f1 = _as_float(audio_detection, "f1")
    video_f1 = _as_float(video_detection, "f1")

    overall = (
        0.34 * _as_float(detection, "f1")
        + 0.2 * _as_float(detection, "roc_auc")
        + 0.18 * _as_float(attribution, "accuracy")
        + 0.16 * _as_float(tamper, "robustness_score")
        + 0.06 * audio_f1
        + 0.06 * video_f1
    )

    entry = {
        "model_id": model_id,
        "updated_at": results["generated_at"],
        "detection_f1": _round(_as_float(detection, "f1")),
        "roc_auc": _round(_as_float(detection, "roc_auc")),
        "audio_detection_f1": _round(audio_f1),
        "video_detection_f1": _round(video_f1),
        "attribution_accuracy": _round(_as_float(attribution, "accuracy")),
        "robustness_score": _round(_as_float(tamper, "robustness_score")),
        "overall_score": _round(overall),
        "audio_video_experimental": True,
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

    existing = [item for item in board.get("entries", []) if item.get("model_id") != model_id]
    existing.append(entry)
    existing.sort(key=lambda item: float(item.get("overall_score", 0.0)), reverse=True)

    ranked_entries = []
    for index, item in enumerate(existing, start=1):
        item["rank"] = index
        item.setdefault("audio_video_experimental", True)
        ranked_entries.append(item)

    board["updated_at"] = results["generated_at"]
    board["entries"] = ranked_entries
    leaderboard_path.parent.mkdir(parents=True, exist_ok=True)
    leaderboard_path.write_text(json.dumps(board, ensure_ascii=False, indent=2), encoding="utf-8")
    return board


def _write_scored_samples(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(row, ensure_ascii=False) for row in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def run() -> int:
    args = parse_args()
    live_mode = _to_bool(args.live_mode)

    repo_root = Path(__file__).resolve().parents[2]
    datasets_dir = Path(args.datasets_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    leaderboard_path = Path(args.leaderboard_output).expanduser().resolve()

    detection_rows = _load_jsonl(datasets_dir / "detection_multidomain.jsonl")
    attribution_rows = _load_jsonl(datasets_dir / "source_attribution.jsonl")
    tamper_rows = _load_jsonl(datasets_dir / "tamper_robustness.jsonl")
    audio_rows = _load_optional_jsonl(datasets_dir / "audio_detection.jsonl")
    video_rows = _load_optional_jsonl(datasets_dir / "video_detection.jsonl")

    _validate_required_fields(
        detection_rows,
        "detection_multidomain.jsonl",
        ("sample_id", "task", "domain", "label_is_ai", "modality", "input_ref"),
    )
    _validate_required_fields(
        attribution_rows,
        "source_attribution.jsonl",
        ("sample_id", "source_model_family", "predicted_model_family_baseline"),
    )
    _validate_required_fields(
        tamper_rows,
        "tamper_robustness.jsonl",
        ("sample_id", "task", "domain", "label_is_ai", "modality", "input_ref", "transform"),
    )
    if audio_rows:
        _validate_required_fields(
            audio_rows,
            "audio_detection.jsonl",
            ("sample_id", "task", "domain", "label_is_ai", "modality", "input_ref"),
        )
    if video_rows:
        _validate_required_fields(
            video_rows,
            "video_detection.jsonl",
            ("sample_id", "task", "domain", "label_is_ai", "modality", "input_ref"),
        )

    if live_mode:
        scored_detection_rows = _score_rows_live(
            detection_rows,
            backend_url=args.backend_url,
            api_key=args.api_key,
            api_key_header=args.api_key_header,
            repo_root=repo_root,
        )
        scored_tamper_rows = _score_rows_live(
            tamper_rows,
            backend_url=args.backend_url,
            api_key=args.api_key,
            api_key_header=args.api_key_header,
            repo_root=repo_root,
        )
        scored_audio_rows = _score_rows_live(
            audio_rows,
            backend_url=args.backend_url,
            api_key=args.api_key,
            api_key_header=args.api_key_header,
            repo_root=repo_root,
        )
        scored_video_rows = _score_rows_live(
            video_rows,
            backend_url=args.backend_url,
            api_key=args.api_key,
            api_key_header=args.api_key_header,
            repo_root=repo_root,
        )
    else:
        scored_detection_rows = _score_rows_precomputed(detection_rows)
        scored_tamper_rows = _score_rows_precomputed(tamper_rows)
        scored_audio_rows = _score_rows_precomputed(audio_rows)
        scored_video_rows = _score_rows_precomputed(video_rows)

    all_scored_rows = (
        scored_detection_rows + scored_tamper_rows + scored_audio_rows + scored_video_rows
    )

    results = {
        "generated_at": datetime.now(UTC).isoformat(),
        "benchmark_version": "v1.0-live",
        "live_mode": live_mode,
        "backend_url": args.backend_url,
        "run_metadata": {
            "model_id": args.model_id,
            "decision_threshold": args.decision_threshold,
            "git_commit_sha": _git_commit_sha(repo_root),
            "run_command": (
                "python benchmark/eval/run_public_benchmark.py "
                f"--datasets-dir {args.datasets_dir} "
                f"--output-dir {args.output_dir} "
                f"--leaderboard-output {args.leaderboard_output} "
                f"--model-id {args.model_id} "
                f"--decision-threshold {args.decision_threshold} "
                f"--backend-url {args.backend_url} "
                f"--live-mode {str(live_mode).lower()}"
            ),
        },
        "datasets": {
            "detection_multidomain": len(detection_rows),
            "source_attribution": len(attribution_rows),
            "tamper_robustness": len(tamper_rows),
            "audio_detection": len(audio_rows),
            "video_detection": len(video_rows),
        },
        "dataset_hashes": {
            "detection_multidomain": _sha256(datasets_dir / "detection_multidomain.jsonl"),
            "source_attribution": _sha256(datasets_dir / "source_attribution.jsonl"),
            "tamper_robustness": _sha256(datasets_dir / "tamper_robustness.jsonl"),
            "audio_detection": _sha256(datasets_dir / "audio_detection.jsonl")
            if (datasets_dir / "audio_detection.jsonl").exists()
            else "",
            "video_detection": _sha256(datasets_dir / "video_detection.jsonl")
            if (datasets_dir / "video_detection.jsonl").exists()
            else "",
        },
        "tasks": {
            "ai_vs_human_detection": _evaluate_detection(
                scored_detection_rows, threshold=args.decision_threshold
            ),
            "source_attribution": _evaluate_attribution(attribution_rows),
            "tamper_detection": _evaluate_tamper(
                scored_tamper_rows, threshold=args.decision_threshold
            ),
            "audio_ai_vs_human_detection": _evaluate_detection(
                scored_audio_rows, threshold=args.decision_threshold
            )
            if audio_rows
            else {"status": "not_available", "samples": 0},
            "video_ai_vs_human_detection": _evaluate_detection(
                scored_video_rows, threshold=args.decision_threshold
            )
            if video_rows
            else {"status": "not_available", "samples": 0},
        },
        "provider_availability_matrix": _provider_availability_matrix(all_scored_rows),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    result_json_path = output_dir / "benchmark_results.json"
    scored_samples_path = output_dir / "scored_samples.jsonl"
    result_json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_scored_samples(scored_samples_path, all_scored_rows)

    summary_path = output_dir / "baseline_results.md"
    _write_markdown_summary(summary_path, results, model_id=args.model_id)

    board = _upsert_leaderboard_entry(leaderboard_path, args.model_id, results)

    print(f"Wrote benchmark results JSON: {result_json_path}")
    print(f"Wrote scored samples JSONL: {scored_samples_path}")
    print(f"Wrote benchmark summary Markdown: {summary_path}")
    print(f"Updated leaderboard JSON: {leaderboard_path}")
    print(f"Leaderboard entries: {len(board.get('entries', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

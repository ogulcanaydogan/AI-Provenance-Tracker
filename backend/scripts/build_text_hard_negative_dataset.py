#!/usr/bin/env python3
"""Build hard-negative text samples from benchmark scored outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract hard negatives from scored benchmark rows."
    )
    parser.add_argument(
        "--scored-samples",
        default="benchmark/results/latest/scored_samples.jsonl",
        help="Path to scored_samples.jsonl artifact from live benchmark.",
    )
    parser.add_argument(
        "--output",
        default="backend/evidence/samples/text_hard_negatives.jsonl",
        help="Output JSONL file.",
    )
    parser.add_argument(
        "--include-false-negatives",
        action="store_true",
        help="Include AI->human misses in addition to human->AI false positives.",
    )
    parser.add_argument(
        "--max-per-domain",
        type=int,
        default=120,
        help="Cap extracted records per domain to keep training balanced.",
    )
    parser.add_argument(
        "--min-score-gap",
        type=float,
        default=0.05,
        help="Minimum absolute gap from 0.5 score to count as a hard case.",
    )
    return parser.parse_args()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _read_text(repo_root: Path, input_ref: str) -> str:
    text_path = Path(input_ref)
    if not text_path.is_absolute():
        text_path = (repo_root / input_ref).resolve()
    if not text_path.exists():
        return ""
    return text_path.read_text(encoding="utf-8", errors="ignore").strip()


def _is_hard_false_positive(row: dict[str, Any], min_gap: float) -> bool:
    if row.get("status") != "ok" or row.get("modality") != "text":
        return False
    label_is_ai = int(row.get("label_is_ai", 0))
    prediction = int(row.get("prediction", 0))
    score = float(row.get("score", 0.0) or 0.0)
    return label_is_ai == 0 and prediction == 1 and abs(score - 0.5) >= min_gap


def _is_hard_false_negative(row: dict[str, Any], min_gap: float) -> bool:
    if row.get("status") != "ok" or row.get("modality") != "text":
        return False
    label_is_ai = int(row.get("label_is_ai", 0))
    prediction = int(row.get("prediction", 0))
    score = float(row.get("score", 0.0) or 0.0)
    return label_is_ai == 1 and prediction == 0 and abs(score - 0.5) >= min_gap


def run() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    scored_path = Path(args.scored_samples).expanduser()
    if not scored_path.is_absolute():
        scored_path = (repo_root / scored_path).resolve()
    if not scored_path.exists():
        raise SystemExit(f"Scored samples not found: {scored_path}")

    rows = _load_jsonl(scored_path)
    by_domain_counts: dict[str, int] = {}
    output_rows: list[dict[str, Any]] = []

    for row in rows:
        is_fp = _is_hard_false_positive(row, float(args.min_score_gap))
        is_fn = args.include_false_negatives and _is_hard_false_negative(
            row, float(args.min_score_gap)
        )
        if not is_fp and not is_fn:
            continue

        domain = str(row.get("domain", "general") or "general")
        domain_count = by_domain_counts.get(domain, 0)
        if domain_count >= int(args.max_per_domain):
            continue

        input_ref = str(row.get("input_ref", ""))
        if not input_ref:
            continue
        text = _read_text(repo_root, input_ref)
        if not text:
            continue

        output_rows.append(
            {
                "sample_id": str(row.get("sample_id")),
                "text": text,
                "label_is_ai": int(row.get("label_is_ai", 0)),
                "domain": domain,
                "hard_case_type": "false_positive" if is_fp else "false_negative",
                "score": float(row.get("score", 0.0) or 0.0),
                "prediction": int(row.get("prediction", 0)),
                "source_input_ref": input_ref,
                "source_scored_samples": str(scored_path),
            }
        )
        by_domain_counts[domain] = domain_count + 1

    output_path = Path(args.output).expanduser()
    if not output_path.is_absolute():
        output_path = (repo_root / output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in output_rows)
        + ("\n" if output_rows else ""),
        encoding="utf-8",
    )

    print(f"Wrote hard negatives: {output_path}")
    print(f"Rows: {len(output_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

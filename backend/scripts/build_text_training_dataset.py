#!/usr/bin/env python3
"""Build a larger labeled text corpus from benchmark datasets."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build expanded text training dataset from benchmark."
    )
    parser.add_argument(
        "--datasets-dir",
        default="benchmark/datasets",
        help="Benchmark datasets directory.",
    )
    parser.add_argument(
        "--output",
        default="backend/evidence/samples/text_labeled_expanded.jsonl",
        help="Output JSONL path.",
    )
    parser.add_argument(
        "--min-chars",
        type=int,
        default=80,
        help="Skip very short text samples.",
    )
    return parser.parse_args()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        rows.append(json.loads(raw))
    return rows


def _normalize_text(text: str) -> str:
    return " ".join(text.split()).strip()


def run() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    datasets_dir = (repo_root / args.datasets_dir).resolve()
    output_path = (repo_root / args.output).resolve()

    dataset_files = [
        "detection_multidomain.jsonl",
        "tamper_robustness.jsonl",
        "source_attribution.jsonl",
    ]

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    by_dataset = Counter()

    for dataset_name in dataset_files:
        dataset_path = datasets_dir / dataset_name
        if not dataset_path.exists():
            continue

        for row in _load_jsonl(dataset_path):
            if str(row.get("modality", "text")) != "text":
                continue

            input_ref = row.get("input_ref")
            if not isinstance(input_ref, str) or not input_ref.strip():
                continue

            sample_path = (repo_root / input_ref).resolve()
            if not sample_path.exists():
                continue

            text = _normalize_text(sample_path.read_text(encoding="utf-8", errors="ignore"))
            if len(text) < args.min_chars:
                continue

            label_is_ai = int(row.get("label_is_ai", 0))
            text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            dedupe_key = f"{text_hash}:{label_is_ai}"
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            rows.append(
                {
                    "sample_id": str(row.get("sample_id", text_hash[:12])),
                    "label_is_ai": label_is_ai,
                    "text": text,
                    "task": row.get("task"),
                    "domain": row.get("domain"),
                    "transform": row.get("transform"),
                    "source_model_family": row.get("source_model_family"),
                    "source_dataset": dataset_name,
                    "source_path": input_ref,
                }
            )
            by_dataset[dataset_name] += 1

    rows.sort(key=lambda item: str(item["sample_id"]))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )

    print(f"Wrote expanded text dataset: {output_path}")
    print(f"Total samples: {len(rows)}")
    for name, count in sorted(by_dataset.items()):
        print(f"  - {name}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

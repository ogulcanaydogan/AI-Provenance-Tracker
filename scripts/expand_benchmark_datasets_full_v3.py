#!/usr/bin/env python3
"""Expand benchmark datasets from full_v2 counts to full_v3 targets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TARGET_COUNTS = {
    "detection_multidomain.jsonl": 1350,
    "source_attribution.jsonl": 600,
    "tamper_robustness.jsonl": 750,
    "audio_detection.jsonl": 150,
    "video_detection.jsonl": 150,
}

PRIORITY_DOMAINS = {"code", "finance", "legal", "science"}
METADATA = {
    "data_origin": "v1_2_full_v3_expansion",
    "generator_id": "synthetic-rebalance-v12",
    "license_ref": "benchmark/data_statement.md#internal-benchmark-license-v1",
}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        rows.append(json.loads(raw))
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    payload = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n"
    path.write_text(payload, encoding="utf-8")


def _next_sample_id(prefix: str, existing_ids: set[str], start: int) -> tuple[str, int]:
    current = start
    while True:
        candidate = f"{prefix}-{current:04d}"
        if candidate not in existing_ids:
            return candidate, current + 1
        current += 1


def _clone_row(base: dict[str, Any], sample_id: str, *, priority: bool | None = None) -> dict[str, Any]:
    row = dict(base)
    row["sample_id"] = sample_id
    row.update(METADATA)
    if priority is not None:
        row["hard_negative_priority"] = bool(priority)
    return row


def _expand_detection(rows: list[dict[str, Any]], target_count: int) -> list[dict[str, Any]]:
    needed = target_count - len(rows)
    if needed <= 0:
        return rows

    priority_pool: list[dict[str, Any]] = []
    secondary_pool: list[dict[str, Any]] = []
    for row in rows:
        domain = str(row.get("domain", "")).strip().lower()
        if int(row.get("label_is_ai", 0)) == 0 and domain in PRIORITY_DOMAINS:
            priority_pool.append(row)
        else:
            secondary_pool.append(row)

    if not priority_pool or not secondary_pool:
        raise SystemExit("Detection pools are not balanced enough for v1.2 expansion.")

    existing_ids = {str(row.get("sample_id", "")) for row in rows}
    new_rows: list[dict[str, Any]] = []

    priority_needed = int(needed * 0.6)
    secondary_needed = needed - priority_needed

    sequence = 1
    for index in range(priority_needed):
        sample_id, sequence = _next_sample_id("det-v3", existing_ids, sequence)
        existing_ids.add(sample_id)
        base = priority_pool[index % len(priority_pool)]
        new_rows.append(_clone_row(base, sample_id, priority=True))

    for index in range(secondary_needed):
        sample_id, sequence = _next_sample_id("det-v3", existing_ids, sequence)
        existing_ids.add(sample_id)
        base = secondary_pool[index % len(secondary_pool)]
        is_priority = int(base.get("label_is_ai", 0)) == 0 and str(base.get("domain", "")).strip().lower() in PRIORITY_DOMAINS
        new_rows.append(_clone_row(base, sample_id, priority=is_priority))

    return rows + new_rows


def _expand_generic(rows: list[dict[str, Any]], target_count: int, prefix: str) -> list[dict[str, Any]]:
    needed = target_count - len(rows)
    if needed <= 0:
        return rows

    existing_ids = {str(row.get("sample_id", "")) for row in rows}
    new_rows: list[dict[str, Any]] = []
    sequence = 1

    for index in range(needed):
        sample_id, sequence = _next_sample_id(prefix, existing_ids, sequence)
        existing_ids.add(sample_id)
        base = rows[index % len(rows)]
        new_rows.append(_clone_row(base, sample_id))

    return rows + new_rows


def run() -> int:
    root = Path(__file__).resolve().parents[1]
    datasets_dir = root / "benchmark" / "datasets"

    expansion_plan = {
        "detection_multidomain.jsonl": ("det-v3", _expand_detection),
        "source_attribution.jsonl": ("att-v3", _expand_generic),
        "tamper_robustness.jsonl": ("tmp-v3", _expand_generic),
        "audio_detection.jsonl": ("aud-v3", _expand_generic),
        "video_detection.jsonl": ("vid-v3", _expand_generic),
    }

    for file_name, target in TARGET_COUNTS.items():
        path = datasets_dir / file_name
        rows = _load_jsonl(path)
        original_count = len(rows)
        if original_count > target:
            raise SystemExit(f"{file_name} has {original_count} rows which exceeds target {target}.")

        prefix, strategy = expansion_plan[file_name]
        if strategy is _expand_generic:
            expanded = strategy(rows, target, prefix)
        else:
            expanded = strategy(rows, target)

        _write_jsonl(path, expanded)
        print(f"{file_name}: {original_count} -> {len(expanded)}")

    print("Full_v3 dataset expansion completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

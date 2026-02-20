#!/usr/bin/env python3
"""Track benchmark dataset growth and coverage quality."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = ("sample_id", "task", "domain", "label_is_ai", "modality", "input_ref")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build benchmark dataset health report.")
    parser.add_argument("--datasets-dir", default="benchmark/datasets")
    parser.add_argument("--output-json", default="benchmark/results/latest/dataset_health.json")
    parser.add_argument("--output-md", default="benchmark/results/latest/dataset_health.md")
    parser.add_argument("--target-total", type=int, default=1000)
    parser.add_argument("--warn-total", type=int, default=500)
    parser.add_argument(
        "--task-target",
        action="append",
        default=[],
        help="Per-task minimum threshold in form task=count (repeatable)",
    )
    parser.add_argument(
        "--enforce",
        action="store_true",
        help="Fail when target thresholds are not met.",
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


def _parse_task_targets(values: list[str]) -> dict[str, int]:
    if not values:
        return {
            "ai_vs_human_detection": 400,
            "source_attribution": 200,
            "tamper_detection": 250,
            "audio_ai_vs_human_detection": 75,
            "video_ai_vs_human_detection": 75,
        }

    targets: dict[str, int] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Invalid --task-target '{value}'. Use task=count format.")
        task, count = value.split("=", 1)
        task = task.strip()
        if not task:
            raise ValueError(f"Invalid --task-target '{value}'.")
        targets[task] = int(count.strip())
    return targets


def _validate_rows(rows: list[dict[str, Any]], dataset_name: str) -> list[str]:
    issues: list[str] = []
    for index, row in enumerate(rows, start=1):
        missing = [field for field in REQUIRED_FIELDS if field not in row]
        if missing:
            sample_id = row.get("sample_id", f"{dataset_name}#{index}")
            issues.append(
                f"{dataset_name}:{sample_id} missing required fields: {', '.join(missing)}"
            )
    return issues


def _build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Dataset Health",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Target total: `{report['targets']['target_total']}`",
        f"- Current total: `{report['summary']['total_samples']}`",
        f"- Progress: `{report['summary']['target_progress_pct']:.2f}%`",
        "",
        "## Samples by Task",
        "",
        "| Task | Samples | Target | Meets Target |",
        "| --- | ---: | ---: | --- |",
    ]
    for row in report["summary"]["task_rows"]:
        lines.append(
            f"| {row['task']} | {row['count']} | {row['target']} | "
            f"{'yes' if row['meets_target'] else 'no'} |"
        )

    lines.extend(
        [
            "",
            "## Modality Distribution",
            "",
            "| Modality | Samples |",
            "| --- | ---: |",
        ]
    )
    for modality, count in report["summary"]["by_modality"].items():
        lines.append(f"| {modality} | {count} |")

    lines.extend(["", "## Alerts", ""])
    if not report["alerts"]:
        lines.append("- None")
    else:
        for alert in report["alerts"]:
            lines.append(f"- [{alert['level'].upper()}] {alert['message']}")

    if report["validation_issues"]:
        lines.extend(["", "## Validation Issues", ""])
        for issue in report["validation_issues"]:
            lines.append(f"- {issue}")

    lines.append("")
    return "\n".join(lines)


def run() -> int:
    args = parse_args()
    datasets_dir = Path(args.datasets_dir).expanduser().resolve()
    output_json = Path(args.output_json).expanduser().resolve()
    output_md = Path(args.output_md).expanduser().resolve()
    task_targets = _parse_task_targets(args.task_target)

    dataset_files = sorted(path for path in datasets_dir.glob("*.jsonl"))
    by_task: Counter[str] = Counter()
    by_modality: Counter[str] = Counter()
    by_domain: Counter[str] = Counter()
    validation_issues: list[str] = []

    total_samples = 0
    for dataset_file in dataset_files:
        rows = _load_jsonl(dataset_file)
        total_samples += len(rows)
        validation_issues.extend(_validate_rows(rows, dataset_file.name))
        for row in rows:
            by_task[str(row.get("task", "unknown"))] += 1
            by_modality[str(row.get("modality", "unknown"))] += 1
            by_domain[str(row.get("domain", "unknown"))] += 1

    alerts: list[dict[str, str]] = []
    if total_samples < args.warn_total:
        alerts.append(
            {
                "level": "warn",
                "message": (
                    f"Dataset total {total_samples} is below warning threshold {args.warn_total}. "
                    "Growth plan may be behind."
                ),
            }
        )
    if total_samples < args.target_total:
        alerts.append(
            {
                "level": "warn",
                "message": (
                    f"Dataset total {total_samples} is below target {args.target_total}. "
                    "Current benchmark is still below next-scale objective."
                ),
            }
        )

    task_rows: list[dict[str, Any]] = []
    for task, target in sorted(task_targets.items()):
        count = int(by_task.get(task, 0))
        meets_target = count >= target
        task_rows.append(
            {
                "task": task,
                "count": count,
                "target": target,
                "meets_target": meets_target,
            }
        )
        if not meets_target:
            alerts.append(
                {
                    "level": "warn",
                    "message": f"Task '{task}' count {count} is below target {target}.",
                }
            )

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "datasets_dir": str(datasets_dir),
        "datasets": [str(path.name) for path in dataset_files],
        "targets": {
            "target_total": args.target_total,
            "warn_total": args.warn_total,
            "task_targets": task_targets,
        },
        "summary": {
            "total_samples": total_samples,
            "target_progress_pct": round((total_samples / args.target_total) * 100.0, 2)
            if args.target_total
            else 0.0,
            "by_task": dict(sorted(by_task.items())),
            "task_rows": task_rows,
            "by_modality": dict(sorted(by_modality.items())),
            "top_domains": [
                {"domain": domain, "count": count}
                for domain, count in by_domain.most_common(15)
            ],
        },
        "validation_issues": validation_issues,
        "alerts": alerts,
        "status": "healthy" if not alerts and not validation_issues else "needs_attention",
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(_build_markdown(report), encoding="utf-8")

    print(f"Wrote dataset health JSON: {output_json}")
    print(f"Wrote dataset health Markdown: {output_md}")

    if args.enforce:
        has_warnings = bool(alerts or validation_issues)
        if has_warnings:
            print("Dataset health enforcement failed.")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

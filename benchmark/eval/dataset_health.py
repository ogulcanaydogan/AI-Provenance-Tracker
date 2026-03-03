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
DEFAULT_TARGET_PROFILES: dict[str, dict[str, Any]] = {
    "smoke_v2": {
        "target_total": 260,
        "warn_total": 220,
        "task_targets": {
            "ai_vs_human_detection": 120,
            "source_attribution": 50,
            "tamper_detection": 60,
            "audio_ai_vs_human_detection": 15,
            "video_ai_vs_human_detection": 15,
        },
    },
    "full_v2": {
        "target_total": 1500,
        "warn_total": 1350,
        "task_targets": {
            "ai_vs_human_detection": 675,
            "source_attribution": 300,
            "tamper_detection": 375,
            "audio_ai_vs_human_detection": 75,
            "video_ai_vs_human_detection": 75,
        },
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build benchmark dataset health report.")
    parser.add_argument("--datasets-dir", default="benchmark/datasets")
    parser.add_argument("--output-json", default="benchmark/results/latest/dataset_health.json")
    parser.add_argument("--output-md", default="benchmark/results/latest/dataset_health.md")
    parser.add_argument(
        "--targets-config",
        default="benchmark/config/benchmark_targets.yaml",
        help="Target profile config file path (JSON or simple YAML).",
    )
    parser.add_argument(
        "--target-profile",
        default="full_v2",
        help="Target profile name from targets config (for example full_v2, smoke_v2).",
    )
    parser.add_argument("--target-total", type=int, default=None)
    parser.add_argument("--warn-total", type=int, default=None)
    parser.add_argument(
        "--task-target",
        action="append",
        default=[],
        help="Per-task minimum threshold in form task=count (repeatable).",
    )
    parser.add_argument(
        "--enforce",
        action="store_true",
        help="Fail when target thresholds are not met.",
    )
    return parser.parse_args()


def _coerce_yaml_scalar(raw: str) -> Any:
    value = raw.strip()
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None
    if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_key: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            if current_key is None:
                continue
            data.setdefault(current_key, [])
            if isinstance(data[current_key], list):
                data[current_key].append(_coerce_yaml_scalar(stripped[2:]))
            continue
        if ":" not in stripped:
            continue
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not raw_value:
            current_key = key
            data[key] = []
            continue
        current_key = key
        data[key] = _coerce_yaml_scalar(raw_value)
    return data


def _load_targets_config(path: Path) -> dict[str, dict[str, Any]]:
    default_profiles = dict(DEFAULT_TARGET_PROFILES)
    if not path.exists():
        return default_profiles

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return default_profiles

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = _parse_simple_yaml(text)

    if not isinstance(parsed, dict):
        return default_profiles
    target_node = parsed.get("targets", parsed)
    if not isinstance(target_node, dict):
        return default_profiles

    loaded_profiles: dict[str, dict[str, Any]] = {}
    for profile, payload in target_node.items():
        if not isinstance(profile, str) or not isinstance(payload, dict):
            continue
        task_targets_raw = payload.get("task_targets", {})
        if not isinstance(task_targets_raw, dict):
            continue

        task_targets: dict[str, int] = {}
        for task, count in task_targets_raw.items():
            if not isinstance(task, str):
                continue
            try:
                task_targets[task] = int(count)
            except (TypeError, ValueError):
                continue

        if not task_targets:
            continue

        try:
            target_total = int(payload.get("target_total", 0))
        except (TypeError, ValueError):
            target_total = 0
        try:
            warn_total = int(payload.get("warn_total", 0))
        except (TypeError, ValueError):
            warn_total = 0

        loaded_profiles[profile] = {
            "target_total": target_total,
            "warn_total": warn_total,
            "task_targets": task_targets,
        }

    if not loaded_profiles:
        return default_profiles
    return loaded_profiles


def _resolve_targets(
    *,
    targets_config_path: Path,
    target_profile: str,
    target_total_override: int | None,
    warn_total_override: int | None,
    task_target_overrides: list[str],
) -> dict[str, Any]:
    all_profiles = _load_targets_config(targets_config_path)
    if target_profile not in all_profiles:
        available = ", ".join(sorted(all_profiles))
        raise ValueError(f"Unknown target profile '{target_profile}'. Available: {available}")

    resolved = dict(all_profiles[target_profile])
    resolved["task_targets"] = dict(resolved.get("task_targets", {}))

    if target_total_override is not None:
        resolved["target_total"] = int(target_total_override)
    if warn_total_override is not None:
        resolved["warn_total"] = int(warn_total_override)

    for task, count in _parse_task_targets(task_target_overrides).items():
        resolved["task_targets"][task] = count

    return resolved


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        rows.append(json.loads(raw))
    return rows


def _parse_task_targets(values: list[str]) -> dict[str, int]:
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
        f"- Target profile: `{report['targets']['target_profile']}`",
        f"- Targets config: `{report['targets']['targets_config_path']}`",
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
    targets_config_path = Path(args.targets_config).expanduser().resolve()

    resolved_targets = _resolve_targets(
        targets_config_path=targets_config_path,
        target_profile=str(args.target_profile),
        target_total_override=args.target_total,
        warn_total_override=args.warn_total,
        task_target_overrides=args.task_target,
    )
    target_total = int(resolved_targets["target_total"])
    warn_total = int(resolved_targets["warn_total"])
    task_targets: dict[str, int] = dict(resolved_targets["task_targets"])

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
    if total_samples < warn_total:
        alerts.append(
            {
                "level": "warn",
                "message": (
                    f"Dataset total {total_samples} is below warning threshold {warn_total}. "
                    "Growth plan may be behind."
                ),
            }
        )
    if total_samples < target_total:
        alerts.append(
            {
                "level": "warn",
                "message": (
                    f"Dataset total {total_samples} is below target {target_total}. "
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
            "target_profile": str(args.target_profile),
            "targets_config_path": str(targets_config_path),
            "target_total": target_total,
            "warn_total": warn_total,
            "task_targets": task_targets,
        },
        "summary": {
            "total_samples": total_samples,
            "target_progress_pct": round((total_samples / target_total) * 100.0, 2)
            if target_total
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

    if args.enforce and (alerts or validation_issues):
        print("Dataset health enforcement failed.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

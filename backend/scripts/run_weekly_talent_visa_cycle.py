"""Run one talent-visa pipeline cycle and compare it to the previous run if available."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run weekly talent-visa cycle with auto-comparison."
    )
    parser.add_argument("--handle", default="", help="Target handle, with or without @")
    parser.add_argument("--input-json", default="", help="Optional pre-collected input JSON path")
    parser.add_argument("--window-days", type=int, default=14)
    parser.add_argument("--max-posts", type=int, default=250)
    parser.add_argument("--query", default="")
    parser.add_argument("--labels", default="")
    parser.add_argument("--output-dir", default="evidence/runs/weekly")
    parser.add_argument("--comparisons-dir", default="evidence/runs/comparisons")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--run-prefix", default="weekly")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--summary-output", default="", help="Optional JSON summary output path")
    return parser.parse_args()


def _run_dirs(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        [path for path in root.iterdir() if path.is_dir()], key=lambda item: item.stat().st_mtime
    )


def _build_run_id(args: argparse.Namespace) -> str:
    if args.run_id.strip():
        return args.run_id.strip()
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    prefix = "".join(ch for ch in args.run_prefix if ch.isalnum() or ch in ("-", "_")).strip("_")
    if not prefix:
        prefix = "weekly"
    return f"{prefix}_{timestamp}"


def _run_python(script: str, script_args: list[str]) -> None:
    command = [sys.executable, str(BACKEND_ROOT / "scripts" / script), *script_args]
    subprocess.run(command, check=True, cwd=BACKEND_ROOT)


def run() -> int:
    args = parse_args()
    output_root = Path(args.output_dir).expanduser().resolve()
    comparisons_root = Path(args.comparisons_dir).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    comparisons_root.mkdir(parents=True, exist_ok=True)

    before_runs = _run_dirs(output_root)
    previous_run = before_runs[-1] if before_runs else None

    run_id = _build_run_id(args)
    pipeline_args = ["--output-dir", str(output_root), "--run-id", run_id]
    if args.overwrite:
        pipeline_args.append("--overwrite")

    if args.input_json:
        pipeline_args.extend(["--input-json", str(Path(args.input_json).expanduser().resolve())])
    else:
        if not args.handle.strip():
            print("Either --handle or --input-json must be provided.")
            return 1
        pipeline_args.extend(
            [
                "--handle",
                args.handle.strip(),
                "--window-days",
                str(args.window_days),
                "--max-posts",
                str(args.max_posts),
            ]
        )
        if args.query.strip():
            pipeline_args.extend(["--query", args.query.strip()])

    if args.labels.strip():
        pipeline_args.extend(["--labels", str(Path(args.labels).expanduser().resolve())])

    _run_python("run_talent_visa_pipeline.py", pipeline_args)

    current_run = output_root / run_id
    if not current_run.exists():
        print(f"Pipeline completed but run directory missing: {current_run}")
        return 1

    comparison_json = ""
    comparison_md = ""
    if (
        previous_run is not None
        and previous_run.exists()
        and previous_run.resolve() != current_run.resolve()
    ):
        file_stem = f"{previous_run.name}_vs_{current_run.name}"
        comparison_json_path = comparisons_root / f"{file_stem}.json"
        comparison_md_path = comparisons_root / f"{file_stem}.md"
        _run_python(
            "compare_talent_visa_runs.py",
            [
                "--base-run-dir",
                str(previous_run),
                "--candidate-run-dir",
                str(current_run),
                "--output-json",
                str(comparison_json_path),
                "--output-md",
                str(comparison_md_path),
            ],
        )
        comparison_json = str(comparison_json_path)
        comparison_md = str(comparison_md_path)

    summary: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "run_id": run_id,
        "current_run_dir": str(current_run),
        "previous_run_dir": str(previous_run) if previous_run else "",
        "comparison_json": comparison_json,
        "comparison_md": comparison_md,
    }

    if args.summary_output:
        summary_output = Path(args.summary_output).expanduser().resolve()
        summary_output.parent.mkdir(parents=True, exist_ok=True)
        summary_output.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Wrote weekly cycle summary to {summary_output}")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

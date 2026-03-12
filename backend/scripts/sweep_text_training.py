#!/usr/bin/env python3
"""Run hyperparameter sweeps for text detector fine-tuning."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

PROFILE_GRID: dict[str, dict[str, str]] = {
    "v11_fp_sweep_lr2e5_pen17": {"learning_rate": "2e-5", "fp_penalty": "1.7", "seed": "42"},
    "v11_fp_sweep_lr3e5_pen20": {"learning_rate": "3e-5", "fp_penalty": "2.0", "seed": "43"},
    "v11_fp_sweep_lr15e5_pen15": {
        "learning_rate": "1.5e-5",
        "fp_penalty": "1.5",
        "seed": "44",
    },
    "v11_fp_sweep_lr25e5_pen18": {
        "learning_rate": "2.5e-5",
        "fp_penalty": "1.8",
        "seed": "45",
    },
    "v11_fp_sweep_lr1e5_pen22": {"learning_rate": "1e-5", "fp_penalty": "2.2", "seed": "46"},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Hyperparameter sweep wrapper for train_text_detector.py"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute commands; otherwise print them only.",
    )
    parser.add_argument("--dataset", default="backend/evidence/samples/text_labeled_expanded.jsonl")
    parser.add_argument(
        "--hard-negatives", default="backend/evidence/samples/text_hard_negatives.jsonl"
    )
    parser.add_argument("--output-dir", default="backend/evidence/models/text")
    parser.add_argument("--base-model", default="distilroberta-base")
    parser.add_argument(
        "--profile",
        choices=["all", *PROFILE_GRID.keys()],
        default="all",
        help="Run all profiles or only one named profile.",
    )
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="Print available profile names and exit.",
    )
    return parser.parse_args()


def _commands(args: argparse.Namespace) -> list[list[str]]:
    root = Path(__file__).resolve().parents[2]
    python_exec = str(root / "backend" / ".venv" / "bin" / "python")
    if not Path(python_exec).exists():
        python_exec = "python3"

    base = [
        python_exec,
        "backend/scripts/train_text_detector.py",
        "--dataset",
        args.dataset,
        "--hard-negatives",
        args.hard_negatives,
        "--output-dir",
        args.output_dir,
        "--base-model",
        args.base_model,
        "--epochs",
        "2",
        "--max-train-samples",
        "0",
    ]

    profile_names = list(PROFILE_GRID.keys()) if args.profile == "all" else [args.profile]
    commands: list[list[str]] = []
    for profile_name in profile_names:
        profile = PROFILE_GRID[profile_name]
        commands.append(
            base
            + [
                "--run-name",
                profile_name,
                "--learning-rate",
                profile["learning_rate"],
                "--fp-penalty",
                profile["fp_penalty"],
                "--seed",
                profile["seed"],
            ]
        )
    return commands


def run() -> int:
    args = parse_args()
    if args.list_profiles:
        for profile_name in PROFILE_GRID:
            print(profile_name)
        return 0

    commands = _commands(args)
    for command in commands:
        print(" ".join(command))
        if args.execute:
            result = subprocess.run(command, check=False)
            if result.returncode != 0:
                return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

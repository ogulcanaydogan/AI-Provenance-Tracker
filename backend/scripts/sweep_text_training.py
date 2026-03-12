#!/usr/bin/env python3
"""Run hyperparameter sweeps for text detector fine-tuning."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


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

    profiles = [
        [
            "--run-name",
            "v11_fp_sweep_lr2e5_pen17",
            "--learning-rate",
            "2e-5",
            "--fp-penalty",
            "1.7",
            "--seed",
            "42",
        ],
        [
            "--run-name",
            "v11_fp_sweep_lr3e5_pen20",
            "--learning-rate",
            "3e-5",
            "--fp-penalty",
            "2.0",
            "--seed",
            "43",
        ],
        [
            "--run-name",
            "v11_fp_sweep_lr15e5_pen15",
            "--learning-rate",
            "1.5e-5",
            "--fp-penalty",
            "1.5",
            "--seed",
            "44",
        ],
    ]

    return [base + profile for profile in profiles]


def run() -> int:
    args = parse_args()
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

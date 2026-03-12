from __future__ import annotations

import argparse
import importlib.util
import types
from pathlib import Path


def _load_script_module(script_name: str) -> types.ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(script_name.replace(".py", ""), script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sweep_commands_all_profiles() -> None:
    module = _load_script_module("sweep_text_training.py")
    args = argparse.Namespace(
        execute=False,
        dataset="backend/evidence/samples/text_labeled_expanded.jsonl",
        hard_negatives="backend/evidence/samples/text_hard_negatives.jsonl",
        output_dir="backend/evidence/models/text",
        base_model="distilroberta-base",
        profile="all",
        list_profiles=False,
    )

    commands = module._commands(args)
    assert len(commands) == len(module.PROFILE_GRID)
    assert all("backend/scripts/train_text_detector.py" in command for command in commands)


def test_sweep_commands_single_profile() -> None:
    module = _load_script_module("sweep_text_training.py")
    args = argparse.Namespace(
        execute=False,
        dataset="backend/evidence/samples/text_labeled_expanded.jsonl",
        hard_negatives="backend/evidence/samples/text_hard_negatives.jsonl",
        output_dir="backend/evidence/models/text",
        base_model="distilroberta-base",
        profile="v11_fp_sweep_lr25e5_pen18",
        list_profiles=False,
    )

    commands = module._commands(args)
    assert len(commands) == 1
    assert "--run-name" in commands[0]
    assert "v11_fp_sweep_lr25e5_pen18" in commands[0]


def test_list_profiles_mode(capsys) -> None:  # type: ignore[no-untyped-def]
    module = _load_script_module("sweep_text_training.py")

    import sys

    original = sys.argv
    sys.argv = ["sweep_text_training.py", "--list-profiles"]
    try:
        rc = module.run()
    finally:
        sys.argv = original

    assert rc == 0
    output_lines = [line.strip() for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert output_lines == list(module.PROFILE_GRID.keys())

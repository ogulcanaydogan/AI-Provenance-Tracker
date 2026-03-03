from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_BENCHMARK_PATH = REPO_ROOT / "benchmark" / "eval" / "run_public_benchmark.py"
DATASET_HEALTH_PATH = REPO_ROOT / "benchmark" / "eval" / "dataset_health.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


run_benchmark_module = _load_module(RUN_BENCHMARK_PATH, "run_public_benchmark_test")
dataset_health_module = _load_module(DATASET_HEALTH_PATH, "dataset_health_test")


@pytest.fixture(autouse=True)
def _reset_runtime_state():
    """Override global async DB fixture for pure script-level tests."""
    yield


def test_select_profile_rows_is_deterministic() -> None:
    rows = [
        {
            "sample_id": f"sample-{idx:03d}",
            "task": "ai_vs_human_detection",
            "domain": "news",
            "label_is_ai": idx % 2,
            "modality": "text",
            "input_ref": f"benchmark/samples/text/sample-{idx:03d}.txt",
        }
        for idx in range(1, 21)
    ]
    limits = {"smoke": {"ai_vs_human_detection": 7}}

    first = run_benchmark_module._select_profile_rows(
        rows,
        task="ai_vs_human_detection",
        profile="smoke",
        profile_limits=limits,
        commit_sha="abc123",
    )
    second = run_benchmark_module._select_profile_rows(
        rows,
        task="ai_vs_human_detection",
        profile="smoke",
        profile_limits=limits,
        commit_sha="abc123",
    )

    assert len(first) == 7
    assert first == second


def test_select_profile_rows_unknown_profile_raises() -> None:
    rows = [{"sample_id": "sample-001"}]
    with pytest.raises(ValueError, match="Unknown benchmark profile"):
        run_benchmark_module._select_profile_rows(
            rows,
            task="ai_vs_human_detection",
            profile="unknown_profile",
            profile_limits={"smoke": {"ai_vs_human_detection": 1}},
            commit_sha="abc123",
        )


def test_dataset_health_unknown_target_profile_fails(tmp_path: Path) -> None:
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir(parents=True, exist_ok=True)
    (datasets_dir / "detection_multidomain.jsonl").write_text("", encoding="utf-8")
    targets = tmp_path / "targets.yaml"
    targets.write_text(
        json.dumps(
            {
                "targets": {
                    "smoke_v2": {
                        "target_total": 1,
                        "warn_total": 1,
                        "task_targets": {"ai_vs_human_detection": 1},
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(DATASET_HEALTH_PATH),
            "--datasets-dir",
            str(datasets_dir),
            "--targets-config",
            str(targets),
            "--target-profile",
            "full_v2",
            "--output-json",
            str(tmp_path / "health.json"),
            "--output-md",
            str(tmp_path / "health.md"),
            "--enforce",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Unknown target profile" in (result.stdout + result.stderr)


def test_dataset_health_full_profile_enforce_fails_when_below_target(tmp_path: Path) -> None:
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir(parents=True, exist_ok=True)
    row = {
        "sample_id": "det-001",
        "task": "ai_vs_human_detection",
        "domain": "news",
        "label_is_ai": 1,
        "modality": "text",
        "input_ref": "benchmark/samples/text/detection/det-001.txt",
    }
    (datasets_dir / "detection_multidomain.jsonl").write_text(
        json.dumps(row) + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(DATASET_HEALTH_PATH),
            "--datasets-dir",
            str(datasets_dir),
            "--targets-config",
            str(REPO_ROOT / "benchmark" / "config" / "benchmark_targets.yaml"),
            "--target-profile",
            "full_v2",
            "--output-json",
            str(tmp_path / "health_full.json"),
            "--output-md",
            str(tmp_path / "health_full.md"),
            "--enforce",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads((tmp_path / "health_full.json").read_text(encoding="utf-8"))
    assert payload["status"] == "needs_attention"


def test_dataset_health_smoke_profile_reports_without_enforce(tmp_path: Path) -> None:
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir(parents=True, exist_ok=True)
    row = {
        "sample_id": "det-001",
        "task": "ai_vs_human_detection",
        "domain": "news",
        "label_is_ai": 1,
        "modality": "text",
        "input_ref": "benchmark/samples/text/detection/det-001.txt",
    }
    (datasets_dir / "detection_multidomain.jsonl").write_text(
        json.dumps(row) + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(DATASET_HEALTH_PATH),
            "--datasets-dir",
            str(datasets_dir),
            "--targets-config",
            str(REPO_ROOT / "benchmark" / "config" / "benchmark_targets.yaml"),
            "--target-profile",
            "smoke_v2",
            "--output-json",
            str(tmp_path / "health_smoke.json"),
            "--output-md",
            str(tmp_path / "health_smoke.md"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads((tmp_path / "health_smoke.json").read_text(encoding="utf-8"))
    assert payload["targets"]["target_profile"] == "smoke_v2"

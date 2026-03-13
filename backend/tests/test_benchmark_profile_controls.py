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
REGRESSION_CHECK_PATH = REPO_ROOT / "benchmark" / "eval" / "check_benchmark_regression.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


run_benchmark_module = _load_module(RUN_BENCHMARK_PATH, "run_public_benchmark_test")
dataset_health_module = _load_module(DATASET_HEALTH_PATH, "dataset_health_test")
regression_check_module = _load_module(REGRESSION_CHECK_PATH, "benchmark_regression_test")


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
    )
    second = run_benchmark_module._select_profile_rows(
        rows,
        task="ai_vs_human_detection",
        profile="smoke",
        profile_limits=limits,
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
        )


def test_evaluate_detection_uses_text_rows_for_calibration_metrics() -> None:
    rows = [
        {
            "sample_id": "text-human",
            "task": "ai_vs_human_detection",
            "modality": "text",
            "domain": "code",
            "label_is_ai": 0,
            "status": "ok",
            "score": 0.001,
        },
        {
            "sample_id": "text-ai",
            "task": "ai_vs_human_detection",
            "modality": "text",
            "domain": "finance",
            "label_is_ai": 1,
            "status": "ok",
            "score": 0.999,
        },
        {
            "sample_id": "image-human",
            "task": "ai_vs_human_detection",
            "modality": "image",
            "domain": "legal",
            "label_is_ai": 0,
            "status": "ok",
            "score": 0.25,
        },
        {
            "sample_id": "image-ai",
            "task": "ai_vs_human_detection",
            "modality": "image",
            "domain": "science",
            "label_is_ai": 1,
            "status": "ok",
            "score": 0.487,
        },
    ]

    metrics = run_benchmark_module._evaluate_detection(rows, threshold=0.45)

    assert metrics["f1"] == 1.0
    assert metrics["calibration_scope"] == "text_only"
    assert metrics["calibration_samples"] == 2
    assert float(metrics["calibration_ece"]) < 0.01
    assert metrics["false_positive_rate_by_domain"] == {"code": 0.0}


def test_evaluate_tamper_uses_auc_ratio_when_clean_f1_is_zero() -> None:
    rows = []
    for transform, ai_score in (
        ("clean", 0.10),
        ("paraphrase", 0.20),
        ("translate", 0.19),
        ("human_edit", 0.18),
    ):
        rows.extend(
            [
                {
                    "sample_id": f"{transform}-human",
                    "task": "tamper_detection",
                    "modality": "text",
                    "domain": "general",
                    "transform": transform,
                    "label_is_ai": 0,
                    "status": "ok",
                    "score": 0.05,
                },
                {
                    "sample_id": f"{transform}-ai",
                    "task": "tamper_detection",
                    "modality": "text",
                    "domain": "general",
                    "transform": transform,
                    "label_is_ai": 1,
                    "status": "ok",
                    "score": ai_score,
                },
            ]
        )

    metrics = run_benchmark_module._evaluate_tamper(rows, threshold=0.45)

    assert metrics["clean_f1"] == 0.0
    assert metrics["robustness_basis"] == "roc_auc_ratio"
    assert metrics["robustness_score"] == 1.0


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


def test_dataset_health_full_v3_enforce_passes_with_metadata_threshold(tmp_path: Path) -> None:
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir(parents=True, exist_ok=True)
    row = {
        "sample_id": "det-v3-0001",
        "task": "ai_vs_human_detection",
        "domain": "code",
        "label_is_ai": 0,
        "modality": "text",
        "input_ref": "benchmark/samples/text/detection/det-t-006.txt",
        "data_origin": "v1_2_full_v3_expansion",
        "generator_id": "synthetic-rebalance-v12",
        "license_ref": "benchmark/data_statement.md#internal-benchmark-license-v1",
    }
    (datasets_dir / "detection_multidomain.jsonl").write_text(
        json.dumps(row) + "\n",
        encoding="utf-8",
    )

    targets = tmp_path / "targets_full_v3.json"
    targets.write_text(
        json.dumps(
            {
                "targets": {
                    "full_v3": {
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
            "full_v3",
            "--min-metadata-rows",
            "1",
            "--output-json",
            str(tmp_path / "health_full_v3.json"),
            "--output-md",
            str(tmp_path / "health_full_v3.md"),
            "--enforce",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads((tmp_path / "health_full_v3.json").read_text(encoding="utf-8"))
    assert payload["targets"]["target_profile"] == "full_v3"
    assert payload["summary"]["metadata_rows"] == 1
    assert payload["status"] == "healthy"


def test_dataset_health_fails_when_metadata_fields_missing(tmp_path: Path) -> None:
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir(parents=True, exist_ok=True)
    row = {
        "sample_id": "det-v3-0002",
        "task": "ai_vs_human_detection",
        "domain": "finance",
        "label_is_ai": 0,
        "modality": "text",
        "input_ref": "benchmark/samples/text/detection/det-t-010.txt",
        "data_origin": "v1_2_full_v3_expansion",
        "generator_id": "synthetic-rebalance-v12",
    }
    (datasets_dir / "detection_multidomain.jsonl").write_text(
        json.dumps(row) + "\n",
        encoding="utf-8",
    )

    targets = tmp_path / "targets_full_v3.json"
    targets.write_text(
        json.dumps(
            {
                "targets": {
                    "full_v3": {
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
            "full_v3",
            "--min-metadata-rows",
            "1",
            "--output-json",
            str(tmp_path / "health_missing_meta.json"),
            "--output-md",
            str(tmp_path / "health_missing_meta.md"),
            "--enforce",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads((tmp_path / "health_missing_meta.json").read_text(encoding="utf-8"))
    assert payload["status"] == "needs_attention"
    assert any("missing metadata fields" in item for item in payload["validation_issues"])


def test_regression_quality_targets_present_for_all_profiles() -> None:
    targets_path = REPO_ROOT / "benchmark" / "config" / "benchmark_targets.yaml"
    for profile in ("smoke_v2", "full_v2", "full_v3"):
        limits = regression_check_module._load_quality_limits(targets_path, profile)
        assert limits
        paths = {item["path"] for item in limits}
        assert "tasks.ai_vs_human_detection.calibration_ece" in paths
        assert "tasks.ai_vs_human_detection.false_positive_rate_by_domain.code" in paths
        assert "tasks.ai_vs_human_detection.false_positive_rate_by_domain.finance" in paths
        assert "tasks.ai_vs_human_detection.false_positive_rate_by_domain.legal" in paths
        assert "tasks.ai_vs_human_detection.false_positive_rate_by_domain.science" in paths


def test_regression_quality_limits_fail_and_pass(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "metrics": [
                    {
                        "path": "tasks.ai_vs_human_detection.f1",
                        "baseline": 0.7,
                        "max_drop": 0.3,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    targets_path = tmp_path / "targets.json"
    targets_path.write_text(
        json.dumps(
            {
                "targets": {
                    "smoke_v2": {
                        "target_total": 1,
                        "warn_total": 1,
                        "task_targets": {"ai_vs_human_detection": 1},
                        "quality_targets": {
                            "ai_vs_human_detection": {
                                "calibration_ece_max": 0.08,
                                "false_positive_rate_by_domain_max": {
                                    "code": 0.30,
                                    "finance": 0.30,
                                    "legal": 0.30,
                                    "science": 0.30,
                                },
                            }
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    failing_current = tmp_path / "current_fail.json"
    failing_current.write_text(
        json.dumps(
            {
                "tasks": {
                    "ai_vs_human_detection": {
                        "f1": 0.75,
                        "calibration_ece": 0.11,
                        "false_positive_rate_by_domain": {
                            "code": 0.31,
                            "finance": 0.29,
                            "legal": 0.29,
                            "science": 0.29,
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    fail_result = subprocess.run(
        [
            sys.executable,
            str(REGRESSION_CHECK_PATH),
            "--current",
            str(failing_current),
            "--baseline",
            str(baseline_path),
            "--targets-config",
            str(targets_path),
            "--target-profile",
            "smoke_v2",
            "--report-json",
            str(tmp_path / "reg_fail.json"),
            "--report-md",
            str(tmp_path / "reg_fail.md"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert fail_result.returncode == 1

    passing_current = tmp_path / "current_pass.json"
    passing_current.write_text(
        json.dumps(
            {
                "tasks": {
                    "ai_vs_human_detection": {
                        "f1": 0.75,
                        "calibration_ece": 0.03,
                        "false_positive_rate_by_domain": {
                            "code": 0.2,
                            "finance": 0.2,
                            "legal": 0.2,
                            "science": 0.2,
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    pass_result = subprocess.run(
        [
            sys.executable,
            str(REGRESSION_CHECK_PATH),
            "--current",
            str(passing_current),
            "--baseline",
            str(baseline_path),
            "--targets-config",
            str(targets_path),
            "--target-profile",
            "smoke_v2",
            "--report-json",
            str(tmp_path / "reg_pass.json"),
            "--report-md",
            str(tmp_path / "reg_pass.md"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert pass_result.returncode == 0

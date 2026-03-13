from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PARITY_REPORT_SCRIPT = REPO_ROOT / "benchmark" / "eval" / "build_public_parity_report.py"


def _write_benchmark_results(path: Path, *, model_id: str, profile: str = "full_v3") -> None:
    payload = {
        "generated_at": "2026-03-13T10:00:00+00:00",
        "profile": profile,
        "run_metadata": {"model_id": model_id},
        "tasks": {
            "ai_vs_human_detection": {
                "f1": 0.82,
                "roc_auc": 0.99,
                "calibration_ece": 0.01,
                "false_positive_rate_by_domain": {
                    "code": 0.02,
                    "finance": 0.01,
                    "legal": 0.02,
                    "science": 0.03,
                },
            },
            "source_attribution": {"accuracy": 0.81},
            "tamper_detection": {"robustness_score": 0.92},
            "audio_ai_vs_human_detection": {"f1": 0.95},
            "video_ai_vs_human_detection": {"f1": 0.96},
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_public_parity_report_rank_and_deltas(tmp_path: Path) -> None:
    benchmark_results = tmp_path / "benchmark_results.json"
    leaderboard = tmp_path / "leaderboard.json"
    output_json = tmp_path / "public_parity_report.json"
    output_md = tmp_path / "public_parity_report.md"

    _write_benchmark_results(benchmark_results, model_id="current-model")
    leaderboard.write_text(
        json.dumps(
            {
                "updated_at": "2026-03-13T10:00:00+00:00",
                "entries": [
                    {
                        "rank": 1,
                        "model_id": "current-model",
                        "overall_score": 0.9012,
                        "text_calibration_ece": 0.01,
                        "text_domain_fp_max": 0.03,
                        "benchmark_profile": "full_v3",
                    },
                    {
                        "rank": 2,
                        "model_id": "baseline-model",
                        "overall_score": 0.8541,
                        "text_calibration_ece": 0.04,
                        "text_domain_fp_max": 0.19,
                        "benchmark_profile": "full_v3",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(PARITY_REPORT_SCRIPT),
            "--benchmark-results",
            str(benchmark_results),
            "--leaderboard",
            str(leaderboard),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["current_model"]["rank"] == 1
    assert report["reference_model"]["model_id"] == "baseline-model"
    assert report["deltas"]["overall_score"] == 0.0471
    assert report["deltas"]["text_calibration_ece"] == -0.03
    assert report["deltas"]["text_domain_fp_max"] == -0.16
    assert report["position_summary"]["overall_score"] == "ahead"
    assert report["position_summary"]["text_calibration_ece"] == "better"
    assert report["position_summary"]["text_domain_fp_max"] == "better"
    assert output_md.exists()


def test_public_parity_report_missing_optional_reference_fields(tmp_path: Path) -> None:
    benchmark_results = tmp_path / "benchmark_results.json"
    leaderboard = tmp_path / "leaderboard.json"
    output_json = tmp_path / "public_parity_report.json"
    output_md = tmp_path / "public_parity_report.md"

    _write_benchmark_results(benchmark_results, model_id="current-model")
    leaderboard.write_text(
        json.dumps(
            {
                "updated_at": "2026-03-13T10:00:00+00:00",
                "entries": [
                    {
                        "rank": 1,
                        "model_id": "current-model",
                        "overall_score": 0.9012,
                        "text_calibration_ece": 0.01,
                        "text_domain_fp_max": 0.03,
                        "benchmark_profile": "full_v3",
                    },
                    {
                        "rank": 2,
                        "model_id": "legacy-model",
                        "overall_score": 0.8844,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(PARITY_REPORT_SCRIPT),
            "--benchmark-results",
            str(benchmark_results),
            "--leaderboard",
            str(leaderboard),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["reference_model"]["model_id"] == "legacy-model"
    assert report["reference_model"]["benchmark_profile"] == "legacy"
    assert report["deltas"]["overall_score"] == 0.0168
    assert report["deltas"]["text_calibration_ece"] is None
    assert report["deltas"]["text_domain_fp_max"] is None
    assert report["position_summary"]["text_calibration_ece"] == "insufficient_reference"
    assert report["position_summary"]["text_domain_fp_max"] == "insufficient_reference"
    assert output_md.exists()

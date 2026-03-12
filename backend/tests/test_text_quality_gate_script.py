from __future__ import annotations

import importlib.util
import json
import types
from pathlib import Path


def _load_script_module(script_name: str) -> types.ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(script_name.replace('.py', ''), script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_quality_gate_passes(tmp_path: Path) -> None:
    module = _load_script_module("check_text_quality_gate.py")
    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "sample_count": 220,
                "ece": 0.04,
                "recommended_uncertainty_margin": 0.08,
                "best_metrics": {"fp_rate": 0.03},
            }
        ),
        encoding="utf-8",
    )

    output_json = tmp_path / "gate.json"
    output_md = tmp_path / "gate.md"

    import sys

    original = sys.argv
    sys.argv = [
        "check_text_quality_gate.py",
        "--report",
        str(report_path),
        "--output-json",
        str(output_json),
        "--output-md",
        str(output_md),
    ]
    try:
        rc = module.run()
    finally:
        sys.argv = original

    assert rc == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"


def test_quality_gate_fails_on_fp_and_ece(tmp_path: Path) -> None:
    module = _load_script_module("check_text_quality_gate.py")
    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "sample_count": 90,
                "ece": 0.21,
                "recommended_uncertainty_margin": 0.19,
                "best_metrics": {"fp_rate": 0.12},
            }
        ),
        encoding="utf-8",
    )

    output_json = tmp_path / "gate.json"
    output_md = tmp_path / "gate.md"

    import sys

    original = sys.argv
    sys.argv = [
        "check_text_quality_gate.py",
        "--report",
        str(report_path),
        "--output-json",
        str(output_json),
        "--output-md",
        str(output_md),
    ]
    try:
        rc = module.run()
    finally:
        sys.argv = original

    assert rc == 1
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["status"] == "fail"
    assert len(payload["failures"]) >= 3

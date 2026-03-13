from __future__ import annotations

import importlib.util
import json
import types
from pathlib import Path


def _load_script_module(script_name: str) -> types.ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(script_name.replace(".py", ""), script_path)
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


def test_quality_gate_domain_fp_passes_under_threshold(tmp_path: Path) -> None:
    module = _load_script_module("check_text_quality_gate.py")
    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "sample_count": 220,
                "ece": 0.02,
                "recommended_uncertainty_margin": 0.07,
                "best_metrics": {"fp_rate": 0.02},
                "false_positive_rate_by_domain": {
                    "code": 0.2,
                    "finance": 0.29,
                    "legal": 0.28,
                    "science": 0.18,
                },
                "domain_sample_count_by_domain": {
                    "code": 40,
                    "finance": 42,
                    "legal": 38,
                    "science": 36,
                },
            }
        ),
        encoding="utf-8",
    )

    output_json = tmp_path / "gate_domain_pass.json"
    output_md = tmp_path / "gate_domain_pass.md"

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
        "--max-domain-fp-rate",
        "0.30",
        "--min-domain-sample-count",
        "30",
    ]
    try:
        rc = module.run()
    finally:
        sys.argv = original

    assert rc == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert all(item["status"] == "pass" for item in payload["domain_checks"])


def test_quality_gate_domain_fp_fails_on_single_domain(tmp_path: Path) -> None:
    module = _load_script_module("check_text_quality_gate.py")
    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "sample_count": 220,
                "ece": 0.03,
                "recommended_uncertainty_margin": 0.09,
                "best_metrics": {"fp_rate": 0.03},
                "false_positive_rate_by_domain": {
                    "code": 0.31,
                    "finance": 0.2,
                    "legal": 0.2,
                    "science": 0.2,
                },
                "domain_sample_count_by_domain": {
                    "code": 40,
                    "finance": 40,
                    "legal": 40,
                    "science": 40,
                },
            }
        ),
        encoding="utf-8",
    )

    output_json = tmp_path / "gate_domain_fail.json"
    output_md = tmp_path / "gate_domain_fail.md"

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
        "--max-domain-fp-rate",
        "0.30",
        "--min-domain-sample-count",
        "30",
    ]
    try:
        rc = module.run()
    finally:
        sys.argv = original

    assert rc == 1
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["status"] == "fail"
    assert any("domain[code]" in failure for failure in payload["failures"])
    failed = [item for item in payload["domain_checks"] if item["status"] == "fail"]
    assert len(failed) == 1
    assert failed[0]["domain"] == "code"


def test_quality_gate_domain_fp_skips_low_sample_domains(tmp_path: Path) -> None:
    module = _load_script_module("check_text_quality_gate.py")
    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "sample_count": 220,
                "ece": 0.03,
                "recommended_uncertainty_margin": 0.09,
                "best_metrics": {"fp_rate": 0.03},
                "false_positive_rate_by_domain": {
                    "code": 0.9,
                    "finance": 0.9,
                    "legal": 0.9,
                    "science": 0.9,
                },
                "domain_sample_count_by_domain": {
                    "code": 12,
                    "finance": 14,
                    "legal": 8,
                    "science": 10,
                },
            }
        ),
        encoding="utf-8",
    )

    output_json = tmp_path / "gate_domain_skip.json"
    output_md = tmp_path / "gate_domain_skip.md"

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
        "--max-domain-fp-rate",
        "0.30",
        "--min-domain-sample-count",
        "30",
    ]
    try:
        rc = module.run()
    finally:
        sys.argv = original

    assert rc == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert all(item["status"] == "skipped" for item in payload["domain_checks"])
    assert all("minimum" in item["reason"] for item in payload["domain_checks"])

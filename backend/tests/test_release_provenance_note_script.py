from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate_release_provenance_note.py"


@pytest.fixture(autouse=True)
def _reset_runtime_state():
    """Override global async DB fixture for pure script-level tests."""
    yield


def test_release_provenance_note_generation(tmp_path: Path) -> None:
    trivy_report = tmp_path / "trivy.json"
    out_json = tmp_path / "release-note.json"
    out_md = tmp_path / "release-note.md"

    trivy_report.write_text(
        json.dumps(
            {
                "Results": [
                    {
                        "Vulnerabilities": [
                            {"Severity": "CRITICAL"},
                            {"Severity": "HIGH"},
                            {"Severity": "HIGH"},
                        ]
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--component",
            "api",
            "--image-ref",
            "ghcr.io/example/provenance-api:sha",
            "--image-digest",
            "sha256:abc123",
            "--trivy-report",
            str(trivy_report),
            "--sbom-artifact",
            "sbom-api-sha.spdx.json",
            "--output-json",
            str(out_json),
            "--output-md",
            str(out_md),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["component"] == "api"
    assert payload["vulnerability_summary"]["critical"] == 1
    assert payload["vulnerability_summary"]["high"] == 2
    assert out_md.exists()

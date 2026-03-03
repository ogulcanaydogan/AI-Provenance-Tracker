from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_package_policy.py"


@pytest.fixture(autouse=True)
def _reset_runtime_state():
    """Override global async DB fixture for pure script-level tests."""
    yield


def test_package_policy_fails_on_disallowed_npm_host(tmp_path: Path) -> None:
    policy = tmp_path / "package_policy.yaml"
    npm_lock = tmp_path / "package-lock.json"
    requirements = tmp_path / "requirements.txt"
    output_json = tmp_path / "report.json"
    output_md = tmp_path / "report.md"

    policy.write_text(
        json.dumps(
            {
                "policy_version": "policy-test",
                "allowed_npm_registry_hosts": ["registry.npmjs.org"],
                "allowed_pip_hosts": ["pypi.org", "files.pythonhosted.org"],
                "blocked_package_patterns": [],
            }
        ),
        encoding="utf-8",
    )
    npm_lock.write_text(
        json.dumps(
            {
                "name": "demo",
                "lockfileVersion": 3,
                "packages": {
                    "": {},
                    "node_modules/bad-pkg": {
                        "version": "1.0.0",
                        "resolved": "https://evil.example.com/bad-pkg-1.0.0.tgz",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    requirements.write_text("fastapi>=0.110.0\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--policy-file",
            str(policy),
            "--npm-lock",
            str(npm_lock),
            "--requirements",
            str(requirements),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["status"] == "fail"
    assert payload["summary"]["violation_count"] >= 1

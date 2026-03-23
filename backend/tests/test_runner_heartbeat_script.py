from __future__ import annotations

import importlib.util
import io
import sys
import types
import urllib.error
from pathlib import Path

import pytest


def _load_script_module() -> types.ModuleType:
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "check_runner_heartbeat.py"
    spec = importlib.util.spec_from_file_location("check_runner_heartbeat", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_prefers_gh_token_over_github_token(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_script_module()
    tokens_seen: list[str] = []

    def _fake_fetch(_repo: str, token: str) -> list[dict]:
        tokens_seen.append(token)
        return [
            {
                "name": "spark-runtime-01",
                "status": "online",
                "labels": [
                    {"name": "self-hosted"},
                    {"name": "linux"},
                    {"name": "spark-runtime"},
                ],
            }
        ]

    monkeypatch.setattr(module, "_fetch_runners", _fake_fetch)
    monkeypatch.setenv("GH_TOKEN", "preferred-token")
    monkeypatch.setenv("GITHUB_TOKEN", "fallback-token")
    monkeypatch.setattr(
        sys, "argv", ["check_runner_heartbeat.py", "--repo", "owner/repo", "--checks", "1"]
    )

    assert module.main() == 0
    assert tokens_seen == ["preferred-token"]


def test_http_403_has_clear_remediation(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_script_module()
    payload = io.BytesIO(b'{"message":"Resource not accessible by integration"}')

    def _fake_urlopen(*_args: object, **_kwargs: object) -> object:
        raise urllib.error.HTTPError(
            url="https://api.github.com/repos/owner/repo/actions/runners",
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=payload,
        )

    monkeypatch.setattr(module.urllib.request, "urlopen", _fake_urlopen)

    with pytest.raises(SystemExit, match="RUNNER_HEARTBEAT_TOKEN"):
        module._fetch_runners("owner/repo", "token")


def test_runner_label_and_status_gate_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_script_module()

    def _fake_fetch(_repo: str, _token: str) -> list[dict]:
        return [
            {
                "name": "spark-runtime-01",
                "status": "online",
                "labels": [
                    {"name": "Self-Hosted"},
                    {"name": "LINUX"},
                    {"name": "spark-runtime"},
                ],
            }
        ]

    monkeypatch.setattr(module, "_fetch_runners", _fake_fetch)
    monkeypatch.setenv("GH_TOKEN", "token")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_runner_heartbeat.py",
            "--repo",
            "owner/repo",
            "--checks",
            "1",
            "--required-labels",
            "self-hosted,linux,spark-runtime",
        ],
    )

    assert module.main() == 0

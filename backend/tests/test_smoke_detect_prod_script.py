from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest


def _load_script_module() -> types.ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "smoke_detect_prod.py"
    spec = importlib.util.spec_from_file_location("smoke_detect_prod", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _DummyClient:
    def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003, D107
        _ = args, kwargs

    def __enter__(self):  # noqa: D105
        return self

    def __exit__(self, exc_type, exc, tb):  # noqa: D105, ANN001
        _ = exc_type, exc, tb
        return False


def _run_script(module: types.ModuleType, argv: list[str]) -> int:
    original_argv = sys.argv
    sys.argv = argv
    try:
        return module.run()
    finally:
        sys.argv = original_argv


def test_smoke_script_passes_with_health_and_detect_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_script_module()
    monkeypatch.setattr(module.httpx, "Client", _DummyClient)

    responses = iter(
        [
            (200, {"status": "ok"}, "", 5.0),
            (200, {"analysis_id": "a1", "confidence": 0.92, "analysis": {}}, "", 11.0),
            (
                200,
                {"analysis_id": "a2", "confidence": 0.90, "analysis": {}, "dimensions": [48, 48]},
                "",
                12.0,
            ),
            (
                200,
                {"analysis_id": "a3", "confidence": 0.88, "analysis": {}, "filename": "smoke.wav"},
                "",
                13.0,
            ),
            (
                200,
                {"analysis_id": "a4", "confidence": 0.86, "analysis": {}, "filename": "smoke.mp4"},
                "",
                14.0,
            ),
        ]
    )
    monkeypatch.setattr(module, "_request_json", lambda *args, **kwargs: next(responses))

    output_path = tmp_path / "smoke_success.json"
    rc = _run_script(
        module,
        [
            "smoke_detect_prod.py",
            "--base-url",
            "https://example.test",
            "--output",
            str(output_path),
        ],
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert rc == 0
    assert payload["health_probe"]["ok"] is True
    assert payload["checks_passed"] == 4
    assert payload["checks_failed"] == 0
    assert payload["root_cause_hint"] is None
    assert payload["overall_ok"] is True


def test_smoke_script_marks_route_mismatch_when_all_detect_endpoints_return_404(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_script_module()
    monkeypatch.setattr(module.httpx, "Client", _DummyClient)

    responses = iter(
        [
            (200, {"status": "ok"}, "", 4.0),
            (404, {"detail": "Not Found"}, "", 10.0),
            (404, {"detail": "Not Found"}, "", 11.0),
            (404, {"detail": "Not Found"}, "", 12.0),
            (404, {"detail": "Not Found"}, "", 13.0),
        ]
    )
    monkeypatch.setattr(module, "_request_json", lambda *args, **kwargs: next(responses))

    output_path = tmp_path / "smoke_route_mismatch.json"
    rc = _run_script(
        module,
        [
            "smoke_detect_prod.py",
            "--base-url",
            "https://wrong.example.test",
            "--output",
            str(output_path),
        ],
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert rc == 1
    assert payload["checks_failed"] == 4
    assert payload["root_cause_hint"] == "base_url_route_mismatch"
    assert payload["overall_ok"] is False


def test_smoke_script_reports_partial_failures_correctly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_script_module()
    monkeypatch.setattr(module.httpx, "Client", _DummyClient)

    responses = iter(
        [
            (200, {"status": "ok"}, "", 6.0),
            (200, {"analysis_id": "a1", "confidence": 0.92, "analysis": {}}, "", 11.0),
            (500, None, "internal error", 12.0),
            (
                200,
                {"analysis_id": "a3", "confidence": 0.88, "analysis": {}, "filename": "smoke.wav"},
                "",
                13.0,
            ),
            (
                200,
                {"analysis_id": "a4", "confidence": 0.86, "analysis": {}, "filename": "smoke.mp4"},
                "",
                14.0,
            ),
        ]
    )
    monkeypatch.setattr(module, "_request_json", lambda *args, **kwargs: next(responses))

    output_path = tmp_path / "smoke_partial.json"
    rc = _run_script(
        module,
        [
            "smoke_detect_prod.py",
            "--base-url",
            "https://partial.example.test",
            "--output",
            str(output_path),
        ],
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert rc == 1
    assert payload["checks_passed"] == 3
    assert payload["checks_failed"] == 1
    assert payload["root_cause_hint"] is None
    assert payload["overall_ok"] is False

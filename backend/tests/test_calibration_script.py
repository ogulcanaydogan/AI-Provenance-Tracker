from __future__ import annotations

import json
import importlib.util
import sys
import types
from pathlib import Path

import pytest


def _load_script_module() -> types.ModuleType:
    script_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "evaluate_detection_calibration.py"
    )
    spec = importlib.util.spec_from_file_location("evaluate_detection_calibration", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _DummyMediaDetector:
    async def detect(self, _payload: bytes, _filename: str):  # noqa: ANN001
        return types.SimpleNamespace(
            confidence=0.81,
            model_version="media-detector:dummy",
            calibration_version="calibration:dummy",
        )


class _DummyTextDetector:
    def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003, D107
        _ = args, kwargs

    async def detect(self, _text: str, domain: str | None = None):  # noqa: ANN001
        _ = domain
        return types.SimpleNamespace(
            confidence=0.22,
            model_version="text-detector:dummy",
            calibration_version="calibration:dummy",
        )


@pytest.mark.asyncio
async def test_score_samples_audio_supported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_script_module()
    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"RIFF0000WAVEfmt ")

    monkeypatch.setattr(module, "AudioDetector", _DummyMediaDetector)
    scores, skipped = await module._score_samples(
        [{"audio_path": str(audio_path), "label_is_ai": True}],
        "audio",
    )

    assert scores == [(0.81, True)]
    assert skipped == 0


@pytest.mark.asyncio
async def test_score_samples_video_supported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_script_module()
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"\x00\x00\x00\x18ftypmp42")

    monkeypatch.setattr(module, "VideoDetector", _DummyMediaDetector)
    scores, skipped = await module._score_samples(
        [{"video_path": str(video_path), "label_is_ai": False}],
        "video",
    )

    assert scores == [(0.81, False)]
    assert skipped == 0


@pytest.mark.asyncio
async def test_score_samples_counts_missing_media_as_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script_module()
    monkeypatch.setattr(module, "AudioDetector", _DummyMediaDetector)

    scores, skipped = await module._score_samples(
        [{"audio_path": "/tmp/does-not-exist.wav", "label_is_ai": True}],
        "audio",
    )

    assert scores == []
    assert skipped == 1


@pytest.mark.asyncio
async def test_score_samples_text_from_input_ref(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_script_module()
    sample_path = tmp_path / "sample.txt"
    sample_path.write_text("This text fixture is used for calibration scoring.", encoding="utf-8")

    monkeypatch.setattr(module, "TextDetector", _DummyTextDetector)
    scores, skipped = await module._score_samples(
        [{"input_ref": str(sample_path), "label_is_ai": False}],
        "text",
    )

    assert scores == [(0.22, False)]
    assert skipped == 0


@pytest.mark.asyncio
async def test_score_text_samples_by_domain_normalizes_labels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_script_module()
    sample_path = tmp_path / "sample.txt"
    sample_path.write_text(
        "This text fixture is used for per-domain calibration scoring.", encoding="utf-8"
    )

    monkeypatch.setattr(module, "TextDetector", _DummyTextDetector)
    domain_scores, skipped = await module._score_text_samples_by_domain(
        [
            {"input_ref": str(sample_path), "label_is_ai": False, "domain": "science"},
            {"input_ref": str(sample_path), "label_is_ai": True, "domain": "code"},
        ]
    )

    assert skipped == 0
    assert set(domain_scores.keys()) == {"academic", "code-doc"}
    assert domain_scores["academic"] == [(0.22, False)]
    assert domain_scores["code-doc"] == [(0.22, True)]


def test_calibration_error_metrics_in_expected_range() -> None:
    module = _load_script_module()
    metrics = module._calibration_error_metrics(
        [
            (0.9, True),
            (0.8, True),
            (0.2, False),
            (0.1, False),
        ]
    )
    assert 0 <= metrics["ece"] <= 1
    assert 0 <= metrics["brier_score"] <= 1


def test_platt_scaler_reduces_calibration_error() -> None:
    module = _load_script_module()
    raw_scores = [
        (0.4, False),
        (0.4, False),
        (0.4, False),
        (0.6, True),
        (0.6, True),
        (0.6, True),
    ]
    calibration_map = module._fit_platt_scaler(raw_scores)
    assert calibration_map is not None
    assert calibration_map["type"] == "platt"

    calibrated_scores = module._apply_calibration_to_scores(raw_scores, calibration_map)
    raw_metrics = module._calibration_error_metrics(raw_scores)
    calibrated_metrics = module._calibration_error_metrics(calibrated_scores)

    assert calibrated_metrics["ece"] < raw_metrics["ece"]
    assert calibrated_metrics["brier_score"] < raw_metrics["brier_score"]


@pytest.mark.asyncio
async def test_run_writes_calibration_map_and_versions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_script_module()

    input_path = tmp_path / "samples.jsonl"
    input_path.write_text(
        "\n".join(
            [
                json.dumps({"modality": "text", "label_is_ai": False}),
                json.dumps({"modality": "text", "label_is_ai": True}),
                json.dumps({"modality": "text", "label_is_ai": False}),
                json.dumps({"modality": "text", "label_is_ai": True}),
            ]
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "report.json"
    profile_path = tmp_path / "profile.json"

    async def _fake_scores(_samples: list[dict[str, object]], _content_type: str):
        return (
            [(0.41, False), (0.42, False), (0.58, True), (0.59, True)],
            0,
            {"model_version": "text-detector:test", "calibration_version": "cal:test"},
        )

    monkeypatch.setattr(module, "_score_samples_with_metadata", _fake_scores)

    original_argv = sys.argv
    sys.argv = [
        "evaluate_detection_calibration.py",
        "--input",
        str(input_path),
        "--content-type",
        "text",
        "--output",
        str(output_path),
        "--write-profile",
        "--profile-output",
        str(profile_path),
        "--min-samples",
        "4",
    ]
    try:
        rc = await module.run()
    finally:
        sys.argv = original_argv

    assert rc == 0
    report = json.loads(output_path.read_text(encoding="utf-8"))
    profile = json.loads(profile_path.read_text(encoding="utf-8"))

    assert report["model_version"] == "text-detector:test"
    assert report["calibration_version"] == "cal:test"
    assert report["calibration_map"]["type"] == "platt"
    assert profile["calibration_map"]["type"] == "platt"

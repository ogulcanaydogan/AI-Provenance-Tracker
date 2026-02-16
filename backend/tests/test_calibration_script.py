from __future__ import annotations

import importlib.util
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
        return types.SimpleNamespace(confidence=0.81)


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

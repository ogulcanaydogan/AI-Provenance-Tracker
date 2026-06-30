"""Tests for the `provenance` command-line interface (app.cli).

These run fully offline: text detection uses the heuristic path (no [ml] extra
installed in CI) and audio uses an in-memory synthetic WAV. Exit-code logic is
exercised deterministically by stubbing the detector call.
"""

from __future__ import annotations

import io
import json
import struct
import wave

import pytest

from app import cli

# --- pure helpers (deterministic) -------------------------------------------


def test_modality_for_path_by_extension(tmp_path):
    assert cli._modality_for_path(tmp_path / "a.PNG") == "image"
    assert cli._modality_for_path(tmp_path / "a.wav") == "audio"
    assert cli._modality_for_path(tmp_path / "a.mp4") == "video"
    assert cli._modality_for_path(tmp_path / "a.txt") == "text"
    assert cli._modality_for_path(tmp_path / "noext") == "text"


def test_modality_for_content_type():
    assert cli._modality_for_content_type("image/png") == "image"
    assert cli._modality_for_content_type("audio/wav") == "audio"
    assert cli._modality_for_content_type("video/mp4; codecs=x") == "video"
    assert cli._modality_for_content_type("text/html; charset=utf-8") == "text"
    assert cli._modality_for_content_type("application/json") == "text"


def test_strip_html_removes_tags_and_scripts():
    html = "<html><head><style>x{}</style></head><body><p>Hello</p><script>1</script>world</body></html>"
    assert cli._strip_html(html) == "Hello world"


@pytest.mark.parametrize(
    "data,label,is_ai",
    [
        ({"decision_band": "ai", "is_ai_generated": True}, "AI-generated", True),
        ({"decision_band": "human", "is_ai_generated": False}, "Human-written", False),
        ({"decision_band": "uncertain", "is_ai_generated": True}, "Uncertain", False),
        (
            {"is_ai_generated": True},
            "AI-generated",
            True,
        ),  # no band (image/audio/video)
        ({"is_ai_generated": False}, "Human-written", False),
    ],
)
def test_verdict(data, label, is_ai):
    assert cli._verdict(data) == (label, is_ai)


# --- integration through run() ----------------------------------------------


def test_detect_text_pretty(capsys):
    code = cli.run(["detect", "--text", "The quick brown fox jumps over the lazy dog."])
    out = capsys.readouterr().out
    assert code == 0
    assert "AI Provenance Tracker - text" in out
    assert "Verdict:" in out
    assert "Analysis:" in out


def test_detect_text_json_is_machine_readable(capsys):
    code = cli.run(["detect", "--text", "Some sample sentence for analysis.", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    payload = json.loads(out)
    assert "is_ai_generated" in payload
    assert "confidence" in payload
    assert "analysis" in payload


def test_detect_text_from_stdin(capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("piped in text for detection"))
    code = cli.run(["detect", "--text", "-", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    assert "confidence" in json.loads(out)


def test_empty_text_returns_error(capsys):
    code = cli.run(["detect", "--text", "   "])
    err = capsys.readouterr().err
    assert code == 2
    assert "error:" in err


def test_missing_file_returns_error(capsys, tmp_path):
    code = cli.run(["detect", "--file", str(tmp_path / "nope.png")])
    assert code == 2
    assert "file not found" in capsys.readouterr().err


def test_detect_audio_file(capsys, tmp_path):
    wav_path = tmp_path / "clip.wav"
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        frames = b"".join(struct.pack("<h", (i % 100) - 50) for i in range(16000))
        handle.writeframes(frames)
    wav_path.write_bytes(buffer.getvalue())

    code = cli.run(["detect", "--file", str(wav_path), "--json"])
    out = capsys.readouterr().out
    assert code == 0
    assert "confidence" in json.loads(out)


def test_fail_on_ai_exit_code(capsys, monkeypatch):
    async def fake_ai(text, domain):
        return {
            "decision_band": "ai",
            "is_ai_generated": True,
            "confidence": 0.9,
            "analysis": {},
        }

    monkeypatch.setattr(cli, "_detect_text", fake_ai)
    assert cli.run(["detect", "--text", "x", "--fail-on-ai"]) == 1
    # without the flag, an AI verdict still exits 0
    assert cli.run(["detect", "--text", "x"]) == 0


def test_fail_on_ai_passes_for_human(capsys, monkeypatch):
    async def fake_human(text, domain):
        return {
            "decision_band": "human",
            "is_ai_generated": False,
            "confidence": 0.1,
            "analysis": {},
        }

    monkeypatch.setattr(cli, "_detect_text", fake_human)
    assert cli.run(["detect", "--text", "x", "--fail-on-ai"]) == 0

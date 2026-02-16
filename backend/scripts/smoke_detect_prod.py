"""Run a production smoke test for text/image/audio/video detection endpoints."""

from __future__ import annotations

import argparse
import io
import json
import math
import struct
import time
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke test detection endpoints on a deployed API."
    )
    parser.add_argument(
        "--base-url", required=True, help="API base URL (for example https://api.example.com)"
    )
    parser.add_argument("--api-key", default="", help="Optional API key for protected deployments")
    parser.add_argument(
        "--api-key-header", default="X-API-Key", help="Header name used for API key auth"
    )
    parser.add_argument("--timeout", type=float, default=25.0, help="Request timeout in seconds")
    parser.add_argument("--output", default="", help="Optional JSON output path")
    return parser.parse_args()


def _create_test_png() -> bytes:
    image = Image.new("RGB", (48, 48), color=(120, 180, 230))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _create_test_wav(duration_seconds: float = 0.5, sample_rate: int = 16000) -> bytes:
    frame_count = int(duration_seconds * sample_rate)
    amplitude = 0.3
    frequency = 330.0

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        frames = bytearray()
        for index in range(frame_count):
            value = amplitude * math.sin(2.0 * math.pi * frequency * (index / sample_rate))
            frames.extend(struct.pack("<h", int(value * 32767)))
        wav_file.writeframes(bytes(frames))

    return buffer.getvalue()


def _create_test_mp4() -> bytes:
    header = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
    body = b"\x00\x00\x00\x08free" + b"videodata12345678" * 3500
    return header + body


def _request_json(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
    files: dict[str, tuple[str, bytes, str]] | None = None,
) -> tuple[int, dict[str, Any] | None, str, float]:
    started = time.perf_counter()
    try:
        response = client.request(method, path, json=json_body, files=files)
    except httpx.HTTPError as exc:
        latency_ms = (time.perf_counter() - started) * 1000
        return 0, None, f"request_error:{exc}", round(latency_ms, 2)
    latency_ms = (time.perf_counter() - started) * 1000
    parsed: dict[str, Any] | None
    parse_error = ""
    try:
        parsed = response.json()
    except ValueError:
        parsed = None
        parse_error = response.text[:400]
    return response.status_code, parsed, parse_error, round(latency_ms, 2)


def _check_required(payload: dict[str, Any] | None, required_keys: tuple[str, ...]) -> list[str]:
    if payload is None:
        return ["response_body_not_json"]
    missing = [key for key in required_keys if key not in payload]
    return [f"missing:{item}" for item in missing]


def run() -> int:
    args = parse_args()
    base_url = args.base_url.strip().rstrip("/")
    if not base_url:
        print("Base URL is required.")
        return 1

    headers = {"User-Agent": "AIProvenanceTracker-Smoke/0.1"}
    if args.api_key:
        headers[args.api_key_header] = args.api_key

    checks: list[dict[str, Any]] = []
    with httpx.Client(
        base_url=base_url, timeout=httpx.Timeout(args.timeout), headers=headers
    ) as client:
        text_status, text_json, text_parse_error, text_latency = _request_json(
            client,
            "POST",
            "/api/v1/detect/text",
            json_body={
                "text": (
                    "Smoke test content for AI provenance endpoint validation. "
                    "This should be long enough for detector processing."
                )
                * 4
            },
        )
        text_errors = []
        if text_status != 200:
            text_errors.append(f"http_status:{text_status}")
        text_errors.extend(_check_required(text_json, ("analysis_id", "confidence", "analysis")))
        checks.append(
            {
                "endpoint": "/api/v1/detect/text",
                "ok": len(text_errors) == 0,
                "status_code": text_status,
                "latency_ms": text_latency,
                "errors": text_errors,
                "parse_error": text_parse_error,
            }
        )

        image_status, image_json, image_parse_error, image_latency = _request_json(
            client,
            "POST",
            "/api/v1/detect/image",
            files={"file": ("smoke.png", _create_test_png(), "image/png")},
        )
        image_errors = []
        if image_status != 200:
            image_errors.append(f"http_status:{image_status}")
        image_errors.extend(
            _check_required(image_json, ("analysis_id", "confidence", "analysis", "dimensions"))
        )
        checks.append(
            {
                "endpoint": "/api/v1/detect/image",
                "ok": len(image_errors) == 0,
                "status_code": image_status,
                "latency_ms": image_latency,
                "errors": image_errors,
                "parse_error": image_parse_error,
            }
        )

        audio_status, audio_json, audio_parse_error, audio_latency = _request_json(
            client,
            "POST",
            "/api/v1/detect/audio",
            files={"file": ("smoke.wav", _create_test_wav(), "audio/wav")},
        )
        audio_errors = []
        if audio_status != 200:
            audio_errors.append(f"http_status:{audio_status}")
        audio_errors.extend(
            _check_required(audio_json, ("analysis_id", "confidence", "analysis", "filename"))
        )
        checks.append(
            {
                "endpoint": "/api/v1/detect/audio",
                "ok": len(audio_errors) == 0,
                "status_code": audio_status,
                "latency_ms": audio_latency,
                "errors": audio_errors,
                "parse_error": audio_parse_error,
            }
        )

        video_status, video_json, video_parse_error, video_latency = _request_json(
            client,
            "POST",
            "/api/v1/detect/video",
            files={"file": ("smoke.mp4", _create_test_mp4(), "video/mp4")},
        )
        video_errors = []
        if video_status != 200:
            video_errors.append(f"http_status:{video_status}")
        video_errors.extend(
            _check_required(video_json, ("analysis_id", "confidence", "analysis", "filename"))
        )
        checks.append(
            {
                "endpoint": "/api/v1/detect/video",
                "ok": len(video_errors) == 0,
                "status_code": video_status,
                "latency_ms": video_latency,
                "errors": video_errors,
                "parse_error": video_parse_error,
            }
        )

    successful = sum(1 for item in checks if item["ok"])
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "base_url": base_url,
        "checks_total": len(checks),
        "checks_passed": successful,
        "checks_failed": len(checks) - successful,
        "checks": checks,
    }

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote smoke report to {output_path}")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if successful == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(run())

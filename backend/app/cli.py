"""Command-line interface for AI Provenance Tracker.

Run content detection from the terminal without starting the API server. The
CLI calls the bare modality detectors directly, so it has no database, no
network (except ``--url``), and no provider-consensus side effects.

Examples
--------
    provenance detect --text "some text to analyze"
    echo "piped text" | provenance detect --text -
    provenance detect --file path/to/image.png
    provenance detect --url https://example.com/article
    provenance detect --text "..." --json          # machine-readable output
    provenance detect --file clip.wav --fail-on-ai  # exit 1 if AI-generated

Text detection runs on pure heuristics when the optional ``[ml]`` extra
(transformers + torch) is not installed, which keeps the CLI fully offline.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Optional

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
AUDIO_EXTENSIONS = {".wav"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}


def _modality_for_path(path: Path) -> str:
    """Infer the detection modality from a file extension (text by default)."""
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    return "text"


def _modality_for_content_type(content_type: str) -> str:
    """Map an HTTP content-type to a detection modality."""
    main = content_type.split(";", 1)[0].strip().lower()
    if main.startswith("image/"):
        return "image"
    if main.startswith("audio/"):
        return "audio"
    if main.startswith("video/"):
        return "video"
    return "text"


def _strip_html(raw: str) -> str:
    """Best-effort plain-text extraction from an HTML document."""
    import re

    without_scripts = re.sub(
        r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.DOTALL | re.IGNORECASE
    )
    text = re.sub(r"<[^>]+>", " ", without_scripts)
    text = re.sub(r"&[a-zA-Z#0-9]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


async def _detect_text(text: str, domain: Optional[str]) -> dict[str, Any]:
    from app.detection import TextDetector

    result = await TextDetector().detect(text, domain=domain)
    return result.model_dump(mode="json")


async def _detect_bytes(modality: str, data: bytes, filename: str) -> dict[str, Any]:
    from app.detection import AudioDetector, ImageDetector, VideoDetector

    detectors = {
        "image": ImageDetector,
        "audio": AudioDetector,
        "video": VideoDetector,
    }
    detector = detectors[modality]()
    result = await detector.detect(data, filename)
    return result.model_dump(mode="json")


def _fetch_url(url: str) -> tuple[str, bytes, str]:
    """Fetch a URL, returning (modality, body bytes, filename)."""
    import httpx

    with httpx.Client(follow_redirects=True, timeout=30.0) as client:
        response = client.get(url)
        response.raise_for_status()
    content_type = response.headers.get("content-type", "text/plain")
    modality = _modality_for_content_type(content_type)
    filename = Path(url.split("?", 1)[0]).name or "download"
    return modality, response.content, filename


def _verdict(data: dict[str, Any]) -> tuple[str, bool]:
    """Return a human verdict label and whether it is an AI-generated call."""
    band = data.get("decision_band")
    is_ai = bool(data.get("is_ai_generated"))
    if band == "ai" or (band is None and is_ai):
        return "AI-generated", True
    if band == "human" or (band is None and not is_ai):
        return "Human-written", False
    return "Uncertain", False


def _print_pretty(modality: str, data: dict[str, Any]) -> None:
    label, _ = _verdict(data)
    confidence = float(data.get("confidence", 0.0)) * 100.0
    print(f"AI Provenance Tracker - {modality}")
    print(f"Verdict: {label} (confidence {confidence:.1f}%)")
    reason = data.get("uncertainty_reason")
    if reason:
        print(f"Reason: {reason}")
    explanation = data.get("explanation")
    if explanation:
        print(f"\n{explanation}")
    analysis = data.get("analysis") or {}
    if isinstance(analysis, dict) and analysis:
        print("\nAnalysis:")
        for key, value in analysis.items():
            print(f"  {key}: {value}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="provenance",
        description="Detect AI-generated content from the terminal.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    detect = subparsers.add_parser(
        "detect", help="Run detection on text, a file, or a URL."
    )
    source = detect.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--text", metavar="TEXT", help='Text to analyze (use "-" to read stdin).'
    )
    source.add_argument(
        "--file", metavar="PATH", help="Path to an image, audio, video, or text file."
    )
    source.add_argument(
        "--url", metavar="URL", help="URL to fetch and analyze (requires network)."
    )
    detect.add_argument("--domain", help="Optional domain hint for text detection.")
    detect.add_argument(
        "--json", action="store_true", help="Emit the raw result as JSON."
    )
    detect.add_argument(
        "--fail-on-ai",
        action="store_true",
        help="Exit with status 1 when the verdict is AI-generated.",
    )
    return parser


def _resolve_input(args: argparse.Namespace) -> tuple[str, dict[str, Any]]:
    """Resolve CLI args to (modality, result dict)."""
    if args.text is not None:
        text = sys.stdin.read() if args.text == "-" else args.text
        if not text.strip():
            raise ValueError("no text provided")
        return "text", asyncio.run(_detect_text(text, args.domain))

    if args.file is not None:
        path = Path(args.file)
        if not path.is_file():
            raise FileNotFoundError(f"file not found: {path}")
        modality = _modality_for_path(path)
        if modality == "text":
            text = path.read_text(encoding="utf-8", errors="replace")
            if not text.strip():
                raise ValueError("file is empty")
            return "text", asyncio.run(_detect_text(text, args.domain))
        return modality, asyncio.run(
            _detect_bytes(modality, path.read_bytes(), path.name)
        )

    # args.url
    modality, body, filename = _fetch_url(args.url)
    if modality == "text":
        text = _strip_html(body.decode("utf-8", errors="replace"))
        if not text.strip():
            raise ValueError("no extractable text at URL")
        return "text", asyncio.run(_detect_text(text, args.domain))
    return modality, asyncio.run(_detect_bytes(modality, body, filename))


def run(argv: Optional[list[str]] = None) -> int:
    """Entry point usable from tests; returns a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        modality, data = _resolve_input(args)
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (
        Exception
    ) as exc:  # noqa: BLE001 - surface any detector/network error cleanly
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        _print_pretty(modality, data)

    _, is_ai = _verdict(data)
    if args.fail_on_ai and is_ai:
        return 1
    return 0


def main() -> None:
    """Console-script entry point."""
    raise SystemExit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()

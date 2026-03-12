"""Regression guard for text detector separation on curated human-vs-ai pairs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.detection.text.detector import TextDetector


def _load_pairs() -> list[dict[str, str]]:
    fixture_path = Path(__file__).parent / "fixtures" / "text_golden_pairs.jsonl"
    rows: list[dict[str, str]] = []
    for line in fixture_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


@pytest.mark.asyncio
async def test_golden_pairs_show_separation() -> None:
    detector = TextDetector()
    pairs = _load_pairs()
    separated = 0

    for pair in pairs:
        human_result = await detector.detect(pair["human_text"])
        ai_result = await detector.detect(pair["ai_text"])

        verdict_differs = human_result.decision_band != ai_result.decision_band
        confidence_gap = abs(human_result.confidence - ai_result.confidence)
        distance_gap = abs(human_result.distance_to_threshold - ai_result.distance_to_threshold)
        if verdict_differs or confidence_gap >= 0.08 or distance_gap >= 0.05:
            separated += 1

    ratio = separated / max(1, len(pairs))
    assert ratio >= 0.6, (
        f"Golden pair separation below threshold: {separated}/{len(pairs)} ({ratio:.2%})"
    )

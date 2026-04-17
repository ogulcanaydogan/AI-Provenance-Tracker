"""Optional text expert bundle loader.

Public core ships with conservative defaults. Private repos can override these
patterns by mounting a JSON bundle via settings.text_expert_bundle_path.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import settings


DEFAULT_TEXT_EXPERT_BUNDLE: dict[str, Any] = {
    "version": "public-baseline-v1",
    "domain_keywords": {
        "news": [
            "reported",
            "breaking",
            "official statement",
            "according to",
            "spokesperson",
            "witnesses",
            "press conference",
        ],
        "social-short": [
            "#",
            "@",
            "viral",
            "followers",
            "thread",
            "caption",
            "reel",
            "story",
            "dm",
        ],
        "code-doc": [
            "```",
            "def ",
            "class ",
            "import ",
            "const ",
            "function ",
            "api endpoint",
            "stack trace",
            "exception",
        ],
        "finance-business": [
            "revenue",
            "guidance",
            "forecast",
            "earnings",
            "margin",
            "market share",
            "quarter",
            "valuation",
        ],
        "legal-policy": [
            "plaintiff",
            "respondent",
            "statute",
            "regulation",
            "clause",
            "compliance",
            "policy",
            "jurisdiction",
        ],
        "science-academic": [
            "hypothesis",
            "methodology",
            "dataset",
            "baseline",
            "peer-reviewed",
            "study",
            "experiment",
            "citation",
        ],
    },
    "hard_negative_markers": [
        "i jotted",
        "after a long day",
        "i rewrote",
        "cut a sentence",
        "added an example",
        "it is not polished",
        "what actually happened",
        "in yesterday's meeting",
    ],
    "rewrite_markers": [
        "in other words",
        "to rephrase",
        "paraphrase",
        "translated",
        "restated",
        "reworded",
        "summarized",
        "condensed",
    ],
}


def load_text_expert_bundle() -> dict[str, Any]:
    """Load optional private bundle and merge it over the public baseline."""
    configured_path = settings.text_expert_bundle_path.strip()
    if not configured_path:
        return DEFAULT_TEXT_EXPERT_BUNDLE

    bundle_path = Path(configured_path)
    if not bundle_path.is_absolute():
        backend_root = Path(__file__).resolve().parents[3]
        bundle_path = (backend_root / bundle_path).resolve()
    if not bundle_path.exists():
        return DEFAULT_TEXT_EXPERT_BUNDLE

    try:
        payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_TEXT_EXPERT_BUNDLE

    if not isinstance(payload, dict):
        return DEFAULT_TEXT_EXPERT_BUNDLE

    merged = {
        **DEFAULT_TEXT_EXPERT_BUNDLE,
        **payload,
        "domain_keywords": {
            **DEFAULT_TEXT_EXPERT_BUNDLE["domain_keywords"],
            **(
                payload.get("domain_keywords")
                if isinstance(payload.get("domain_keywords"), dict)
                else {}
            ),
        },
    }
    for key in ("hard_negative_markers", "rewrite_markers"):
        if isinstance(payload.get(key), list):
            merged[key] = [str(item).strip().lower() for item in payload[key] if str(item).strip()]
    return merged

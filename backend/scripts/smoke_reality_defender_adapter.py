#!/usr/bin/env python3
"""Optional live smoke test for Reality Defender adapter contract."""

from __future__ import annotations

import json
import os
import sys

import httpx


def main() -> int:
    api_key = os.getenv("REALITY_DEFENDER_API_KEY", "").strip()
    if not api_key:
        print("REALITY_DEFENDER_API_KEY is empty; skipping smoke.")
        return 0

    url = os.getenv("REALITY_DEFENDER_API_URL", "https://api.realitydefender.com/v1/detect").strip()
    payload = {"modality": "text", "text": "Reality Defender adapter smoke test payload."}

    try:
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        print(f"Smoke request failed: {exc}")
        return 1

    if response.status_code >= 400:
        print(f"Smoke request returned HTTP {response.status_code}")
        try:
            print(response.json())
        except Exception:
            print(response.text[:500])
        return 1

    try:
        parsed = response.json()
    except json.JSONDecodeError:
        print("Smoke response is not valid JSON")
        print(response.text[:500])
        return 1

    if not isinstance(parsed, dict):
        print("Smoke response JSON is not an object")
        return 1

    print("Reality Defender live smoke succeeded.")
    print(f"Top-level keys: {sorted(parsed.keys())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

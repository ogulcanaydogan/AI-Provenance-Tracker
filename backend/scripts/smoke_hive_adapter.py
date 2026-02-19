#!/usr/bin/env python3
"""Optional live smoke test for Hive adapter contract."""

from __future__ import annotations

import json
import os

import httpx


def main() -> int:
    api_key = os.getenv("HIVE_API_KEY", "").strip()
    if not api_key:
        print("HIVE_API_KEY is empty; skipping smoke.")
        return 0

    url = os.getenv("HIVE_API_URL", "").strip() or "https://api.thehive.ai/api/v2/task/sync"
    payload = {"input": {"text": "Hive adapter smoke test payload."}}

    try:
        response = httpx.post(
            url,
            headers={"Authorization": f"Token {api_key}"},
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

    print("Hive live smoke succeeded.")
    print(f"Top-level keys: {sorted(parsed.keys())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

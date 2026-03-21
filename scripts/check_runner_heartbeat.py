#!/usr/bin/env python3
"""Fail-fast guard for self-hosted runner availability before deploy dispatch."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Iterable


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check GitHub self-hosted runner heartbeat.")
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--runner-name", default="spark-self-hosted")
    parser.add_argument(
        "--required-labels",
        default="self-hosted,linux,spark",
        help="Comma-separated labels that runner must have",
    )
    parser.add_argument(
        "--checks",
        type=int,
        default=2,
        help="How many consecutive checks must be online.",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=12,
        help="Sleep interval between checks.",
    )
    return parser.parse_args()


def _auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _fetch_runners(repo: str, token: str) -> list[dict]:
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/actions/runners",
        headers=_auth_headers(token),
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            runners = payload.get("runners", [])
            if isinstance(runners, list):
                return runners
            return []
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        remediation = ""
        if exc.code == 403:
            remediation = (
                " - runner API requires a token with repository Actions read access "
                "(set RUNNER_HEARTBEAT_TOKEN and expose it as GH_TOKEN)."
            )
        raise SystemExit(f"Failed to query runners: HTTP {exc.code} {detail}{remediation}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Failed to query runners: {exc}") from exc


def _normalize_labels(labels: Iterable[str]) -> set[str]:
    return {label.strip().lower() for label in labels if label.strip()}


def main() -> int:
    args = parse_args()
    # GH_TOKEN is intentionally preferred so workflows can supply a privileged heartbeat token.
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GH_TOKEN or GITHUB_TOKEN is required.")

    required_labels = _normalize_labels(args.required_labels.split(","))
    consecutive = 0
    attempts = max(1, int(args.checks))

    for check_idx in range(attempts):
        runners = _fetch_runners(args.repo, token)
        target = next((r for r in runners if r.get("name") == args.runner_name), None)
        if not target:
            raise SystemExit(f"Runner '{args.runner_name}' not found in {args.repo}.")

        labels = _normalize_labels(label.get("name", "") for label in target.get("labels", []))
        status = str(target.get("status", "offline")).lower()
        online = status == "online"
        labels_ok = required_labels.issubset(labels)

        print(
            f"check={check_idx + 1}/{attempts} status={status} "
            f"labels_ok={labels_ok} labels={sorted(labels)}"
        )
        if online and labels_ok:
            consecutive += 1
        else:
            consecutive = 0

        if consecutive >= attempts:
            print("Runner heartbeat passed.")
            return 0

        if check_idx < attempts - 1:
            time.sleep(max(1, int(args.interval_seconds)))

    raise SystemExit(
        f"Runner heartbeat failed: '{args.runner_name}' was not online for {attempts} consecutive checks."
    )


if __name__ == "__main__":
    raise SystemExit(main())

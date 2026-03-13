#!/usr/bin/env python3
"""Generate Tier-1/Tier-2 security + grant rollout readiness snapshot."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OWNER = "ogulcanaydogan"

TIERS = {
    "tier1": [
        "AI-Provenance-Tracker",
        "Verifiable-AI-Output-Ledger",
        "LLM-Supply-Chain-Attestation",
        "Sovereign-RAG-Gateway",
        "Prompt-Injection-Firewall",
    ],
    "tier2": [
        "LLM-Cost-Guardian",
        "MMSAFE-Bench",
        "AI-Model-Card-Generator",
        "AI-Regulation-Compliance-Scanner",
        "LLM-SLO-eBPF-Toolkit",
        "LowResource-LLM-Forge",
        "Turkish-LLM",
        "dgx-spark-llm-stack",
    ],
}

CORE_FILES = [
    "SECURITY.md",
    "CONTRIBUTING.md",
    "LICENSE",
    ".github/workflows/ci.yml",
    ".github/workflows/codeql.yml",
    ".github/workflows/scorecard.yml",
]


def run_gh_api(endpoint: str) -> tuple[dict | list | None, str | None]:
    cmd = ["gh", "api", endpoint]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return None, proc.stderr.strip() or f"gh api failed for {endpoint}"
    try:
        return json.loads(proc.stdout), None
    except json.JSONDecodeError as exc:
        return None, f"invalid gh api json for {endpoint}: {exc}"


def file_exists(repo: str, path: str, branch: str) -> tuple[bool | None, str | None]:
    endpoint = f"repos/{OWNER}/{repo}/contents/{path}?ref={branch}"
    cmd = ["gh", "api", endpoint]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 0:
        return True, None
    stderr = (proc.stderr or "").lower()
    if "404" in stderr or "not found" in stderr:
        return False, None
    return None, proc.stderr.strip() or f"failed to check {path}"


def fetch_text(url: str) -> tuple[str | None, str | None]:
    req = urllib.request.Request(url, headers={"User-Agent": "grant-rollout-audit/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace"), None
    except urllib.error.HTTPError as exc:
        return None, f"http {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def fetch_status_code(url: str) -> tuple[int | None, str | None]:
    req = urllib.request.Request(url, headers={"User-Agent": "grant-rollout-audit/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return int(resp.getcode()), None
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def bestpractices_status(repo: str) -> tuple[bool | None, str | None, int]:
    q = urllib.parse.quote(repo)
    url = f"https://www.bestpractices.dev/en/projects?q={q}"
    html, err = fetch_text(url)
    if err:
        return None, err, 0
    rows = html.count('class="project_name"')
    return rows > 0, None, rows


def huntr_status(repo: str) -> tuple[bool | None, int | None, str | None]:
    url = f"https://huntr.com/repos/{OWNER}/{repo}"
    code, err = fetch_status_code(url)
    if err:
        return None, code, err
    return code == 200, code, None


def recommended_actions(entry: dict) -> list[str]:
    actions: list[str] = []
    files = entry.get("files", {})
    if files.get("SECURITY.md") is False:
        actions.append("add SECURITY.md")
    if files.get("CONTRIBUTING.md") is False:
        actions.append("add CONTRIBUTING.md")
    if files.get(".github/workflows/ci.yml") is False:
        actions.append("add CI workflow")
    if files.get(".github/workflows/codeql.yml") is False:
        actions.append("add CodeQL workflow")
    if files.get(".github/workflows/scorecard.yml") is False:
        actions.append("add OpenSSF Scorecard workflow")

    if entry.get("bestpractices", {}).get("registered") is False:
        actions.append("submit bestpractices.dev badge application")
    if entry.get("huntr", {}).get("registered") is False:
        actions.append("submit huntr maintainer onboarding request")
    return actions


def md_bool(value: bool | None) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"


def to_markdown(payload: dict) -> str:
    lines: list[str] = []
    lines.append("# Security Audit & Grant Rollout Status")
    lines.append("")
    lines.append(f"Generated at: {payload['generated_at']}")
    lines.append("")

    for tier_name in ["tier1", "tier2"]:
        repos = payload["tiers"][tier_name]
        lines.append(f"## {tier_name.upper()}")
        lines.append("")
        lines.append("| Repo | Private | Security.md | CI | CodeQL | Scorecard | BestPractices | Huntr |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
        for entry in repos:
            if "files" not in entry:
                lines.append(
                    f"| `{entry['repo']}` | unknown | unknown | unknown | unknown | unknown | unknown | unknown |"
                )
                continue
            files = entry["files"]
            bp = entry["bestpractices"]
            huntr = entry["huntr"]
            lines.append(
                "| "
                f"[{entry['repo']}]({entry['repo_url']}) | "
                f"{md_bool(entry['is_private'])} | "
                f"{md_bool(files.get('SECURITY.md'))} | "
                f"{md_bool(files.get('.github/workflows/ci.yml'))} | "
                f"{md_bool(files.get('.github/workflows/codeql.yml'))} | "
                f"{md_bool(files.get('.github/workflows/scorecard.yml'))} | "
                f"{md_bool(bp.get('registered'))} | "
                f"{md_bool(huntr.get('registered'))} |"
            )
        lines.append("")

    lines.append("## Recommended Next Actions")
    lines.append("")
    for tier_name in ["tier1", "tier2"]:
        lines.append(f"### {tier_name.upper()}")
        lines.append("")
        for entry in payload["tiers"][tier_name]:
            if "files" not in entry:
                lines.append(f"- `{entry['repo']}`: metadata lookup failed ({entry.get('error', 'unknown error')})")
                continue
            actions = entry.get("recommended_actions", [])
            if not actions:
                lines.append(f"- `{entry['repo']}`: no immediate action")
            else:
                lines.append(f"- `{entry['repo']}`: {', '.join(actions)}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--md-out", required=True)
    args = parser.parse_args()

    generated_at = dt.datetime.now(dt.timezone.utc).isoformat()
    payload: dict = {
        "generated_at": generated_at,
        "owner": OWNER,
        "tiers": {"tier1": [], "tier2": []},
    }

    for tier_name, repos in TIERS.items():
        for repo in repos:
            meta, meta_err = run_gh_api(f"repos/{OWNER}/{repo}")
            if not isinstance(meta, dict):
                payload["tiers"][tier_name].append(
                    {
                        "repo": repo,
                        "repo_url": f"https://github.com/{OWNER}/{repo}",
                        "error": meta_err or "metadata lookup failed",
                    }
                )
                continue

            branch = (meta.get("default_branch") or "main").strip()
            files: dict[str, bool | None] = {}
            file_errors: dict[str, str] = {}
            for path in CORE_FILES:
                exists, err = file_exists(repo, path, branch)
                files[path] = exists
                if err:
                    file_errors[path] = err

            bp_registered, bp_err, bp_rows = bestpractices_status(repo)
            huntr_registered, huntr_code, huntr_err = huntr_status(repo)

            entry = {
                "repo": repo,
                "repo_url": meta.get("html_url"),
                "default_branch": branch,
                "is_private": bool(meta.get("private")),
                "stargazers": int(meta.get("stargazers_count", 0)),
                "pushed_at": meta.get("pushed_at"),
                "files": files,
                "file_errors": file_errors,
                "bestpractices": {
                    "registered": bp_registered,
                    "rows": bp_rows,
                    "error": bp_err,
                },
                "huntr": {
                    "registered": huntr_registered,
                    "status_code": huntr_code,
                    "error": huntr_err,
                },
            }
            entry["recommended_actions"] = recommended_actions(entry)
            payload["tiers"][tier_name].append(entry)

    json_path = Path(args.json_out)
    md_path = Path(args.md_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    md_path.write_text(to_markdown(payload), encoding="utf-8")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

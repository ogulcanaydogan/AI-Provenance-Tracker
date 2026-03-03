#!/usr/bin/env python3
"""Validate dependency sources against package policy allow/deny rules."""

from __future__ import annotations

import argparse
import fnmatch
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_POLICY: dict[str, Any] = {
    "policy_version": "2026-03-03.moderate-v1",
    "allowed_npm_registry_hosts": ["registry.npmjs.org"],
    "allowed_pip_hosts": ["pypi.org", "files.pythonhosted.org"],
    "blocked_package_patterns": [],
}


@dataclass(slots=True)
class Violation:
    source: str
    package: str
    detail: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check npm/pip dependency sources against policy.")
    parser.add_argument("--policy-file", default="config/package_policy.yaml")
    parser.add_argument("--npm-lock", default="frontend/package-lock.json")
    parser.add_argument("--requirements", default="backend/requirements.txt")
    parser.add_argument("--output-json", default="ops/reports/package_policy_report.json")
    parser.add_argument("--output-md", default="ops/reports/package_policy_report.md")
    return parser.parse_args()


def _coerce_yaml_scalar(raw: str) -> Any:
    value = raw.strip()
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none", "~"}:
        return None
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_key: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            if current_key is None:
                continue
            data.setdefault(current_key, [])
            if isinstance(data[current_key], list):
                data[current_key].append(_coerce_yaml_scalar(stripped[2:]))
            continue
        if ":" not in stripped:
            continue
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not raw_value:
            data[key] = []
            current_key = key
            continue
        data[key] = _coerce_yaml_scalar(raw_value)
        current_key = key
    return data


def _load_policy(path: Path) -> dict[str, Any]:
    policy: dict[str, Any] = json.loads(json.dumps(DEFAULT_POLICY))
    if not path.exists():
        policy["policy_source"] = "default"
        return policy

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        policy["policy_source"] = f"{path} (empty -> default)"
        return policy

    parsed: dict[str, Any]
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = _parse_simple_yaml(text)

    if isinstance(parsed, dict):
        for key in (
            "policy_version",
            "allowed_npm_registry_hosts",
            "allowed_pip_hosts",
            "blocked_package_patterns",
        ):
            if key in parsed:
                policy[key] = parsed[key]

    policy["policy_source"] = str(path)
    return policy


def _extract_npm_resolved(payload: dict[str, Any]) -> list[tuple[str, str]]:
    resolved_entries: list[tuple[str, str]] = []

    packages = payload.get("packages")
    if isinstance(packages, dict):
        for package_path, meta in packages.items():
            if not isinstance(meta, dict):
                continue
            resolved = meta.get("resolved")
            if isinstance(resolved, str) and resolved:
                package_name = package_path.replace("node_modules/", "") or "root"
                resolved_entries.append((package_name, resolved))

    def walk_dependencies(deps: Any) -> None:
        if not isinstance(deps, dict):
            return
        for name, meta in deps.items():
            if not isinstance(meta, dict):
                continue
            resolved = meta.get("resolved")
            if isinstance(resolved, str) and resolved:
                resolved_entries.append((str(name), resolved))
            walk_dependencies(meta.get("dependencies"))

    walk_dependencies(payload.get("dependencies"))
    return resolved_entries


def _extract_requirement_name(line: str) -> str:
    chunk = line.strip()
    if "@" in chunk and "http" in chunk:
        return chunk.split("@", 1)[0].strip()
    separators = ["==", ">=", "<=", "~=", "!=", "<", ">"]
    for sep in separators:
        if sep in chunk:
            return chunk.split(sep, 1)[0].strip()
    return chunk.split()[0].strip() if chunk.split() else "unknown"


def _host_from_url(url: str) -> str:
    parsed = urlparse(url)
    return (parsed.hostname or "").lower().strip()


def _build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Package Policy Report",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Policy version: `{report['policy']['policy_version']}`",
        f"- Policy source: `{report['policy']['policy_source']}`",
        f"- Status: `{report['status']}`",
        "",
        "## Summary",
        "",
        f"- npm resolved entries checked: `{report['summary']['npm_entries_checked']}`",
        f"- requirements lines checked: `{report['summary']['requirements_checked']}`",
        f"- violations: `{report['summary']['violation_count']}`",
        "",
        "## Violations",
        "",
    ]

    violations = report.get("violations", [])
    if not violations:
        lines.append("- None")
    else:
        lines.extend(
            [
                "| Source | Package | Detail |",
                "| --- | --- | --- |",
            ]
        )
        for item in violations:
            lines.append(f"| {item['source']} | {item['package']} | {item['detail']} |")

    lines.append("")
    return "\n".join(lines)


def run() -> int:
    args = parse_args()

    policy_path = Path(args.policy_file).expanduser().resolve()
    npm_lock_path = Path(args.npm_lock).expanduser().resolve()
    requirements_path = Path(args.requirements).expanduser().resolve()

    policy = _load_policy(policy_path)
    allowed_npm_hosts = {
        str(host).lower().strip() for host in policy.get("allowed_npm_registry_hosts", []) if str(host).strip()
    }
    allowed_pip_hosts = {
        str(host).lower().strip() for host in policy.get("allowed_pip_hosts", []) if str(host).strip()
    }
    blocked_patterns = [str(item).strip() for item in policy.get("blocked_package_patterns", []) if str(item).strip()]

    violations: list[Violation] = []

    npm_entries_checked = 0
    if npm_lock_path.exists():
        payload = json.loads(npm_lock_path.read_text(encoding="utf-8"))
        for package_name, resolved in _extract_npm_resolved(payload):
            npm_entries_checked += 1
            if resolved.startswith("file:"):
                continue
            host = _host_from_url(resolved)
            if host and allowed_npm_hosts and host not in allowed_npm_hosts:
                violations.append(
                    Violation(
                        source="npm",
                        package=package_name,
                        detail=f"resolved host '{host}' not in allowlist",
                    )
                )
            if any(fnmatch.fnmatch(package_name, pattern) for pattern in blocked_patterns):
                violations.append(
                    Violation(
                        source="npm",
                        package=package_name,
                        detail="matches blocked_package_patterns",
                    )
                )

    requirements_checked = 0
    if requirements_path.exists():
        for raw_line in requirements_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            requirements_checked += 1

            if line.startswith("--index-url") or line.startswith("--extra-index-url"):
                url = line.split(maxsplit=1)[1].strip() if len(line.split(maxsplit=1)) > 1 else ""
                host = _host_from_url(url)
                if host and allowed_pip_hosts and host not in allowed_pip_hosts:
                    violations.append(
                        Violation(
                            source="pip",
                            package="index-url",
                            detail=f"index host '{host}' not in allowlist",
                        )
                    )
                continue

            package_name = _extract_requirement_name(line)
            if "http://" in line or "https://" in line:
                token = next((part for part in line.split() if part.startswith(("http://", "https://"))), "")
                host = _host_from_url(token)
                if host and allowed_pip_hosts and host not in allowed_pip_hosts:
                    violations.append(
                        Violation(
                            source="pip",
                            package=package_name,
                            detail=f"package URL host '{host}' not in allowlist",
                        )
                    )

            if any(fnmatch.fnmatch(package_name, pattern) for pattern in blocked_patterns):
                violations.append(
                    Violation(
                        source="pip",
                        package=package_name,
                        detail="matches blocked_package_patterns",
                    )
                )

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "pass" if not violations else "fail",
        "policy": {
            "policy_version": policy.get("policy_version", "unknown"),
            "policy_source": policy.get("policy_source", "default"),
            "allowed_npm_registry_hosts": sorted(allowed_npm_hosts),
            "allowed_pip_hosts": sorted(allowed_pip_hosts),
            "blocked_package_patterns": blocked_patterns,
        },
        "summary": {
            "npm_entries_checked": npm_entries_checked,
            "requirements_checked": requirements_checked,
            "violation_count": len(violations),
        },
        "violations": [
            {
                "source": v.source,
                "package": v.package,
                "detail": v.detail,
            }
            for v in violations
        ],
    }

    output_json = Path(args.output_json).expanduser().resolve()
    output_md = Path(args.output_md).expanduser().resolve()
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(_build_markdown(report), encoding="utf-8")

    print(f"Wrote JSON: {output_json}")
    print(f"Wrote Markdown: {output_md}")

    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(run())

#!/usr/bin/env python3
"""Generate release provenance summary from publish artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate release provenance note artifacts.")
    parser.add_argument("--component", required=True)
    parser.add_argument("--image-ref", required=True)
    parser.add_argument("--image-digest", default="")
    parser.add_argument("--trivy-report", required=True)
    parser.add_argument("--sbom-artifact", required=True)
    parser.add_argument("--attestation-type", default="spdxjson")
    parser.add_argument("--signed-keyless", default="true")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    return parser.parse_args()


def _to_bool(value: str) -> bool:
    normalized = (value or "").strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def _count_vulns(report: dict[str, Any]) -> dict[str, int]:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0}
    for result in report.get("Results", []) or []:
        vulns = result.get("Vulnerabilities") or []
        for vuln in vulns:
            severity = str(vuln.get("Severity") or "UNKNOWN").lower()
            if severity in counts:
                counts[severity] += 1
            else:
                counts["unknown"] += 1
    return counts


def _build_markdown(payload: dict[str, Any]) -> str:
    vuln = payload["vulnerability_summary"]
    lines = [
        f"## Release Provenance ({payload['component']})",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Image ref: `{payload['image']['ref']}`",
        f"- Image digest: `{payload['image']['digest'] or 'n/a'}`",
        f"- Keyless signature step: `{payload['verification']['signed_keyless']}`",
        f"- SBOM artifact: `{payload['verification']['sbom_artifact']}`",
        f"- Attestation type: `{payload['verification']['attestation_type']}`",
        "",
        "### Trivy Summary",
        "",
        f"- Critical: `{vuln['critical']}`",
        f"- High: `{vuln['high']}`",
        f"- Medium: `{vuln['medium']}`",
        f"- Low: `{vuln['low']}`",
        f"- Unknown: `{vuln['unknown']}`",
        "",
    ]
    return "\n".join(lines)


def run() -> int:
    args = parse_args()

    trivy_path = Path(args.trivy_report).expanduser().resolve()
    trivy_payload = json.loads(trivy_path.read_text(encoding="utf-8")) if trivy_path.exists() else {}

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "component": args.component,
        "image": {
            "ref": args.image_ref,
            "digest": args.image_digest,
        },
        "verification": {
            "signed_keyless": _to_bool(args.signed_keyless),
            "sbom_artifact": args.sbom_artifact,
            "attestation_type": args.attestation_type,
        },
        "vulnerability_summary": _count_vulns(trivy_payload),
    }

    output_json = Path(args.output_json).expanduser().resolve()
    output_md = Path(args.output_md).expanduser().resolve()
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(_build_markdown(payload), encoding="utf-8")

    print(f"Wrote JSON: {output_json}")
    print(f"Wrote Markdown: {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

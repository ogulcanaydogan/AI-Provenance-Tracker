"""Build a talent-visa-oriented evidence pack from report artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from glob import glob
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build talent visa evidence pack from reports.")
    parser.add_argument(
        "--reports-glob",
        default="backend/x_trust_report*.json",
        help="Glob for trust report JSON files",
    )
    parser.add_argument(
        "--benchmarks-glob",
        default="backend/x_trust_benchmark*.json",
        help="Glob for benchmark JSON files",
    )
    parser.add_argument(
        "--output-dir",
        default="backend/evidence",
        help="Directory for evidence pack outputs",
    )
    return parser.parse_args()


def _load_json_files(pattern: str) -> list[tuple[Path, dict[str, Any]]]:
    items: list[tuple[Path, dict[str, Any]]] = []
    for raw in sorted(glob(pattern)):
        path = Path(raw).resolve()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        items.append((path, payload))
    return items


def _summarize_report(path: Path, report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("executive_summary", {})
    timeline = report.get("timeline", [])
    claims = report.get("claims_and_narratives", [])
    return {
        "file": str(path),
        "risk_level": summary.get("risk_level", "low"),
        "confidence_overall": report.get("confidence_overall", "low"),
        "timeline_days": len(timeline),
        "claim_topics": len(claims),
        "top_findings": summary.get("top_3_findings", []),
    }


def _summarize_benchmark(path: Path, benchmark: dict[str, Any]) -> dict[str, Any]:
    metrics = benchmark.get("metrics", {})
    bot = metrics.get("bot_detection", {})
    claim = metrics.get("claim_response", {})
    return {
        "file": str(path),
        "bot_f1": bot.get("f1", 0.0),
        "bot_precision": bot.get("precision", 0.0),
        "bot_recall": bot.get("recall", 0.0),
        "claim_accuracy": claim.get("accuracy", 0.0),
    }


def _build_markdown(pack: dict[str, Any]) -> str:
    lines = [
        "# Talent Visa Evidence Pack",
        "",
        f"- Generated At: {pack['generated_at']}",
        f"- Report Count: {pack['report_count']}",
        f"- Benchmark Count: {pack['benchmark_count']}",
        "",
        "## Technical Contributions",
        "- Implemented X intelligence collection pipeline (handle + query scope).",
        "- Implemented trust-and-safety report generator with explainable JSON output.",
        "- Implemented benchmark harness and evidence-pack automation.",
        "",
        "## Operational Evidence",
    ]
    for report in pack["reports"]:
        lines.extend(
            [
                f"- `{report['file']}`",
                f"  - risk_level={report['risk_level']}, confidence={report['confidence_overall']}",
                f"  - timeline_days={report['timeline_days']}, claim_topics={report['claim_topics']}",
            ]
        )

    if pack["benchmarks"]:
        lines.append("")
        lines.append("## Benchmark Evidence")
        for benchmark in pack["benchmarks"]:
            lines.extend(
                [
                    f"- `{benchmark['file']}`",
                    f"  - bot_f1={benchmark['bot_f1']}, precision={benchmark['bot_precision']}, recall={benchmark['bot_recall']}",
                    f"  - claim_accuracy={benchmark['claim_accuracy']}",
                ]
            )

    lines.extend(
        [
            "",
            "## Suggested Submission Bundle",
            "- Architecture and methodology note (detection + limitations).",
            "- 2-3 timestamped report artifacts with source-linked evidence.",
            "- Benchmark snapshots showing iterative quality improvements.",
            "- Public technical write-up and open-source commit references.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    reports = _load_json_files(args.reports_glob)
    if not reports:
        print(f"No report files found for pattern: {args.reports_glob}")
        return 1

    benchmarks = _load_json_files(args.benchmarks_glob)

    pack = {
        "generated_at": datetime.now(UTC).isoformat(),
        "report_count": len(reports),
        "benchmark_count": len(benchmarks),
        "reports": [_summarize_report(path, payload) for path, payload in reports],
        "benchmarks": [_summarize_benchmark(path, payload) for path, payload in benchmarks],
    }

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "talent_visa_evidence_pack.json"
    md_path = output_dir / "talent_visa_evidence_pack.md"

    json_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_build_markdown(pack), encoding="utf-8")

    print(f"Wrote evidence pack JSON to {json_path}")
    print(f"Wrote evidence pack Markdown to {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


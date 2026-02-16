"""Compare two pipeline run directories and generate a compact evidence delta report."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


RISK_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}
CONFIDENCE_ORDER = {"low": 1, "medium": 2, "high": 3}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _risk_delta(base: str, candidate: str) -> dict[str, Any]:
    base_score = RISK_ORDER.get(base, 0)
    candidate_score = RISK_ORDER.get(candidate, 0)
    diff = candidate_score - base_score
    if diff > 0:
        direction = "up"
    elif diff < 0:
        direction = "down"
    else:
        direction = "same"
    return {"direction": direction, "delta": diff}


def _confidence_delta(base: str, candidate: str) -> dict[str, Any]:
    base_score = CONFIDENCE_ORDER.get(base, 0)
    candidate_score = CONFIDENCE_ORDER.get(candidate, 0)
    diff = candidate_score - base_score
    if diff > 0:
        direction = "up"
    elif diff < 0:
        direction = "down"
    else:
        direction = "same"
    return {"direction": direction, "delta": diff}


def _run_summary(run_dir: Path) -> dict[str, Any]:
    input_path = run_dir / "x_intel_input.json"
    report_path = run_dir / "x_trust_report.json"
    benchmark_path = run_dir / "x_trust_benchmark.json"
    manifest_path = run_dir / "pipeline_manifest.json"

    intel = _load_json(input_path)
    report = _load_json(report_path)
    benchmark = _load_json(benchmark_path)
    manifest = _load_json(manifest_path) if manifest_path.exists() else {}

    posts = intel.get("posts", [])
    unique_accounts = len({(post.get("author") or {}).get("handle", "") for post in posts})
    exec_summary = report.get("executive_summary", {})
    bot_activity = report.get("bot_activity", {})
    narratives = report.get("claims_and_narratives", [])
    timeline = report.get("timeline", [])

    return {
        "run_dir": str(run_dir.resolve()),
        "run_id": str(manifest.get("run_id", run_dir.name)),
        "window": str(intel.get("window", "unknown")),
        "post_count": len(posts),
        "unique_accounts": unique_accounts,
        "risk_level": str(exec_summary.get("risk_level", "unknown")),
        "confidence_overall": str(report.get("confidence_overall", "unknown")),
        "timeline_days": len(timeline),
        "suspected_clusters": len(bot_activity.get("suspected_clusters", [])),
        "narrative_topics": len(narratives),
        "benchmark_summary": benchmark.get("report_summary", {}),
    }


def _markdown_report(comparison: dict[str, Any]) -> str:
    base = comparison["base"]
    candidate = comparison["candidate"]
    delta = comparison["delta"]

    lines = [
        "# Talent Visa Run Comparison",
        "",
        f"- Generated at: {comparison['generated_at']}",
        f"- Base run: `{base['run_id']}`",
        f"- Candidate run: `{candidate['run_id']}`",
        "",
        "## Coverage",
        "",
        f"- Base posts: {base['post_count']}",
        f"- Candidate posts: {candidate['post_count']}",
        f"- Delta posts: {delta['post_count_delta']}",
        f"- Base unique accounts: {base['unique_accounts']}",
        f"- Candidate unique accounts: {candidate['unique_accounts']}",
        "",
        "## Risk and Confidence",
        "",
        f"- Risk: {base['risk_level']} -> {candidate['risk_level']} ({delta['risk_change']['direction']})",
        (
            f"- Confidence: {base['confidence_overall']} -> {candidate['confidence_overall']} "
            f"({delta['confidence_change']['direction']})"
        ),
        "",
        "## Structure",
        "",
        f"- Timeline days: {base['timeline_days']} -> {candidate['timeline_days']}",
        f"- Narrative topics: {base['narrative_topics']} -> {candidate['narrative_topics']}",
        f"- Suspected clusters: {base['suspected_clusters']} -> {candidate['suspected_clusters']}",
        "",
        "## Benchmark",
        "",
        f"- Base benchmark summary: `{json.dumps(base['benchmark_summary'], ensure_ascii=False)}`",
        f"- Candidate benchmark summary: `{json.dumps(candidate['benchmark_summary'], ensure_ascii=False)}`",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two talent-visa pipeline run directories.")
    parser.add_argument("--base-run-dir", required=True, help="Reference run directory")
    parser.add_argument("--candidate-run-dir", required=True, help="New run directory")
    parser.add_argument("--output-json", default="comparison.json", help="Output comparison JSON")
    parser.add_argument("--output-md", default="comparison.md", help="Output comparison Markdown")
    return parser.parse_args()


def run() -> int:
    args = parse_args()
    base_dir = Path(args.base_run_dir).expanduser().resolve()
    candidate_dir = Path(args.candidate_run_dir).expanduser().resolve()

    if not base_dir.exists():
        print(f"Base run directory not found: {base_dir}")
        return 1
    if not candidate_dir.exists():
        print(f"Candidate run directory not found: {candidate_dir}")
        return 1

    base = _run_summary(base_dir)
    candidate = _run_summary(candidate_dir)

    comparison = {
        "generated_at": datetime.now(UTC).isoformat(),
        "base": base,
        "candidate": candidate,
        "delta": {
            "post_count_delta": candidate["post_count"] - base["post_count"],
            "unique_accounts_delta": candidate["unique_accounts"] - base["unique_accounts"],
            "timeline_days_delta": candidate["timeline_days"] - base["timeline_days"],
            "narrative_topics_delta": candidate["narrative_topics"] - base["narrative_topics"],
            "suspected_clusters_delta": candidate["suspected_clusters"] - base["suspected_clusters"],
            "risk_change": _risk_delta(base["risk_level"], candidate["risk_level"]),
            "confidence_change": _confidence_delta(
                base["confidence_overall"], candidate["confidence_overall"]
            ),
        },
    }

    output_json = Path(args.output_json).expanduser().resolve()
    output_md = Path(args.output_md).expanduser().resolve()
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    output_json.write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(_markdown_report(comparison), encoding="utf-8")

    print(f"Wrote comparison JSON to {output_json}")
    print(f"Wrote comparison Markdown to {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())


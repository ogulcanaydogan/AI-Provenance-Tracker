"""Run full talent-visa evidence pipeline: collect -> report -> benchmark -> evidence pack."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models.x_intel import UserContext
from app.services.trust_report import generate_trust_report
from app.services.x_intel import XDataCollectionError, XIntelCollector


def _canonical_json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _resolve_run_id(args: argparse.Namespace, intel_payload: dict) -> str:
    if args.run_id:
        return "".join(ch for ch in args.run_id if ch.isalnum() or ch in ("-", "_"))[:48]
    digest = _sha256_bytes(_canonical_json(intel_payload).encode("utf-8"))
    return f"run_{digest[:12]}"


def _validate_report_contract(report: dict) -> None:
    required = {
        "executive_summary",
        "timeline",
        "bot_activity",
        "ai_generated_content",
        "claims_and_narratives",
        "recommended_strategy",
        "data_gaps",
        "confidence_overall",
    }
    missing = required.difference(report.keys())
    if missing:
        raise ValueError(f"Trust report missing required keys: {sorted(missing)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run full talent-visa evidence pipeline.")
    parser.add_argument("--handle", required=True, help="Target handle, with or without @")
    parser.add_argument("--window-days", type=int, default=90, help="Collection window in days")
    parser.add_argument("--max-posts", type=int, default=600, help="Max posts to collect")
    parser.add_argument("--query", default="", help="Optional search query for broader scope")
    parser.add_argument("--output-dir", default="evidence/runs", help="Run artifact directory")
    parser.add_argument("--labels", default="", help="Optional benchmark labels JSON path")
    parser.add_argument("--run-id", default="", help="Deterministic run id override")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow writing into an existing run directory",
    )

    parser.add_argument("--sector", default="unknown")
    parser.add_argument("--risk-tolerance", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--preferred-language", default="tr")
    parser.add_argument(
        "--user-profile",
        default="brand",
        choices=["influencer", "brand", "journalist", "politician", "startup_ceo"],
    )
    parser.add_argument(
        "--legal-pr-capacity",
        default="basic",
        choices=["none", "basic", "advanced"],
    )
    parser.add_argument(
        "--goal",
        default="reputation_protection",
        choices=["reputation_protection", "crisis_response", "brand_safety", "misinfo_mitigation"],
    )
    return parser.parse_args()


def _run_python_script(script: str, args: list[str]) -> None:
    command = [sys.executable, str(BACKEND_ROOT / "scripts" / script), *args]
    subprocess.run(command, check=True, cwd=BACKEND_ROOT)


async def run() -> int:
    args = parse_args()
    collector = XIntelCollector()
    user_context = UserContext(
        sector=args.sector,
        risk_tolerance=args.risk_tolerance,
        preferred_language=args.preferred_language,
        user_profile=args.user_profile,
        legal_pr_capacity=args.legal_pr_capacity,
        goal=args.goal,
    )

    try:
        intel_input_model = await collector.collect(
            target_handle=args.handle,
            window_days=args.window_days,
            max_posts=args.max_posts,
            query=args.query or None,
            user_context=user_context,
        )
    except XDataCollectionError as exc:
        print(f"Collection failed: {exc}")
        return 1

    intel_input = intel_input_model.model_dump(mode="json")
    run_id = _resolve_run_id(args, intel_input)
    run_dir = Path(args.output_dir).expanduser().resolve() / run_id
    if run_dir.exists() and not args.overwrite:
        print(f"Run directory already exists: {run_dir} (use --overwrite to reuse)")
        return 1
    run_dir.mkdir(parents=True, exist_ok=True)

    input_path = run_dir / "x_intel_input.json"
    input_canonical_path = run_dir / "x_intel_input.canonical.json"
    report_path = run_dir / "x_trust_report.json"
    report_canonical_path = run_dir / "x_trust_report.canonical.json"
    benchmark_path = run_dir / "x_trust_benchmark.json"
    manifest_path = run_dir / "pipeline_manifest.json"

    input_path.write_text(json.dumps(intel_input, ensure_ascii=False, indent=2), encoding="utf-8")
    input_canonical_path.write_text(_canonical_json(intel_input), encoding="utf-8")

    intel_input = json.loads(input_canonical_path.read_text(encoding="utf-8"))
    report = generate_trust_report(intel_input)
    _validate_report_contract(report)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_canonical_path.write_text(_canonical_json(report), encoding="utf-8")

    benchmark_args = [
        "--report",
        str(report_path),
        "--output",
        str(benchmark_path),
    ]
    if args.labels:
        benchmark_args.extend(["--labels", str(Path(args.labels).expanduser().resolve())])
    _run_python_script("benchmark_x_intel.py", benchmark_args)

    _run_python_script(
        "build_talent_visa_evidence_pack.py",
        [
            "--reports-glob",
            str(run_dir / "x_trust_report*.json"),
            "--benchmarks-glob",
            str(run_dir / "x_trust_benchmark*.json"),
            "--output-dir",
            str(run_dir),
        ],
    )

    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "run_id": run_id,
        "run_dir": str(run_dir),
        "artifacts": {
            "input": str(input_path),
            "input_canonical": str(input_canonical_path),
            "report": str(report_path),
            "report_canonical": str(report_canonical_path),
            "benchmark": str(benchmark_path),
            "evidence_pack_json": str(run_dir / "talent_visa_evidence_pack.json"),
            "evidence_pack_md": str(run_dir / "talent_visa_evidence_pack.md"),
        },
        "checksums_sha256": {
            "x_intel_input.canonical.json": _sha256_bytes(
                input_canonical_path.read_bytes()
            ),
            "x_trust_report.canonical.json": _sha256_bytes(
                report_canonical_path.read_bytes()
            ),
            "x_trust_benchmark.json": _sha256_bytes(
                benchmark_path.read_bytes()
            ),
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Pipeline completed. Run ID: {run_id}. Artifacts in: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))

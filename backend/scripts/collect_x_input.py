"""CLI utility to collect X data and emit schema-compliant intelligence JSON."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.models.x_intel import UserContext
from app.services.x_intel import XDataCollectionError, XIntelCollector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect X data and output trust-and-safety input JSON.",
    )
    parser.add_argument("--handle", required=True, help="Target handle, with or without @")
    parser.add_argument("--window-days", type=int, default=14, help="Time window in days")
    parser.add_argument("--max-posts", type=int, default=250, help="Maximum posts to collect")
    parser.add_argument(
        "--query",
        default="",
        help="Optional X search query for broader topic collection",
    )
    parser.add_argument(
        "--output",
        default="x_intel_input.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--show-request-estimate",
        action="store_true",
        help="Print estimated X API request usage before collection.",
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


async def run() -> int:
    args = parse_args()
    collector = XIntelCollector()
    if args.show_request_estimate:
        plan = collector.estimate_request_plan(max_posts=args.max_posts)
        print(
            "Estimated X API requests:",
            plan["estimated_requests"],
            f"(cap={settings.x_max_requests_per_run}, page_cap={plan['page_cap']})",
        )
    user_context = UserContext(
        sector=args.sector,
        risk_tolerance=args.risk_tolerance,
        preferred_language=args.preferred_language,
        user_profile=args.user_profile,
        legal_pr_capacity=args.legal_pr_capacity,
        goal=args.goal,
    )

    try:
        payload = await collector.collect(
            target_handle=args.handle,
            window_days=args.window_days,
            max_posts=args.max_posts,
            query=args.query or None,
            user_context=user_context,
        )
    except XDataCollectionError as exc:
        print(f"Collection failed: {exc}")
        return 1

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(payload.model_dump_json(indent=2), encoding="utf-8")
    print(f"Wrote intelligence input JSON to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))

"""Generate trust-and-safety report JSON from collected X intelligence input."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.trust_report import generate_trust_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate trust-and-safety report from x_intel_input JSON.",
    )
    parser.add_argument("--input", required=True, help="Path to collected x_intel_input JSON")
    parser.add_argument(
        "--output",
        default="x_trust_report.json",
        help="Output report JSON path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        return 1

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    report = generate_trust_report(payload)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote trust report JSON to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

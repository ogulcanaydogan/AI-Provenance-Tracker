#!/usr/bin/env python3
"""Generate runtime latency/error observability report from Prometheus metrics."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SAMPLE_RE = re.compile(
    r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{([^}]*)\})?\s+([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)"
)
LABEL_RE = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)="((?:\\"|[^"])*)"')

DEFAULT_EXCLUDED_HANDLERS = {
    "/health",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
}


@dataclass(slots=True)
class MetricSample:
    name: str
    labels: dict[str, str]
    value: float


@dataclass(slots=True)
class Alert:
    level: str
    source: str
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute runtime SLO signals from /metrics output.")
    parser.add_argument(
        "--metrics-url",
        default=os.getenv("PRODUCTION_METRICS_URL", ""),
        help="Prometheus metrics endpoint URL (defaults to PRODUCTION_METRICS_URL).",
    )
    parser.add_argument(
        "--api-url",
        default=os.getenv("PRODUCTION_API_URL", ""),
        help="Base API URL. Used as fallback to metrics-url + '/metrics'.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("PRODUCTION_API_KEY", ""),
        help="Optional API key used while scraping metrics.",
    )
    parser.add_argument(
        "--api-key-header",
        default=os.getenv("PRODUCTION_API_KEY_HEADER", "X-API-Key"),
        help="Header name for --api-key.",
    )
    parser.add_argument(
        "--latency-p95-slo-seconds",
        type=float,
        default=2.0,
        help="Warn threshold for p95 latency.",
    )
    parser.add_argument(
        "--latency-p95-critical-seconds",
        type=float,
        default=3.5,
        help="Critical threshold for p95 latency.",
    )
    parser.add_argument(
        "--error-rate-slo",
        type=float,
        default=0.03,
        help="Warn threshold for runtime error rate (0-1).",
    )
    parser.add_argument(
        "--error-rate-critical",
        type=float,
        default=0.06,
        help="Critical threshold for runtime error rate (0-1).",
    )
    parser.add_argument(
        "--metrics-file",
        default="",
        help="Optional local metrics text file for offline parsing/testing.",
    )
    parser.add_argument("--output-json", default="ops/reports/runtime_observability_report.json")
    parser.add_argument("--output-md", default="ops/reports/runtime_observability_report.md")
    parser.add_argument(
        "--fail-on-alert-level",
        choices=("none", "warn", "critical"),
        default="none",
    )
    return parser.parse_args()


def _resolve_metrics_url(metrics_url: str, api_url: str) -> str:
    direct = metrics_url.strip()
    if direct:
        return direct

    base = api_url.strip().rstrip("/")
    if base:
        return f"{base}/metrics"
    raise ValueError("Missing metrics URL. Provide --metrics-url or --api-url.")


def _fetch_metrics_text(url: str, api_key: str, api_key_header: str) -> str:
    headers = {
        "Accept": "text/plain",
        "User-Agent": "ai-provenance-runtime-observability/1.0",
    }
    if api_key:
        headers[api_key_header] = api_key
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8")


def _parse_labels(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    labels: dict[str, str] = {}
    for key, value in LABEL_RE.findall(raw):
        labels[key] = value.replace('\\"', '"')
    return labels


def parse_prometheus_text(text: str) -> list[MetricSample]:
    samples: list[MetricSample] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = SAMPLE_RE.match(line)
        if not match:
            continue
        name = match.group(1)
        labels_raw = match.group(3)
        value_raw = match.group(4)
        try:
            value = float(value_raw)
        except ValueError:
            continue
        samples.append(MetricSample(name=name, labels=_parse_labels(labels_raw), value=value))
    return samples


def _is_runtime_handler(handler: str) -> bool:
    return handler and handler not in DEFAULT_EXCLUDED_HANDLERS and not handler.startswith("/static")


def _to_float_le(raw_le: str) -> float:
    if raw_le in {"+Inf", "Inf", "inf"}:
        return math.inf
    return float(raw_le)


def _quantile_from_buckets(cumulative: dict[float, float], quantile: float) -> float | None:
    if not cumulative:
        return None
    ordered = sorted(cumulative.items(), key=lambda item: item[0])
    total = ordered[-1][1]
    if total <= 0:
        return None

    target = total * quantile
    previous_finite = None
    for bound, count in ordered:
        if math.isfinite(bound):
            previous_finite = bound
        if count >= target:
            if math.isfinite(bound):
                return bound
            return previous_finite
    return previous_finite


def _build_runtime_summary(samples: list[MetricSample]) -> dict[str, Any]:
    total_requests = 0.0
    error_requests = 0.0
    per_handler_totals: dict[str, float] = {}
    per_handler_errors: dict[str, float] = {}

    global_buckets: dict[float, float] = {}
    per_handler_buckets: dict[str, dict[float, float]] = {}

    for sample in samples:
        if sample.name == "http_requests_total":
            handler = sample.labels.get("handler", "")
            if not _is_runtime_handler(handler):
                continue
            status = sample.labels.get("status", "")
            total_requests += sample.value
            per_handler_totals[handler] = per_handler_totals.get(handler, 0.0) + sample.value
            if status.startswith("5"):
                error_requests += sample.value
                per_handler_errors[handler] = per_handler_errors.get(handler, 0.0) + sample.value

        if sample.name == "http_request_duration_seconds_bucket":
            handler = sample.labels.get("handler", "")
            if not _is_runtime_handler(handler):
                continue
            le_raw = sample.labels.get("le")
            if le_raw is None:
                continue
            try:
                bound = _to_float_le(le_raw)
            except ValueError:
                continue
            global_buckets[bound] = global_buckets.get(bound, 0.0) + sample.value
            if handler not in per_handler_buckets:
                per_handler_buckets[handler] = {}
            per_handler_buckets[handler][bound] = (
                per_handler_buckets[handler].get(bound, 0.0) + sample.value
            )

    p95 = _quantile_from_buckets(global_buckets, 0.95)
    p99 = _quantile_from_buckets(global_buckets, 0.99)
    error_rate = (error_requests / total_requests) if total_requests > 0 else None

    handler_rows: list[dict[str, Any]] = []
    for handler, req_total in per_handler_totals.items():
        handler_error = per_handler_errors.get(handler, 0.0)
        handler_error_rate = (handler_error / req_total) if req_total > 0 else 0.0
        handler_p95 = _quantile_from_buckets(per_handler_buckets.get(handler, {}), 0.95)
        handler_rows.append(
            {
                "handler": handler,
                "requests": int(round(req_total)),
                "errors": int(round(handler_error)),
                "error_rate": round(handler_error_rate, 6),
                "p95_latency_seconds": round(handler_p95, 4) if handler_p95 is not None else None,
            }
        )

    handler_rows.sort(
        key=lambda row: (
            row["error_rate"],
            row["p95_latency_seconds"] if row["p95_latency_seconds"] is not None else -1.0,
            row["requests"],
        ),
        reverse=True,
    )

    return {
        "total_requests": int(round(total_requests)),
        "error_requests": int(round(error_requests)),
        "error_rate": round(error_rate, 6) if error_rate is not None else None,
        "p95_latency_seconds": round(p95, 4) if p95 is not None else None,
        "p99_latency_seconds": round(p99, 4) if p99 is not None else None,
        "handler_breakdown": handler_rows[:10],
    }


def _level_rank(level: str) -> int:
    return {"none": 0, "warn": 1, "critical": 2}.get(level, 0)


def _build_alerts(summary: dict[str, Any], args: argparse.Namespace) -> list[Alert]:
    alerts: list[Alert] = []
    total_requests = int(summary["total_requests"])
    error_rate = summary["error_rate"]
    p95 = summary["p95_latency_seconds"]

    if total_requests == 0:
        alerts.append(
            Alert(
                level="warn",
                source="runtime",
                message="No runtime traffic detected in scraped metrics.",
            )
        )
        return alerts

    if error_rate is None:
        alerts.append(
            Alert(
                level="warn",
                source="runtime",
                message="Error-rate could not be computed from metrics payload.",
            )
        )
    else:
        if error_rate >= args.error_rate_critical:
            alerts.append(
                Alert(
                    level="critical",
                    source="runtime",
                    message=(
                        f"Runtime error rate {error_rate:.2%} exceeds critical threshold "
                        f"{args.error_rate_critical:.2%}."
                    ),
                )
            )
        elif error_rate >= args.error_rate_slo:
            alerts.append(
                Alert(
                    level="warn",
                    source="runtime",
                    message=(
                        f"Runtime error rate {error_rate:.2%} exceeds SLO "
                        f"{args.error_rate_slo:.2%}."
                    ),
                )
            )

    if p95 is None:
        alerts.append(
            Alert(
                level="warn",
                source="runtime",
                message="p95 latency could not be derived from histogram buckets.",
            )
        )
    else:
        if p95 >= args.latency_p95_critical_seconds:
            alerts.append(
                Alert(
                    level="critical",
                    source="runtime",
                    message=(
                        f"Runtime p95 latency {p95:.3f}s exceeds critical threshold "
                        f"{args.latency_p95_critical_seconds:.3f}s."
                    ),
                )
            )
        elif p95 >= args.latency_p95_slo_seconds:
            alerts.append(
                Alert(
                    level="warn",
                    source="runtime",
                    message=(
                        f"Runtime p95 latency {p95:.3f}s exceeds SLO "
                        f"{args.latency_p95_slo_seconds:.3f}s."
                    ),
                )
            )

    return alerts


def _build_markdown(
    generated_at: str,
    metrics_source: str,
    thresholds: dict[str, float],
    summary: dict[str, Any],
    alerts: list[Alert],
) -> str:
    error_rate = summary["error_rate"]
    p95 = summary["p95_latency_seconds"]
    p99 = summary["p99_latency_seconds"]

    lines = [
        "# Runtime Observability Report",
        "",
        f"- Generated: `{generated_at}`",
        f"- Metrics Source: `{metrics_source}`",
        "",
        "## Runtime SLO Signals",
        "",
        "| Signal | Value | Threshold |",
        "| --- | ---: | ---: |",
        f"| Total Requests | {summary['total_requests']} | - |",
        f"| Error Requests | {summary['error_requests']} | - |",
        (
            "| Error Rate | "
            + ("n/a" if error_rate is None else f"{float(error_rate):.2%}")
            + f" | warn >= {thresholds['error_rate_slo']:.2%}, critical >= {thresholds['error_rate_critical']:.2%} |"
        ),
        (
            "| P95 Latency | "
            + ("n/a" if p95 is None else f"{float(p95):.3f}s")
            + f" | warn >= {thresholds['latency_p95_slo_seconds']:.3f}s, critical >= {thresholds['latency_p95_critical_seconds']:.3f}s |"
        ),
        (
            "| P99 Latency | "
            + ("n/a" if p99 is None else f"{float(p99):.3f}s")
            + " | - |"
        ),
        "",
        "## Top Handlers",
        "",
        "| Handler | Requests | Error Rate | P95 Latency |",
        "| --- | ---: | ---: | ---: |",
    ]
    rows = summary.get("handler_breakdown", [])
    if rows:
        for row in rows:
            row_error_rate = row["error_rate"]
            row_p95 = row["p95_latency_seconds"]
            lines.append(
                f"| `{row['handler']}` | {row['requests']} | {row_error_rate:.2%} | "
                f"{'n/a' if row_p95 is None else f'{row_p95:.3f}s'} |"
            )
    else:
        lines.append("| n/a | 0 | n/a | n/a |")

    lines.extend(["", "## Alerts", ""])
    if not alerts:
        lines.append("- None")
    else:
        for alert in alerts:
            lines.append(f"- [{alert.level.upper()}] {alert.source}: {alert.message}")
    lines.append("")
    return "\n".join(lines)


def run() -> int:
    args = parse_args()
    generated_at = datetime.now(UTC).isoformat()

    metrics_source = "metrics_file"
    scrape_error = None
    try:
        if args.metrics_file:
            metrics_text = Path(args.metrics_file).expanduser().read_text(encoding="utf-8")
            metrics_source = str(Path(args.metrics_file).expanduser().resolve())
        else:
            metrics_url = _resolve_metrics_url(args.metrics_url, args.api_url)
            metrics_text = _fetch_metrics_text(metrics_url, args.api_key, args.api_key_header)
            metrics_source = metrics_url
    except (ValueError, FileNotFoundError, urllib.error.URLError, TimeoutError) as exc:
        metrics_text = ""
        scrape_error = str(exc)

    summary = _build_runtime_summary(parse_prometheus_text(metrics_text)) if metrics_text else {
        "total_requests": 0,
        "error_requests": 0,
        "error_rate": None,
        "p95_latency_seconds": None,
        "p99_latency_seconds": None,
        "handler_breakdown": [],
    }

    thresholds = {
        "latency_p95_slo_seconds": args.latency_p95_slo_seconds,
        "latency_p95_critical_seconds": args.latency_p95_critical_seconds,
        "error_rate_slo": args.error_rate_slo,
        "error_rate_critical": args.error_rate_critical,
    }
    alerts = _build_alerts(summary, args)
    if scrape_error:
        alerts.append(
            Alert(
                level="critical",
                source="runtime",
                message=f"Metrics scrape failed: {scrape_error}",
            )
        )

    payload = {
        "generated_at": generated_at,
        "metrics_source": metrics_source,
        "thresholds": thresholds,
        "runtime": summary,
        "alerts": [
            {"level": alert.level, "source": alert.source, "message": alert.message}
            for alert in alerts
        ],
    }

    output_json = Path(args.output_json).expanduser().resolve()
    output_md = Path(args.output_md).expanduser().resolve()
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    output_md.write_text(
        _build_markdown(
            generated_at=generated_at,
            metrics_source=metrics_source,
            thresholds=thresholds,
            summary=summary,
            alerts=alerts,
        ),
        encoding="utf-8",
    )
    print(f"Wrote JSON: {output_json}")
    print(f"Wrote Markdown: {output_md}")

    if args.fail_on_alert_level != "none":
        threshold = _level_rank(args.fail_on_alert_level)
        if any(_level_rank(alert.level) >= threshold for alert in alerts):
            print(f"Failing due to alerts at or above '{args.fail_on_alert_level}'.")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

"""Read calibration reports and expose dashboard-friendly trend metrics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from typing import Any

from app.core.config import settings


class EvaluationStore:
    """Aggregates evaluation reports written by calibration scripts."""

    def _report_files(self) -> list[Path]:
        base = Path(settings.calibration_reports_dir).expanduser().resolve()
        if not base.exists():
            return []
        return sorted(base.glob("**/*.json"))

    def get_summary(self, days: int = 90) -> dict[str, Any]:
        window_days = max(1, min(days, 365))
        cutoff = datetime.now(UTC) - timedelta(days=window_days - 1)
        rows: list[dict[str, Any]] = []

        for file_path in self._report_files():
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue

            generated_at_raw = payload.get("generated_at")
            if not isinstance(generated_at_raw, str):
                continue
            try:
                generated_at = datetime.fromisoformat(generated_at_raw.replace("Z", "+00:00"))
            except ValueError:
                continue

            if generated_at.tzinfo is None:
                generated_at = generated_at.replace(tzinfo=UTC)
            if generated_at < cutoff:
                continue

            best_metrics = payload.get("best_metrics", {})
            rows.append(
                {
                    "generated_at": generated_at,
                    "generated_at_iso": generated_at.isoformat(),
                    "content_type": str(payload.get("content_type", "unknown")),
                    "sample_count": int(payload.get("sample_count", 0)),
                    "recommended_threshold": float(payload.get("recommended_threshold", 0.5)),
                    "precision": float(best_metrics.get("precision", 0.0)),
                    "recall": float(best_metrics.get("recall", 0.0)),
                    "f1": float(best_metrics.get("f1", 0.0)),
                    "accuracy": float(best_metrics.get("accuracy", 0.0)),
                }
            )

        rows.sort(key=lambda item: item["generated_at"])

        latest_by_type: dict[str, dict[str, Any]] = {}
        by_type_counts: dict[str, int] = {}
        for row in rows:
            content_type = row["content_type"]
            by_type_counts[content_type] = by_type_counts.get(content_type, 0) + 1
            latest_by_type[content_type] = {
                "generated_at": row["generated_at_iso"],
                "sample_count": row["sample_count"],
                "recommended_threshold": row["recommended_threshold"],
                "precision": row["precision"],
                "recall": row["recall"],
                "f1": row["f1"],
                "accuracy": row["accuracy"],
            }

        alerts: list[dict[str, str]] = []
        by_type_series: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            by_type_series.setdefault(row["content_type"], []).append(row)

        for content_type, series in by_type_series.items():
            if len(series) < 2:
                continue
            previous = series[-2]
            latest = series[-1]
            if latest["f1"] + 0.1 < previous["f1"]:
                alerts.append(
                    {
                        "severity": "medium",
                        "code": "f1_regression",
                        "message": f"{content_type} F1 dropped from {previous['f1']:.3f} to {latest['f1']:.3f}.",
                    }
                )

        trend = [
            {
                "date": row["generated_at"].date().isoformat(),
                "generated_at": row["generated_at_iso"],
                "content_type": row["content_type"],
                "sample_count": row["sample_count"],
                "threshold": row["recommended_threshold"],
                "precision": row["precision"],
                "recall": row["recall"],
                "f1": row["f1"],
                "accuracy": row["accuracy"],
            }
            for row in rows
        ]

        return {
            "window_days": window_days,
            "total_reports": len(rows),
            "by_content_type": by_type_counts,
            "latest_by_content_type": latest_by_type,
            "trend": trend,
            "alerts": alerts,
        }


evaluation_store = EvaluationStore()


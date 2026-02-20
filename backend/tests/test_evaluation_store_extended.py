"""Extended evaluation store tests for uncovered branches."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.services.evaluation_store import EvaluationStore


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> EvaluationStore:
    monkeypatch.setattr(
        "app.services.evaluation_store.settings",
        type("S", (), {"calibration_reports_dir": str(tmp_path)})(),
    )
    return EvaluationStore()


def _write_report(base: Path, name: str, payload: dict) -> None:
    path = base / name
    path.write_text(json.dumps(payload, default=str), encoding="utf-8")


class TestEvaluationStoreSummary:
    def test_empty_directory(self, store: EvaluationStore) -> None:
        result = store.get_summary(days=30)
        assert result["total_reports"] == 0
        assert result["trend"] == []

    def test_report_outside_window(self, store: EvaluationStore, tmp_path: Path) -> None:
        old_date = (datetime.now(UTC) - timedelta(days=200)).isoformat()
        _write_report(
            tmp_path,
            "old.json",
            {
                "generated_at": old_date,
                "content_type": "text",
                "sample_count": 10,
                "recommended_threshold": 0.5,
                "best_metrics": {"precision": 0.9, "recall": 0.8, "f1": 0.85, "accuracy": 0.88},
            },
        )
        result = store.get_summary(days=30)
        assert result["total_reports"] == 0

    def test_report_within_window(self, store: EvaluationStore, tmp_path: Path) -> None:
        recent_date = datetime.now(UTC).isoformat()
        _write_report(
            tmp_path,
            "recent.json",
            {
                "generated_at": recent_date,
                "content_type": "text",
                "sample_count": 50,
                "recommended_threshold": 0.55,
                "best_metrics": {"precision": 0.9, "recall": 0.85, "f1": 0.87, "accuracy": 0.9},
            },
        )
        result = store.get_summary(days=90)
        assert result["total_reports"] == 1
        assert result["by_content_type"]["text"] == 1
        assert result["latest_by_content_type"]["text"]["f1"] == 0.87

    def test_invalid_json_is_skipped(self, store: EvaluationStore, tmp_path: Path) -> None:
        (tmp_path / "broken.json").write_text("not json!", encoding="utf-8")
        result = store.get_summary()
        assert result["total_reports"] == 0

    def test_missing_generated_at_is_skipped(self, store: EvaluationStore, tmp_path: Path) -> None:
        _write_report(tmp_path, "no_date.json", {"content_type": "text"})
        result = store.get_summary()
        assert result["total_reports"] == 0

    def test_non_string_generated_at_is_skipped(
        self, store: EvaluationStore, tmp_path: Path
    ) -> None:
        _write_report(tmp_path, "bad_date.json", {"generated_at": 12345, "content_type": "text"})
        result = store.get_summary()
        assert result["total_reports"] == 0

    def test_invalid_date_format_is_skipped(self, store: EvaluationStore, tmp_path: Path) -> None:
        _write_report(
            tmp_path, "bad_format.json", {"generated_at": "not-a-date", "content_type": "text"}
        )
        result = store.get_summary()
        assert result["total_reports"] == 0

    def test_naive_datetime_gets_utc_timezone(self, store: EvaluationStore, tmp_path: Path) -> None:
        naive_date = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
        _write_report(
            tmp_path,
            "naive.json",
            {
                "generated_at": naive_date,
                "content_type": "image",
                "sample_count": 20,
                "recommended_threshold": 0.6,
                "best_metrics": {"precision": 0.8, "recall": 0.7, "f1": 0.75, "accuracy": 0.78},
            },
        )
        result = store.get_summary(days=7)
        assert result["total_reports"] == 1

    def test_f1_regression_alert(self, store: EvaluationStore, tmp_path: Path) -> None:
        now = datetime.now(UTC)
        _write_report(
            tmp_path,
            "report_01.json",
            {
                "generated_at": (now - timedelta(days=2)).isoformat(),
                "content_type": "text",
                "sample_count": 50,
                "recommended_threshold": 0.5,
                "best_metrics": {"precision": 0.9, "recall": 0.9, "f1": 0.9, "accuracy": 0.9},
            },
        )
        _write_report(
            tmp_path,
            "report_02.json",
            {
                "generated_at": now.isoformat(),
                "content_type": "text",
                "sample_count": 50,
                "recommended_threshold": 0.5,
                "best_metrics": {"precision": 0.7, "recall": 0.7, "f1": 0.7, "accuracy": 0.7},
            },
        )
        result = store.get_summary(days=30)
        assert result["total_reports"] == 2
        assert len(result["alerts"]) == 1
        assert result["alerts"][0]["code"] == "f1_regression"

    def test_no_regression_alert_when_f1_stable(
        self, store: EvaluationStore, tmp_path: Path
    ) -> None:
        now = datetime.now(UTC)
        _write_report(
            tmp_path,
            "stable_01.json",
            {
                "generated_at": (now - timedelta(days=1)).isoformat(),
                "content_type": "text",
                "sample_count": 50,
                "recommended_threshold": 0.5,
                "best_metrics": {"precision": 0.85, "recall": 0.85, "f1": 0.85, "accuracy": 0.85},
            },
        )
        _write_report(
            tmp_path,
            "stable_02.json",
            {
                "generated_at": now.isoformat(),
                "content_type": "text",
                "sample_count": 50,
                "recommended_threshold": 0.5,
                "best_metrics": {"precision": 0.84, "recall": 0.84, "f1": 0.84, "accuracy": 0.84},
            },
        )
        result = store.get_summary(days=30)
        assert result["alerts"] == []

    def test_days_clamp_min(self, store: EvaluationStore) -> None:
        result = store.get_summary(days=-5)
        assert result["window_days"] == 1

    def test_days_clamp_max(self, store: EvaluationStore) -> None:
        result = store.get_summary(days=9999)
        assert result["window_days"] == 365

    def test_nonexistent_reports_dir(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "app.services.evaluation_store.settings",
            type("S", (), {"calibration_reports_dir": "/tmp/does_not_exist_xyzzy"})(),
        )
        s = EvaluationStore()
        result = s.get_summary()
        assert result["total_reports"] == 0

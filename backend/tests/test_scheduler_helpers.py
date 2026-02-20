"""Tests for job scheduler helper functions and budget tracking."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.services.job_scheduler import _slug_handle, XPipelineScheduler


class TestSlugHandle:
    def test_strips_at_sign(self) -> None:
        assert _slug_handle("@user_name") == "user_name"

    def test_lowercases(self) -> None:
        assert _slug_handle("UserName") == "username"

    def test_replaces_special_chars_with_hyphen(self) -> None:
        assert _slug_handle("user.name!") == "user-name"

    def test_strips_leading_trailing_hyphens(self) -> None:
        assert _slug_handle("@---user---") == "user"

    def test_empty_returns_target(self) -> None:
        assert _slug_handle("") == "target"

    def test_whitespace_only_returns_target(self) -> None:
        assert _slug_handle("   ") == "target"


class TestUsageStatePersistence:
    def test_load_usage_state_missing_file(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(
            "app.services.job_scheduler.settings",
            type(
                "S",
                (),
                {
                    "scheduler_usage_file": str(tmp_path / "nonexistent.json"),
                    "scheduler_enabled": False,
                    "scheduler_handles": [],
                    "scheduler_monthly_request_cap": 0,
                    "scheduler_interval_minutes": 60,
                },
            )(),
        )
        scheduler = XPipelineScheduler()
        assert scheduler._usage_state == {"months": {}}

    def test_load_usage_state_corrupt_file(self, tmp_path: Path, monkeypatch) -> None:
        usage_file = tmp_path / "usage.json"
        usage_file.write_text("not json", encoding="utf-8")
        monkeypatch.setattr(
            "app.services.job_scheduler.settings",
            type(
                "S",
                (),
                {
                    "scheduler_usage_file": str(usage_file),
                    "scheduler_enabled": False,
                    "scheduler_handles": [],
                    "scheduler_monthly_request_cap": 0,
                    "scheduler_interval_minutes": 60,
                },
            )(),
        )
        scheduler = XPipelineScheduler()
        assert scheduler._usage_state == {"months": {}}

    def test_save_and_reload_usage(self, tmp_path: Path, monkeypatch) -> None:
        usage_file = tmp_path / "usage.json"
        settings_mock = type(
            "S",
            (),
            {
                "scheduler_usage_file": str(usage_file),
                "scheduler_enabled": False,
                "scheduler_handles": [],
                "scheduler_monthly_request_cap": 1000,
                "scheduler_interval_minutes": 60,
            },
        )()
        monkeypatch.setattr("app.services.job_scheduler.settings", settings_mock)
        scheduler = XPipelineScheduler()
        scheduler._record_consumed_requests(42)

        assert usage_file.exists()
        data = json.loads(usage_file.read_text(encoding="utf-8"))
        month_key = scheduler._month_key()
        assert data["months"][month_key]["requests_used"] == 42


class TestMonthlyBudget:
    def test_budget_no_cap(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(
            "app.services.job_scheduler.settings",
            type(
                "S",
                (),
                {
                    "scheduler_usage_file": str(tmp_path / "usage.json"),
                    "scheduler_enabled": False,
                    "scheduler_handles": [],
                    "scheduler_monthly_request_cap": 0,
                    "scheduler_interval_minutes": 60,
                },
            )(),
        )
        scheduler = XPipelineScheduler()
        budget = scheduler._monthly_budget()
        assert budget["cap_requests"] == 0
        assert budget["remaining_requests"] is None

    def test_budget_with_cap(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(
            "app.services.job_scheduler.settings",
            type(
                "S",
                (),
                {
                    "scheduler_usage_file": str(tmp_path / "usage.json"),
                    "scheduler_enabled": False,
                    "scheduler_handles": [],
                    "scheduler_monthly_request_cap": 100,
                    "scheduler_interval_minutes": 60,
                },
            )(),
        )
        scheduler = XPipelineScheduler()
        budget = scheduler._monthly_budget()
        assert budget["cap_requests"] == 100
        assert budget["remaining_requests"] == 100


class TestMonthKey:
    def test_format(self) -> None:
        now = datetime(2026, 2, 15, tzinfo=UTC)
        assert XPipelineScheduler._month_key(now) == "2026-02"

    def test_defaults_to_now(self) -> None:
        key = XPipelineScheduler._month_key()
        assert len(key) == 7
        assert key[4] == "-"

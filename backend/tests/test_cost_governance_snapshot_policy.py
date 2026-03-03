from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "cost_governance_snapshot.py"


spec = importlib.util.spec_from_file_location("cost_governance_snapshot", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


@pytest.fixture(autouse=True)
def _reset_runtime_state():
    """Override global async DB fixture for pure script-level tests."""
    yield


def test_evaluate_budget_status_warn_and_block() -> None:
    policy = {
        "policy_version": "test-v1",
        "monthly_cap_usd": 10.0,
        "warn_threshold_pct": 50.0,
        "block_threshold_pct": 80.0,
        "non_essential_workflows": ["Publish Service Images"],
        "cost_model": {
            "github_actions_usd_per_minute": 0.1,
            "vercel_usd_per_deployment": 0.0,
        },
    }

    warn_state = module._evaluate_budget_status(
        github_summary={"total_runtime_minutes": 60.0},
        vercel_summary={"status": "ok", "total_deployments": 0},
        policy=policy,
        workflow_name="Publish Service Images",
    )
    assert warn_state["status"] == "warn"
    assert warn_state["remaining_budget"] == 4.0
    assert warn_state["non_essential_allowed"] is True

    block_state = module._evaluate_budget_status(
        github_summary={"total_runtime_minutes": 90.0},
        vercel_summary={"status": "ok", "total_deployments": 0},
        policy=policy,
        workflow_name="Publish Service Images",
    )
    assert block_state["status"] == "block"
    assert block_state["non_essential_allowed"] is False


def test_load_policy_from_json_text(tmp_path: Path) -> None:
    policy_path = tmp_path / "cost_policy.yaml"
    policy_path.write_text(
        json.dumps(
            {
                "policy_version": "json-policy-v2",
                "monthly_cap_usd": 75,
                "warn_threshold_pct": 70,
                "block_threshold_pct": 90,
                "override_label": "override-me",
                "non_essential_workflows": ["Public Provenance Benchmark"],
                "cost_model": {
                    "github_actions_usd_per_minute": 0.02,
                    "vercel_usd_per_deployment": 0.03,
                },
            }
        ),
        encoding="utf-8",
    )

    loaded = module._load_policy(policy_path)

    assert loaded["policy_version"] == "json-policy-v2"
    assert loaded["monthly_cap_usd"] == 75
    assert loaded["override_label"] == "override-me"
    assert loaded["cost_model"]["github_actions_usd_per_minute"] == 0.02

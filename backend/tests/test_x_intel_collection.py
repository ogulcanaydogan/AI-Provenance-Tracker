from unittest.mock import patch

import httpx
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.services.job_scheduler import XPipelineScheduler
from app.services.x_intel import XIntelCollector


def _json_response(url: str, payload: dict, status_code: int = 200) -> httpx.Response:
    request = httpx.Request("GET", f"https://api.x.com{url}")
    return httpx.Response(status_code=status_code, json=payload, request=request)


@pytest.mark.asyncio
async def test_collect_x_intel_returns_schema_payload(client: AsyncClient):
    old_token = settings.x_bearer_token
    settings.x_bearer_token = "test-token"

    async def fake_get(self, url, **kwargs):  # noqa: ARG001
        path = str(url)

        if "/users/by/username/targetacct" in path:
            return _json_response(
                path,
                {
                    "data": {
                        "id": "111",
                        "username": "targetacct",
                        "created_at": "2023-01-01T00:00:00.000Z",
                        "verified": True,
                        "public_metrics": {"followers_count": 5000, "following_count": 300},
                        "description": "Official account",
                    }
                },
            )

        if "/users/111/tweets" in path:
            return _json_response(
                path,
                {
                    "data": [
                        {
                            "id": "1001",
                            "author_id": "111",
                            "created_at": "2026-02-11T10:00:00.000Z",
                            "text": "Official update #yapay https://example.com/update",
                            "lang": "en",
                            "public_metrics": {
                                "like_count": 10,
                                "retweet_count": 3,
                                "reply_count": 1,
                                "impression_count": 1000,
                            },
                            "entities": {
                                "hashtags": [{"tag": "yapay"}],
                                "urls": [{"expanded_url": "https://example.com/update"}],
                            },
                            "attachments": {"media_keys": ["3_1"]},
                        }
                    ],
                    "includes": {
                        "users": [
                            {
                                "id": "111",
                                "username": "targetacct",
                                "created_at": "2023-01-01T00:00:00.000Z",
                                "verified": True,
                                "public_metrics": {"followers_count": 5000, "following_count": 300},
                            }
                        ],
                        "media": [
                            {
                                "media_key": "3_1",
                                "type": "photo",
                                "url": "https://pbs.twimg.com/media/img1.jpg",
                            }
                        ],
                    },
                },
            )

        if "/users/111/mentions" in path:
            return _json_response(
                path,
                {
                    "data": [
                        {
                            "id": "2001",
                            "author_id": "222",
                            "created_at": "2026-02-11T10:08:00.000Z",
                            "text": "Breaking #yapay https://example.com/update",
                            "lang": "en",
                            "public_metrics": {"like_count": 1, "retweet_count": 1, "reply_count": 0},
                            "entities": {
                                "hashtags": [{"tag": "yapay"}],
                                "urls": [{"expanded_url": "https://example.com/update"}],
                                "mentions": [{"username": "targetacct"}],
                            },
                            "referenced_tweets": [{"type": "replied_to", "id": "1001"}],
                        },
                        {
                            "id": "2002",
                            "author_id": "333",
                            "created_at": "2026-02-11T10:15:00.000Z",
                            "text": "Breaking #yapay https://example.com/update",
                            "lang": "en",
                            "public_metrics": {"like_count": 2, "retweet_count": 2, "reply_count": 0},
                            "entities": {
                                "hashtags": [{"tag": "yapay"}],
                                "urls": [{"expanded_url": "https://example.com/update"}],
                                "mentions": [{"username": "targetacct"}],
                            },
                            "referenced_tweets": [{"type": "replied_to", "id": "1001"}],
                        },
                    ],
                    "includes": {
                        "users": [
                            {
                                "id": "222",
                                "username": "amplifier_a",
                                "created_at": "2026-02-01T00:00:00.000Z",
                                "verified": False,
                                "public_metrics": {"followers_count": 15, "following_count": 900},
                            },
                            {
                                "id": "333",
                                "username": "amplifier_b",
                                "created_at": "2026-01-15T00:00:00.000Z",
                                "verified": False,
                                "public_metrics": {"followers_count": 20, "following_count": 800},
                            },
                        ]
                    },
                },
            )

        if "/tweets/search/recent" in path:
            return _json_response(
                path,
                {
                    "data": [
                        {
                            "id": "3001",
                            "author_id": "444",
                            "created_at": "2026-02-11T10:20:00.000Z",
                            "text": "Breaking #yapay https://example.com/update",
                            "lang": "en",
                            "public_metrics": {"like_count": 0, "retweet_count": 1, "reply_count": 0},
                            "entities": {
                                "hashtags": [{"tag": "yapay"}],
                                "urls": [{"expanded_url": "https://example.com/update"}],
                                "mentions": [{"username": "targetacct"}],
                            },
                            "referenced_tweets": [{"type": "quoted", "id": "1001"}],
                        }
                    ],
                    "includes": {
                        "users": [
                            {
                                "id": "444",
                                "username": "bridge_user",
                                "created_at": "2025-12-20T00:00:00.000Z",
                                "verified": False,
                                "public_metrics": {"followers_count": 30, "following_count": 200},
                            }
                        ]
                    },
                },
            )

        return _json_response(path, {"data": []})

    try:
        with patch.object(httpx.AsyncClient, "get", new=fake_get):
            response = await client.post(
                "/api/v1/intel/x/collect",
                json={
                    "target_handle": "@targetacct",
                    "window_days": 14,
                    "max_posts": 120,
                    "query": "anthropic OR claudecode",
                    "user_context": {
                        "sector": "fintech",
                        "risk_tolerance": "medium",
                        "preferred_language": "tr",
                        "user_profile": "brand",
                        "legal_pr_capacity": "basic",
                        "goal": "reputation_protection",
                    },
                },
            )
    finally:
        settings.x_bearer_token = old_token

    assert response.status_code == 200
    payload = response.json()
    assert payload["target"] == "@targetacct"
    assert "window" in payload
    assert len(payload["posts"]) >= 4
    assert "network_signals" in payload
    assert "coordinated_clusters" in payload["network_signals"]
    assert payload["network_signals"]["coordinated_clusters"]
    assert payload["bot_scores"]
    assert len(payload["ai_content_scores"]) == len(payload["posts"])
    assert payload["claim_clusters"]
    assert payload["user_context"]["goal"] == "reputation_protection"


@pytest.mark.asyncio
async def test_collect_x_intel_requires_token(client: AsyncClient):
    old_token = settings.x_bearer_token
    settings.x_bearer_token = ""

    try:
        response = await client.post(
            "/api/v1/intel/x/collect",
            json={"target_handle": "@targetacct", "window_days": 14, "max_posts": 100},
        )
    finally:
        settings.x_bearer_token = old_token

    assert response.status_code == 400
    assert "X_BEARER_TOKEN" in response.json()["detail"]


def test_estimate_request_plan_low_cost():
    plan = XIntelCollector.estimate_request_plan(max_posts=60, max_pages=1)
    assert plan["estimated_requests"] == 4
    assert plan["worst_case_requests"] == 4
    assert plan["page_cap"] == 1


@pytest.mark.asyncio
async def test_collect_x_intel_budget_guard_blocks_large_run(client: AsyncClient):
    old_token = settings.x_bearer_token
    old_guard_enabled = settings.x_cost_guard_enabled
    old_max_requests = settings.x_max_requests_per_run
    old_max_pages = settings.x_max_pages

    settings.x_bearer_token = "test-token"
    settings.x_cost_guard_enabled = True
    settings.x_max_requests_per_run = 3
    settings.x_max_pages = 1
    try:
        response = await client.post(
            "/api/v1/intel/x/collect",
            json={"target_handle": "@targetacct", "window_days": 7, "max_posts": 60},
        )
    finally:
        settings.x_bearer_token = old_token
        settings.x_cost_guard_enabled = old_guard_enabled
        settings.x_max_requests_per_run = old_max_requests
        settings.x_max_pages = old_max_pages

    assert response.status_code == 400
    assert "exceeds budget" in response.json()["detail"]


@pytest.mark.asyncio
async def test_collect_x_intel_estimate_endpoint(client: AsyncClient):
    old_guard_enabled = settings.x_cost_guard_enabled
    old_max_requests = settings.x_max_requests_per_run
    old_max_pages = settings.x_max_pages

    settings.x_cost_guard_enabled = True
    settings.x_max_requests_per_run = 4
    settings.x_max_pages = 1
    try:
        response = await client.post(
            "/api/v1/intel/x/collect/estimate",
            json={"window_days": 7, "max_posts": 60, "max_pages": 1},
        )
    finally:
        settings.x_cost_guard_enabled = old_guard_enabled
        settings.x_max_requests_per_run = old_max_requests
        settings.x_max_pages = old_max_pages

    assert response.status_code == 200
    payload = response.json()
    assert payload["estimated_requests"] == 4
    assert payload["within_budget"] is True
    assert payload["max_requests_per_run"] == 4
    assert payload["recommended_max_posts"] >= 60


@pytest.mark.asyncio
async def test_scheduler_monthly_cap_activates_kill_switch(tmp_path):
    old_usage_file = settings.scheduler_usage_file
    old_cap = settings.scheduler_monthly_request_cap
    old_kill = settings.scheduler_kill_switch_on_cap
    old_scheduler_max_posts = settings.scheduler_max_posts
    old_x_max_pages = settings.x_max_pages
    old_send_webhooks = settings.scheduler_send_webhooks

    settings.scheduler_usage_file = str(tmp_path / "scheduler_usage.json")
    settings.scheduler_monthly_request_cap = 3
    settings.scheduler_kill_switch_on_cap = True
    settings.scheduler_max_posts = 60
    settings.x_max_pages = 1
    settings.scheduler_send_webhooks = False
    try:
        scheduler = XPipelineScheduler()
        first = await scheduler.trigger_once(handle="@targetacct")
        status = scheduler.status()
        second = await scheduler.trigger_once(handle="@targetacct")
    finally:
        settings.scheduler_usage_file = old_usage_file
        settings.scheduler_monthly_request_cap = old_cap
        settings.scheduler_kill_switch_on_cap = old_kill
        settings.scheduler_max_posts = old_scheduler_max_posts
        settings.x_max_pages = old_x_max_pages
        settings.scheduler_send_webhooks = old_send_webhooks

    assert first["status"] == "blocked"
    assert first["reason"] == "monthly_request_cap"
    assert first.get("kill_switch_activated") is True
    assert status["auto_disabled"] is True
    assert status["enabled"] is False
    assert second["status"] == "blocked"
    assert second["reason"] == "kill_switch_active"


@pytest.mark.asyncio
async def test_scheduler_status_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/intel/x/scheduler/status")
    assert response.status_code == 200
    payload = response.json()
    assert "enabled" in payload
    assert "handles" in payload
    assert "running" in payload


@pytest.mark.asyncio
async def test_scheduler_run_endpoint_without_handles(client: AsyncClient):
    old_handles = list(settings.scheduler_handles)
    settings.scheduler_handles = []
    try:
        response = await client.post("/api/v1/intel/x/scheduler/run")
    finally:
        settings.scheduler_handles = old_handles

    assert response.status_code == 200
    payload = response.json()
    assert payload["triggered"] == 0

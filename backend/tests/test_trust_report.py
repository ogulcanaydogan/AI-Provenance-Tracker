import pytest
from httpx import AsyncClient

from app.services.trust_report import generate_trust_report


def _sample_input_payload() -> dict:
    return {
        "target": "@sample",
        "window": "2026-02-01/2026-02-15",
        "posts": [
            {
                "tweet_id": "1",
                "created_at": "2026-02-15T12:00:00.000Z",
                "text": "Breaking update #topic @team",
                "lang": "en",
                "media_urls": [],
                "metrics": {"likes": 3, "reposts": 1, "replies": 0, "views": 120},
                "author": {
                    "user_id": "u1",
                    "handle": "acct1",
                    "created_at": "2022-01-01T00:00:00.000Z",
                    "followers": 100,
                    "following": 50,
                    "verified": False,
                    "profile_fields": {},
                },
                "reply_to": None,
                "quoted_tweet_id": None,
                "urls": [],
                "hashtags": ["topic"],
                "mentions": ["team"],
            },
            {
                "tweet_id": "2",
                "created_at": "2026-02-15T12:05:00.000Z",
                "text": "Another update #topic",
                "lang": "en",
                "media_urls": [],
                "metrics": {"likes": 1, "reposts": 0, "replies": 0, "views": 80},
                "author": {
                    "user_id": "u2",
                    "handle": "acct2",
                    "created_at": "2023-01-01T00:00:00.000Z",
                    "followers": 30,
                    "following": 80,
                    "verified": False,
                    "profile_fields": {},
                },
                "reply_to": None,
                "quoted_tweet_id": None,
                "urls": [],
                "hashtags": ["topic"],
                "mentions": [],
            },
        ],
        "network_signals": {
            "coordinated_clusters": [],
            "amplification_graph_metrics": {
                "density": 0.1,
                "modularity": 0.0,
                "central_accounts": [{"handle": "acct1", "score": 0.5}],
            },
        },
        "bot_scores": [
            {
                "user_id": "u1",
                "handle": "acct1",
                "bot_probability": 0.2,
                "top_features": [
                    {
                        "feature": "posts_per_day",
                        "value": "2.0",
                        "why_it_matters": "Velocity hint",
                    }
                ],
                "confidence": "medium",
            }
        ],
        "ai_content_scores": [
            {
                "tweet_id": "1",
                "ai_text_probability": 0.3,
                "ai_image_probability": 0.0,
                "provenance_notes": ["No provenance"],
                "confidence": "medium",
            }
        ],
        "claim_clusters": [
            {
                "cluster_id": "c1",
                "topic_label": "breaking",
                "representative_claims": ["Breaking update claim"],
                "spread_over_time": "2026-02-15: 12",
                "key_accounts": ["acct1"],
                "sentiment": "neutral",
            }
        ],
        "user_context": {
            "sector": "fintech",
            "risk_tolerance": "medium",
            "preferred_language": "tr",
            "user_profile": "brand",
            "legal_pr_capacity": "basic",
            "goal": "reputation_protection",
        },
    }


def test_generate_trust_report_schema_keys():
    report = generate_trust_report(_sample_input_payload())
    assert "executive_summary" in report
    assert "timeline" in report
    assert "bot_activity" in report
    assert "ai_generated_content" in report
    assert "claims_and_narratives" in report
    assert "recommended_strategy" in report
    assert "data_gaps" in report
    assert "confidence_overall" in report


@pytest.mark.asyncio
async def test_x_report_endpoint(client: AsyncClient):
    response = await client.post("/api/v1/intel/x/report", json=_sample_input_payload())
    assert response.status_code == 200
    payload = response.json()
    assert payload["executive_summary"]["risk_level"] in {"low", "medium", "high", "critical"}
    assert isinstance(payload["timeline"], list)
    assert isinstance(payload["claims_and_narratives"], list)


@pytest.mark.asyncio
async def test_x_drilldown_endpoint(client: AsyncClient):
    response = await client.post("/api/v1/intel/x/drilldown", json=_sample_input_payload())
    assert response.status_code == 200
    payload = response.json()
    assert payload["target"] == "@sample"
    assert "clusters" in payload
    assert "claim_timeline" in payload
    assert "alerts" in payload

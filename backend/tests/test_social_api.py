from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.api.v1.detect import PLATFORM_MEDIA_MISSING_DETAIL
from app.core.config import settings
from app.services.instagram_client import instagram_client
from app.services.social_intake import social_intake_service


def _comment_webhook_payload() -> dict:
    return {
        "object": "instagram",
        "entry": [
            {
                "id": "1789",
                "time": 1710000000,
                "changes": [
                    {
                        "field": "comments",
                        "value": {
                            "id": "comment-1",
                            "text": "@whoisfake is this AI?",
                            "from": {"id": "igsid-commenter", "username": "reader"},
                            "media": {
                                "id": "media-1",
                                "permalink": "https://www.instagram.com/p/OWNEDMEDIA/",
                            },
                        },
                    }
                ],
            }
        ],
    }


def _mention_webhook_payload() -> dict:
    return {
        "object": "instagram",
        "entry": [
            {
                "id": "1790",
                "time": 1710000001,
                "changes": [
                    {
                        "field": "mentions",
                        "value": {
                            "media_id": "media-2",
                            "permalink": "https://www.instagram.com/reel/ABC123/",
                            "from": {"id": "igsid-mentioner", "username": "sourceuser"},
                        },
                    }
                ],
            }
        ],
    }


@pytest.mark.asyncio
async def test_instagram_webhook_verification_challenge(client: AsyncClient):
    old_token = settings.instagram_webhook_verify_token
    settings.instagram_webhook_verify_token = "verify-me"
    try:
        response = await client.get(
            "/api/v1/social/instagram/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "verify-me",
                "hub.challenge": "12345",
            },
        )
    finally:
        settings.instagram_webhook_verify_token = old_token

    assert response.status_code == 200
    assert response.text == "12345"


@pytest.mark.asyncio
async def test_instagram_webhook_deduplicates_duplicate_events(client: AsyncClient):
    payload = _comment_webhook_payload()

    response_1 = await client.post("/api/v1/social/instagram/webhook", json=payload)
    response_2 = await client.post("/api/v1/social/instagram/webhook", json=payload)

    assert response_1.status_code == 200
    assert response_1.json() == {"received": 1, "queued": 1, "duplicates": 0}
    assert response_2.status_code == 200
    assert response_2.json() == {"received": 1, "queued": 0, "duplicates": 1}

    list_response = await client.get("/api/v1/social/events")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["reply_channel"] == "public_comment"
    assert payload["items"][0]["status"] == "pending"


@pytest.mark.asyncio
async def test_social_process_own_post_comment_replies_publicly(client: AsyncClient):
    enqueue_response = await client.post(
        "/api/v1/social/instagram/webhook", json=_comment_webhook_payload()
    )
    assert enqueue_response.status_code == 200

    with (
        patch.object(
            social_intake_service,
            "_analyze_source_url",
            AsyncMock(
                return_value={
                    "analysis_id": "analysis-comment-1",
                    "content_type": "video",
                    "result": {"confidence": 0.88, "is_ai_generated": True},
                }
            ),
        ),
        patch.object(
            instagram_client,
            "reply_to_comment",
            AsyncMock(return_value={"id": "reply-123"}),
        ) as reply_mock,
    ):
        response = await client.post("/api/v1/social/events/process")

    assert response.status_code == 200
    assert response.json()["completed"] == 1
    reply_mock.assert_awaited_once()
    sent_message = reply_mock.await_args.kwargs["message"]
    assert "AI likely" in sent_message
    assert "/api/v1/analyze/evidence/analysis-comment-1" in sent_message

    list_response = await client.get("/api/v1/social/events")
    item = list_response.json()["items"][0]
    assert item["status"] == "completed"
    assert item["analysis_id"] == "analysis-comment-1"
    assert item["response_status"] == "public_comment_sent"


@pytest.mark.asyncio
async def test_social_process_third_party_mention_replies_via_dm(client: AsyncClient):
    enqueue_response = await client.post(
        "/api/v1/social/instagram/webhook", json=_mention_webhook_payload()
    )
    assert enqueue_response.status_code == 200

    with (
        patch.object(
            social_intake_service,
            "_analyze_source_url",
            AsyncMock(
                return_value={
                    "analysis_id": "analysis-mention-1",
                    "content_type": "text",
                    "result": {"confidence": 0.41, "decision_band": "uncertain"},
                }
            ),
        ),
        patch.object(
            instagram_client,
            "send_text_message",
            AsyncMock(return_value={"message_id": "mid-42"}),
        ) as dm_mock,
    ):
        response = await client.post("/api/v1/social/events/process")

    assert response.status_code == 200
    assert response.json()["completed"] == 1
    dm_mock.assert_awaited_once()
    sent_message = dm_mock.await_args.kwargs["message"]
    assert "Uncertain" in sent_message
    assert "/api/v1/analyze/evidence/analysis-mention-1" in sent_message

    list_response = await client.get("/api/v1/social/events")
    item = list_response.json()["items"][0]
    assert item["reply_channel"] == "dm"
    assert item["response_status"] == "dm_sent"


@pytest.mark.asyncio
async def test_social_process_falls_back_when_public_media_missing(client: AsyncClient):
    enqueue_response = await client.post(
        "/api/v1/social/instagram/webhook", json=_mention_webhook_payload()
    )
    assert enqueue_response.status_code == 200

    with (
        patch.object(
            social_intake_service,
            "_analyze_source_url",
            AsyncMock(side_effect=HTTPException(status_code=400, detail=PLATFORM_MEDIA_MISSING_DETAIL)),
        ),
        patch.object(
            instagram_client,
            "send_text_message",
            AsyncMock(return_value={"message_id": "mid-fallback"}),
        ) as dm_mock,
    ):
        response = await client.post("/api/v1/social/events/process")

    assert response.status_code == 200
    assert response.json()["completed"] == 1
    dm_mock.assert_awaited_once()
    sent_message = dm_mock.await_args.kwargs["message"]
    assert "public direct media" in sent_message.lower()
    assert "/detect/url" in sent_message

    list_response = await client.get("/api/v1/social/events")
    item = list_response.json()["items"][0]
    assert item["status"] == "completed"
    assert item["response_status"] == "fallback_no_public_media"


@pytest.mark.asyncio
async def test_instagram_webhook_rejects_invalid_signature_when_secret_configured(
    client: AsyncClient,
):
    old_secret = settings.instagram_webhook_app_secret
    settings.instagram_webhook_app_secret = "app-secret"
    try:
        response = await client.post(
            "/api/v1/social/instagram/webhook",
            json=_mention_webhook_payload(),
            headers={"X-Hub-Signature-256": "sha256=wrong"},
        )
    finally:
        settings.instagram_webhook_app_secret = old_secret

    assert response.status_code == 403
    assert "invalid instagram webhook signature" in response.json()["detail"].lower()

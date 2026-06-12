"""Unit tests for InstagramClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.instagram_client import InstagramClient, InstagramClientError


@pytest.fixture()
def enabled_settings():
    with (
        patch("app.services.instagram_client.settings") as mock_settings,
    ):
        mock_settings.instagram_enabled = True
        mock_settings.instagram_access_token = "test-token"
        mock_settings.instagram_business_account_id = "ig-biz-123"
        mock_settings.instagram_graph_api_base_url = "https://graph.instagram.com/v25.0"
        mock_settings.instagram_reply_timeout_seconds = 5.0
        yield mock_settings


@pytest.fixture()
def disabled_settings():
    with patch("app.services.instagram_client.settings") as mock_settings:
        mock_settings.instagram_enabled = False
        mock_settings.instagram_access_token = "test-token"
        mock_settings.instagram_business_account_id = "ig-biz-123"
        mock_settings.instagram_graph_api_base_url = "https://graph.instagram.com/v25.0"
        mock_settings.instagram_reply_timeout_seconds = 5.0
        yield mock_settings


class TestEnsureEnabled:
    def test_raises_when_disabled(self, disabled_settings) -> None:
        with pytest.raises(InstagramClientError, match="disabled"):
            InstagramClient._ensure_enabled()

    def test_raises_when_token_blank(self, enabled_settings) -> None:
        enabled_settings.instagram_access_token = "   "
        with pytest.raises(InstagramClientError, match="access token"):
            InstagramClient._ensure_enabled()

    def test_passes_when_configured(self, enabled_settings) -> None:
        InstagramClient._ensure_enabled()  # should not raise


class TestSendTextMessage:
    @pytest.mark.asyncio
    async def test_success(self, enabled_settings) -> None:
        client = InstagramClient()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message_id": "msg-1"}

        with patch("app.services.instagram_client.httpx.AsyncClient") as mock_http:
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            result = await client.send_text_message(recipient_id="user-456", message="Hello")

        assert result == {"message_id": "msg-1"}

    @pytest.mark.asyncio
    async def test_raises_when_recipient_blank(self, enabled_settings) -> None:
        client = InstagramClient()
        with pytest.raises(InstagramClientError, match="recipient id is required"):
            await client.send_text_message(recipient_id="  ", message="Hello")

    @pytest.mark.asyncio
    async def test_raises_when_biz_account_missing(self, enabled_settings) -> None:
        enabled_settings.instagram_business_account_id = ""
        client = InstagramClient()
        with pytest.raises(InstagramClientError, match="business account id"):
            await client.send_text_message(recipient_id="user-1", message="Hi")


class TestReplyToComment:
    @pytest.mark.asyncio
    async def test_success(self, enabled_settings) -> None:
        client = InstagramClient()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "reply-789"}

        with patch("app.services.instagram_client.httpx.AsyncClient") as mock_http:
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            result = await client.reply_to_comment(comment_id="comment-1", message="Thanks!")

        assert result == {"id": "reply-789"}

    @pytest.mark.asyncio
    async def test_raises_when_comment_id_blank(self, enabled_settings) -> None:
        client = InstagramClient()
        with pytest.raises(InstagramClientError, match="comment id is required"):
            await client.reply_to_comment(comment_id="", message="Reply")


class TestPostJson:
    @pytest.mark.asyncio
    async def test_raises_on_http_error(self, enabled_settings) -> None:
        client = InstagramClient()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch("app.services.instagram_client.httpx.AsyncClient") as mock_http:
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            with pytest.raises(InstagramClientError, match="Unauthorized"):
                await client._post_json("https://example.com", {})

    @pytest.mark.asyncio
    async def test_raises_on_malformed_response(self, enabled_settings) -> None:
        client = InstagramClient()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = ["not", "a", "dict"]

        with patch("app.services.instagram_client.httpx.AsyncClient") as mock_http:
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            with pytest.raises(InstagramClientError, match="malformed"):
                await client._post_json("https://example.com", {})

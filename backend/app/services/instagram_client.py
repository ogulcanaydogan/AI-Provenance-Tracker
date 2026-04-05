"""Instagram Graph API reply helpers for DMs and owned-media comment replies."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


class InstagramClientError(Exception):
    """Raised when Instagram API configuration or delivery fails."""


class InstagramClient:
    """Small adapter around the Instagram Graph API."""

    @staticmethod
    def _base_url() -> str:
        return settings.instagram_graph_api_base_url.rstrip("/")

    @staticmethod
    def _ensure_enabled() -> None:
        if not settings.instagram_enabled:
            raise InstagramClientError("Instagram integration is disabled")
        if not settings.instagram_access_token.strip():
            raise InstagramClientError("Instagram access token is not configured")

    @staticmethod
    def _headers() -> dict[str, str]:
        return {"Authorization": f"Bearer {settings.instagram_access_token.strip()}"}

    async def send_text_message(self, *, recipient_id: str, message: str) -> dict[str, Any]:
        """Send a DM reply to a user who already messaged the professional account."""
        self._ensure_enabled()
        ig_id = settings.instagram_business_account_id.strip()
        if not ig_id:
            raise InstagramClientError("Instagram business account id is not configured")
        if not recipient_id.strip():
            raise InstagramClientError("Instagram recipient id is required")

        payload = {
            "recipient": {"id": recipient_id.strip()},
            "message": {"text": message},
        }
        return await self._post_json(f"{self._base_url()}/{ig_id}/messages", payload)

    async def reply_to_comment(self, *, comment_id: str, message: str) -> dict[str, Any]:
        """Reply publicly to a comment on media owned by the professional account."""
        self._ensure_enabled()
        if not comment_id.strip():
            raise InstagramClientError("Instagram comment id is required")

        payload = {"message": message}
        return await self._post_json(f"{self._base_url()}/{comment_id}/replies", payload)

    async def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        timeout = max(2.0, float(settings.instagram_reply_timeout_seconds))
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=self._headers())
        if response.status_code >= 400:
            detail = response.text[:500] or f"HTTP {response.status_code}"
            raise InstagramClientError(detail)
        data = response.json()
        if not isinstance(data, dict):
            raise InstagramClientError("Instagram API returned malformed response")
        return data


instagram_client = InstagramClient()

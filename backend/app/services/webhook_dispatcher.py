"""Webhook delivery helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class WebhookDispatcher:
    """Sends JSON events to configured webhook URLs."""

    async def dispatch(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not settings.webhook_urls:
            return {"sent": 0, "delivered": 0, "results": []}

        body = {"event_type": event_type, "payload": payload}
        encoded = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        signature = self._signature(encoded)

        results: list[dict[str, Any]] = []
        delivered = 0
        async with httpx.AsyncClient(timeout=settings.webhook_timeout_seconds) as client:
            for url in settings.webhook_urls:
                headers = {"Content-Type": "application/json"}
                if signature:
                    headers["X-Webhook-Signature"] = signature
                try:
                    response = await client.post(url, content=encoded, headers=headers)
                    ok = response.status_code < 400
                    if ok:
                        delivered += 1
                    results.append(
                        {
                            "url": url,
                            "status_code": response.status_code,
                            "ok": ok,
                        }
                    )
                except httpx.HTTPError as exc:
                    logger.warning("webhook_delivery_error", url=url, error=str(exc))
                    results.append({"url": url, "status_code": None, "ok": False, "error": str(exc)})

        return {"sent": len(settings.webhook_urls), "delivered": delivered, "results": results}

    @staticmethod
    def _signature(payload: bytes) -> str:
        if not settings.webhook_secret:
            return ""
        digest = hmac.new(
            settings.webhook_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return f"sha256={digest}"


webhook_dispatcher = WebhookDispatcher()


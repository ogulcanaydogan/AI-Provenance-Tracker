"""Webhook delivery helpers with retry queue and dead-letter logging."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class WebhookDispatcher:
    """Sends JSON events to configured webhook URLs."""

    @staticmethod
    def _queue_path() -> Path:
        return Path(settings.webhook_queue_file).expanduser().resolve()

    @staticmethod
    def _dead_letter_path() -> Path:
        return Path(settings.webhook_dead_letter_file).expanduser().resolve()

    def _load_queue(self) -> list[dict[str, Any]]:
        path = self._queue_path()
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(payload, list):
            return []
        return [item for item in payload if isinstance(item, dict)]

    def _save_queue(self, queue: list[dict[str, Any]]) -> None:
        path = self._queue_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")

    def _append_dead_letter(self, entry: dict[str, Any]) -> None:
        path = self._dead_letter_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False) + "\n")

    @staticmethod
    def _parse_iso(value: str) -> datetime:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed

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

    @staticmethod
    def _next_attempt_at(attempts: int) -> str:
        backoff = max(0.0, settings.webhook_retry_backoff_seconds)
        delay_seconds = backoff * (2 ** max(0, attempts - 1))
        return (datetime.now(UTC) + timedelta(seconds=delay_seconds)).isoformat()

    async def _deliver_once(
        self,
        client: httpx.AsyncClient,
        url: str,
        encoded: bytes,
        signature: str,
    ) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if signature:
            headers["X-Webhook-Signature"] = signature
        try:
            response = await client.post(url, content=encoded, headers=headers)
            ok = response.status_code < 400
            return {
                "ok": ok,
                "status_code": response.status_code,
                "error": None if ok else response.text[:300],
            }
        except httpx.HTTPError as exc:
            logger.warning("webhook_delivery_error", url=url, error=str(exc))
            return {"ok": False, "status_code": None, "error": str(exc)}

    async def drain_retry_queue(self) -> dict[str, Any]:
        queue = self._load_queue()
        if not queue:
            return {"processed": 0, "delivered": 0, "dead_lettered": 0, "pending": 0}

        now = datetime.now(UTC)
        pending: list[dict[str, Any]] = []
        processed = 0
        delivered = 0
        dead_lettered = 0
        max_attempts = max(1, settings.webhook_retry_attempts)

        async with httpx.AsyncClient(timeout=settings.webhook_timeout_seconds) as client:
            for item in queue:
                event_type = str(item.get("event_type", "unknown"))
                payload = item.get("payload")
                url = str(item.get("url", "")).strip()
                if not isinstance(payload, dict) or not url:
                    dead_lettered += 1
                    self._append_dead_letter(
                        {
                            "event_type": event_type,
                            "payload": payload,
                            "url": url,
                            "reason": "invalid_queue_entry",
                            "dead_lettered_at": now.isoformat(),
                        }
                    )
                    continue

                try:
                    next_attempt_at = self._parse_iso(
                        str(item.get("next_attempt_at", now.isoformat()))
                    )
                except ValueError:
                    next_attempt_at = now

                if next_attempt_at > now:
                    pending.append(item)
                    continue

                body = {"event_type": event_type, "payload": payload}
                encoded = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode(
                    "utf-8"
                )
                signature = self._signature(encoded)
                processed += 1
                result = await self._deliver_once(client, url, encoded, signature)
                if result["ok"]:
                    delivered += 1
                    continue

                attempts = int(item.get("attempts", 1) or 1) + 1
                if attempts >= max_attempts:
                    dead_lettered += 1
                    self._append_dead_letter(
                        {
                            "event_type": event_type,
                            "payload": payload,
                            "url": url,
                            "attempts": attempts,
                            "last_status_code": result.get("status_code"),
                            "last_error": result.get("error"),
                            "dead_lettered_at": now.isoformat(),
                        }
                    )
                    continue

                updated = {
                    "event_type": event_type,
                    "payload": payload,
                    "url": url,
                    "attempts": attempts,
                    "last_status_code": result.get("status_code"),
                    "last_error": result.get("error"),
                    "created_at": str(item.get("created_at") or now.isoformat()),
                    "updated_at": now.isoformat(),
                    "next_attempt_at": self._next_attempt_at(attempts),
                }
                pending.append(updated)

        self._save_queue(pending)
        return {
            "processed": processed,
            "delivered": delivered,
            "dead_lettered": dead_lettered,
            "pending": len(pending),
        }

    async def dispatch(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not settings.webhook_urls:
            return {
                "sent": 0,
                "delivered": 0,
                "queued": 0,
                "results": [],
                "retry_queue": {"pending": 0},
            }

        drained = await self.drain_retry_queue()
        body = {"event_type": event_type, "payload": payload}
        encoded = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        signature = self._signature(encoded)

        results: list[dict[str, Any]] = []
        delivered = 0
        queued = 0
        queue_entries: list[dict[str, Any]] = []
        now = datetime.now(UTC)

        async with httpx.AsyncClient(timeout=settings.webhook_timeout_seconds) as client:
            for url in settings.webhook_urls:
                result = await self._deliver_once(client, url, encoded, signature)
                if result["ok"]:
                    delivered += 1
                    results.append(
                        {
                            "url": url,
                            "status_code": result["status_code"],
                            "ok": True,
                            "queued": False,
                        }
                    )
                    continue

                queued += 1
                queue_entries.append(
                    {
                        "event_type": event_type,
                        "payload": payload,
                        "url": url,
                        "attempts": 1,
                        "last_status_code": result.get("status_code"),
                        "last_error": result.get("error"),
                        "created_at": now.isoformat(),
                        "updated_at": now.isoformat(),
                        "next_attempt_at": self._next_attempt_at(1),
                    }
                )
                results.append(
                    {
                        "url": url,
                        "status_code": result.get("status_code"),
                        "ok": False,
                        "queued": True,
                        "error": result.get("error"),
                    }
                )

        if queue_entries:
            queue = self._load_queue()
            queue.extend(queue_entries)
            self._save_queue(queue)

        queue_state = self._load_queue()
        return {
            "sent": len(settings.webhook_urls),
            "delivered": delivered,
            "queued": queued,
            "results": results,
            "retry_queue": {
                "drained": drained,
                "pending": len(queue_state),
                "queue_file": str(self._queue_path()),
                "dead_letter_file": str(self._dead_letter_path()),
            },
        }


webhook_dispatcher = WebhookDispatcher()

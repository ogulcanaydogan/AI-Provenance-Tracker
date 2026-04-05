"""Instagram-first social intake queue, dedupe, and automated reply handling."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import hmac
import json
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel
import structlog
from sqlalchemy import delete, desc, func, select

from app.api.v1.detect import PLATFORM_MEDIA_MISSING_DETAIL, analyze_url_content
from app.core.config import settings
from app.db.models import SocialEventRecord
from app.db.session import get_db_session, init_database
from app.services.audit_events import audit_event_store
from app.services.instagram_client import InstagramClientError, instagram_client

logger = structlog.get_logger()


@dataclass(slots=True)
class NormalizedSocialEvent:
    """Canonical event shape derived from raw Instagram webhook payloads."""

    platform_event_id: str
    platform: str
    event_type: str
    reply_channel: str
    source_url: str | None
    actor_platform_id: str | None
    platform_media_id: str | None
    platform_comment_id: str | None
    payload: dict[str, Any]


class SocialIntakeService:
    """Persists, drains, and replies to social intake events."""

    def __init__(self) -> None:
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        await init_database()
        self._initialized = True

    def verify_instagram_signature(self, body: bytes, signature: str | None) -> bool:
        """Validate X-Hub-Signature-256 when a webhook app secret is configured."""
        secret = settings.instagram_webhook_app_secret.strip()
        if not secret:
            return True
        if not signature:
            return False
        expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def enqueue_instagram_webhook(self, payload: dict[str, Any]) -> dict[str, int]:
        """Parse inbound Instagram webhook payload and enqueue unique events."""
        await self._ensure_initialized()
        events = self._extract_instagram_events(payload)
        if not events:
            return {"received": 0, "queued": 0, "duplicates": 0}

        queued = 0
        duplicates = 0
        async with get_db_session() as session:
            for event in events:
                existing = await session.execute(
                    select(SocialEventRecord.id).where(
                        SocialEventRecord.platform_event_id == event.platform_event_id
                    )
                )
                if existing.scalar_one_or_none() is not None:
                    duplicates += 1
                    continue
                session.add(
                    SocialEventRecord(
                        platform_event_id=event.platform_event_id,
                        platform=event.platform,
                        event_type=event.event_type,
                        reply_channel=event.reply_channel,
                        status="pending",
                        source_url=event.source_url,
                        platform_media_id=event.platform_media_id,
                        platform_comment_id=event.platform_comment_id,
                        actor_platform_id=event.actor_platform_id,
                        payload=event.payload,
                    )
                )
                queued += 1
            await session.commit()

        await audit_event_store.safe_log_event(
            event_type="social.instagram.webhook_ingested",
            source="instagram_webhook",
            payload={"received": len(events), "queued": queued, "duplicates": duplicates},
        )
        return {"received": len(events), "queued": queued, "duplicates": duplicates}

    async def process_pending_events(self, *, limit: int | None = None) -> dict[str, int]:
        """Drain pending social events and send replies."""
        await self._ensure_initialized()
        batch_size = max(1, int(limit or settings.social_queue_batch_size))
        summary = {"scanned": 0, "processed": 0, "completed": 0, "failed": 0, "skipped": 0}

        async with get_db_session() as session:
            rows = (
                (
                    await session.execute(
                        select(SocialEventRecord)
                        .where(SocialEventRecord.status == "pending")
                        .order_by(SocialEventRecord.created_at.asc(), SocialEventRecord.id.asc())
                        .limit(batch_size)
                    )
                )
                .scalars()
                .all()
            )

        summary["scanned"] = len(rows)

        for row in rows:
            async with get_db_session() as session:
                record = await session.get(SocialEventRecord, row.id)
                if record is None or record.status != "pending":
                    continue
                record.status = "processing"
                record.attempt_count = int(record.attempt_count or 0) + 1
                record.updated_at = datetime.now(UTC)
                await session.commit()

            try:
                outcome = await self._process_record(row.id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("social_event_processing_failed", id=row.id, error=str(exc))
                async with get_db_session() as session:
                    record = await session.get(SocialEventRecord, row.id)
                    if record is not None:
                        record.status = "failed"
                        record.last_error = str(exc)[:1024]
                        record.updated_at = datetime.now(UTC)
                        await session.commit()
                summary["processed"] += 1
                summary["failed"] += 1
                await audit_event_store.safe_log_event(
                    event_type="social.event_failed",
                    severity="warning",
                    source="instagram_worker",
                    payload={"social_event_id": row.id, "error": str(exc)},
                )
                continue

            async with get_db_session() as session:
                record = await session.get(SocialEventRecord, row.id)
                if record is not None:
                    record.status = outcome["status"]
                    record.analysis_id = outcome.get("analysis_id")
                    record.response_status = outcome.get("response_status")
                    record.response_id = outcome.get("response_id")
                    record.last_error = outcome.get("last_error")
                    record.updated_at = datetime.now(UTC)
                    await session.commit()

            summary["processed"] += 1
            summary[outcome["status"]] += 1

        return summary

    async def list_events(
        self,
        *,
        limit: int,
        offset: int,
        status: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return paginated social queue rows for admin inspection."""
        await self._ensure_initialized()
        async with get_db_session() as session:
            base_query = select(SocialEventRecord)
            count_query = select(func.count()).select_from(SocialEventRecord)
            if status:
                base_query = base_query.where(SocialEventRecord.status == status)
                count_query = count_query.where(SocialEventRecord.status == status)

            total = int((await session.execute(count_query)).scalar() or 0)
            rows = (
                (
                    await session.execute(
                        base_query.order_by(
                            desc(SocialEventRecord.created_at), desc(SocialEventRecord.id)
                        )
                        .offset(offset)
                        .limit(limit)
                    )
                )
                .scalars()
                .all()
            )

        return [self._to_item(row) for row in rows], total

    async def reset(self) -> None:
        """Clear stored social events for tests."""
        await self._ensure_initialized()
        async with get_db_session() as session:
            await session.execute(delete(SocialEventRecord))
            await session.commit()

    def _extract_instagram_events(self, payload: dict[str, Any]) -> list[NormalizedSocialEvent]:
        events: list[NormalizedSocialEvent] = []
        for entry in payload.get("entry", []):
            if not isinstance(entry, dict):
                continue
            entry_id = str(entry.get("id") or "unknown")
            entry_time = str(entry.get("time") or "0")

            for change in entry.get("changes") or []:
                if not isinstance(change, dict):
                    continue
                field = str(change.get("field") or "").strip().lower()
                value = change.get("value") if isinstance(change.get("value"), dict) else {}
                if field not in {"mentions", "tags", "comments", "story_mentions", "caption"}:
                    continue
                actor_id = self._first_non_empty(
                    self._nested_str(value, "from", "id"),
                    self._nested_str(value, "sender", "id"),
                    self._nested_str(value, "mentioned_by", "id"),
                )
                media_id = self._first_non_empty(
                    value.get("media_id"),
                    self._nested_str(value, "media", "id"),
                )
                comment_id = self._first_non_empty(value.get("id"), value.get("comment_id"))
                source_url = self._first_non_empty(
                    value.get("permalink"),
                    self._nested_str(value, "media", "permalink"),
                    self._nested_str(value, "media_share", "permalink"),
                    value.get("link"),
                    self._nested_str(value, "share", "link"),
                )
                raw_suffix = self._first_non_empty(
                    value.get("id"),
                    value.get("comment_id"),
                    value.get("media_id"),
                    value.get("timestamp"),
                    source_url,
                    entry_time,
                )
                reply_channel = "public_comment" if field == "comments" and comment_id else "dm"
                events.append(
                    NormalizedSocialEvent(
                        platform_event_id=f"instagram:{field}:{entry_id}:{raw_suffix}",
                        platform="instagram",
                        event_type=field,
                        reply_channel=reply_channel,
                        source_url=source_url,
                        actor_platform_id=actor_id,
                        platform_media_id=media_id,
                        platform_comment_id=comment_id,
                        payload={"entry_id": entry_id, "entry_time": entry_time, "change": change},
                    )
                )

            for message_event in entry.get("messaging") or []:
                if not isinstance(message_event, dict):
                    continue
                message = message_event.get("message")
                if not isinstance(message, dict):
                    continue
                actor_id = self._nested_str(message_event, "sender", "id")
                message_id = self._first_non_empty(
                    message.get("mid"), message_event.get("timestamp")
                )
                attachment_url = self._extract_message_attachment_url(message)
                source_url = self._first_non_empty(
                    attachment_url,
                    self._nested_str(message, "reply_to", "story", "url"),
                )
                if not actor_id:
                    continue
                events.append(
                    NormalizedSocialEvent(
                        platform_event_id=f"instagram:message:{entry_id}:{message_id}",
                        platform="instagram",
                        event_type="message",
                        reply_channel="dm",
                        source_url=source_url,
                        actor_platform_id=actor_id,
                        platform_media_id=None,
                        platform_comment_id=None,
                        payload={
                            "entry_id": entry_id,
                            "entry_time": entry_time,
                            "message": message_event,
                        },
                    )
                )
        return events

    async def _process_record(self, social_event_id: int) -> dict[str, Any]:
        async with get_db_session() as session:
            record = await session.get(SocialEventRecord, social_event_id)
            if record is None:
                raise RuntimeError("Social event record not found")
            event_type = record.event_type
            reply_channel = record.reply_channel
            source_url = (record.source_url or "").strip()

        if (
            reply_channel == "public_comment"
            and not settings.instagram_reply_public_comments_enabled
        ):
            return {
                "status": "skipped",
                "response_status": "public_comment_disabled",
                "last_error": None,
            }
        if reply_channel == "dm" and not settings.instagram_reply_dm_enabled:
            return {"status": "skipped", "response_status": "dm_disabled", "last_error": None}

        if not source_url:
            return await self._send_fallback_reply(
                social_event_id=social_event_id,
                reason="no_public_media",
            )

        try:
            analysis_payload = await self._analyze_source_url(source_url, event_type=event_type)
        except HTTPException as exc:
            detail = str(exc.detail)
            if exc.status_code == 400 and detail == PLATFORM_MEDIA_MISSING_DETAIL:
                return await self._send_fallback_reply(
                    social_event_id=social_event_id,
                    reason="no_public_media",
                )
            raise RuntimeError(detail) from exc

        content_type = str(analysis_payload.get("content_type") or "content")
        raw_result = analysis_payload.get("result")
        result = self._dump_result(raw_result)
        analysis_id = str(analysis_payload.get("analysis_id") or "")
        reply_text = self._compose_analysis_reply(
            content_type=content_type,
            result=result,
            analysis_id=analysis_id,
            reply_channel=reply_channel,
        )
        response = await self._send_reply(social_event_id=social_event_id, message=reply_text)

        await audit_event_store.safe_log_event(
            event_type="social.event_completed",
            source="instagram_worker",
            payload={
                "social_event_id": social_event_id,
                "analysis_id": analysis_id,
                "content_type": content_type,
                "reply_channel": reply_channel,
                "response_status": response["response_status"],
            },
        )
        return {
            "status": "completed",
            "analysis_id": analysis_id,
            "response_status": response["response_status"],
            "response_id": response.get("response_id"),
            "last_error": None,
        }

    async def _analyze_source_url(self, source_url: str, *, event_type: str) -> dict[str, Any]:
        return await analyze_url_content(source_url, source=f"instagram_{event_type}")

    async def _send_fallback_reply(self, *, social_event_id: int, reason: str) -> dict[str, Any]:
        message = (
            "I couldn't access public direct media from that Instagram post. "
            f"Send a public media link or use {self._detect_url_link()}"
        )
        response = await self._send_reply(social_event_id=social_event_id, message=message)
        return {
            "status": "completed",
            "analysis_id": None,
            "response_status": f"fallback_{reason}",
            "response_id": response.get("response_id"),
            "last_error": None,
        }

    async def _send_reply(self, *, social_event_id: int, message: str) -> dict[str, Any]:
        async with get_db_session() as session:
            record = await session.get(SocialEventRecord, social_event_id)
            if record is None:
                raise RuntimeError("Social event record not found")
            reply_channel = record.reply_channel
            comment_id = (record.platform_comment_id or "").strip()
            actor_id = (record.actor_platform_id or "").strip()

        clipped_message = self._clip_reply_text(message)

        try:
            if reply_channel == "public_comment":
                if not comment_id:
                    raise RuntimeError("Comment reply target is missing")
                payload = await instagram_client.reply_to_comment(
                    comment_id=comment_id, message=clipped_message
                )
                response_status = "public_comment_sent"
            else:
                if not actor_id:
                    raise RuntimeError("DM recipient id is missing")
                payload = await instagram_client.send_text_message(
                    recipient_id=actor_id, message=clipped_message
                )
                response_status = "dm_sent"
        except InstagramClientError as exc:
            raise RuntimeError(str(exc)) from exc

        response_id = self._first_non_empty(payload.get("id"), payload.get("message_id"))
        return {"response_status": response_status, "response_id": response_id}

    def _compose_analysis_reply(
        self,
        *,
        content_type: str,
        result: dict[str, Any],
        analysis_id: str,
        reply_channel: str,
    ) -> str:
        verdict = self._conservative_verdict(content_type=content_type, result=result)
        confidence = float(result.get("confidence", 0.0) or 0.0)
        confidence_pct = int(round(max(0.0, min(confidence, 1.0)) * 100))
        evidence_url = self._evidence_url(analysis_id)

        if reply_channel == "public_comment":
            if verdict == "uncertain":
                return (
                    f"Uncertain ({content_type}, {confidence_pct}% confidence). "
                    f"Evidence: {evidence_url}"
                )
            return f"{verdict} ({content_type}, {confidence_pct}% confidence). Evidence: {evidence_url}"

        if verdict == "uncertain":
            return (
                f"Uncertain for this {content_type} ({confidence_pct}% confidence). "
                f"Review the evidence: {evidence_url}"
            )
        return (
            f"{verdict} for this {content_type} ({confidence_pct}% confidence). "
            f"Evidence: {evidence_url}"
        )

    def _conservative_verdict(self, *, content_type: str, result: dict[str, Any]) -> str:
        if content_type == "text":
            decision_band = str(result.get("decision_band") or "").strip().lower()
            if decision_band == "ai":
                return "AI likely"
            if decision_band == "human":
                return "Human likely"
            return "uncertain"

        confidence = float(result.get("confidence", 0.0) or 0.0)
        is_ai_generated = bool(result.get("is_ai_generated"))
        if is_ai_generated and confidence >= 0.75:
            return "AI likely"
        if not is_ai_generated and confidence <= 0.25:
            return "Human likely"
        return "uncertain"

    @staticmethod
    def _dump_result(result: Any) -> dict[str, Any]:
        if isinstance(result, BaseModel):
            return result.model_dump(mode="json")
        if isinstance(result, dict):
            return result
        return {}

    @staticmethod
    def _nested_str(data: dict[str, Any], *path: str) -> str | None:
        current: Any = data
        for part in path:
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        if current is None:
            return None
        text = str(current).strip()
        return text or None

    @classmethod
    def _extract_message_attachment_url(cls, message: dict[str, Any]) -> str | None:
        attachments = message.get("attachments")
        if not isinstance(attachments, list):
            return None
        for attachment in attachments:
            if not isinstance(attachment, dict):
                continue
            url = cls._nested_str(attachment, "payload", "url")
            if url:
                return url
        return None

    @staticmethod
    def _first_non_empty(*values: Any) -> str | None:
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None

    def _clip_reply_text(self, message: str) -> str:
        max_length = max(80, int(settings.social_reply_max_length))
        collapsed = " ".join(message.split()).strip()
        if len(collapsed) <= max_length:
            return collapsed
        return collapsed[: max_length - 1].rstrip() + "…"

    def _detect_url_link(self) -> str:
        return settings.public_frontend_base_url.rstrip("/") + "/detect/url"

    def _evidence_url(self, analysis_id: str) -> str:
        return settings.public_api_base_url.rstrip("/") + f"/api/v1/analyze/evidence/{analysis_id}"

    @staticmethod
    def _to_item(record: SocialEventRecord) -> dict[str, Any]:
        created_at = record.created_at
        updated_at = record.updated_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)
        return {
            "id": record.id,
            "platform_event_id": record.platform_event_id,
            "platform": record.platform,
            "event_type": record.event_type,
            "reply_channel": record.reply_channel,
            "status": record.status,
            "source_url": record.source_url,
            "actor_platform_id": record.actor_platform_id,
            "platform_media_id": record.platform_media_id,
            "platform_comment_id": record.platform_comment_id,
            "analysis_id": record.analysis_id,
            "response_status": record.response_status,
            "response_id": record.response_id,
            "attempt_count": record.attempt_count,
            "last_error": record.last_error,
            "created_at": created_at.isoformat(),
            "updated_at": updated_at.isoformat(),
        }


social_intake_service = SocialIntakeService()

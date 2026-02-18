"""Audit event persistence and query helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import delete, desc, func, select

from app.core.config import settings
from app.db.models import AuditEventRecord
from app.db.session import get_db_session, init_database

logger = structlog.get_logger()


@dataclass(slots=True)
class StoredAuditEvent:
    """Normalized audit event for API responses."""

    id: int
    created_at: datetime
    event_type: str
    severity: str
    source: str
    actor_id: str | None
    request_id: str | None
    payload: dict[str, Any]


class AuditEventStore:
    """Persistent store for audit events."""

    def __init__(self, max_items: int | None = None) -> None:
        self._max_items = max(1000, int(max_items or settings.audit_events_max_items))
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        await init_database()
        self._initialized = True

    async def log_event(
        self,
        *,
        event_type: str,
        severity: str = "info",
        source: str = "api",
        actor_id: str | None = None,
        request_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> int | None:
        """Persist a new audit event and return inserted id."""
        if not settings.audit_events_enabled:
            return None

        await self._ensure_initialized()
        clean_payload = payload or {}

        async with get_db_session() as session:
            event = AuditEventRecord(
                event_type=event_type,
                severity=severity,
                source=source,
                actor_id=actor_id,
                request_id=request_id,
                payload=clean_payload,
            )
            session.add(event)
            await session.flush()
            event_id = int(event.id)
            await session.commit()

            count_query = select(func.count()).select_from(AuditEventRecord)
            total = int((await session.execute(count_query)).scalar() or 0)
            overflow = total - self._max_items
            if overflow > 0:
                oldest_ids_query = (
                    select(AuditEventRecord.id)
                    .order_by(AuditEventRecord.created_at.asc())
                    .limit(overflow)
                )
                oldest_ids = [row[0] for row in (await session.execute(oldest_ids_query)).all()]
                if oldest_ids:
                    await session.execute(
                        delete(AuditEventRecord).where(AuditEventRecord.id.in_(oldest_ids))
                    )
                    await session.commit()

            return event_id

    async def safe_log_event(
        self,
        *,
        event_type: str,
        severity: str = "info",
        source: str = "api",
        actor_id: str | None = None,
        request_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Log event without propagating storage failures to request handlers."""
        try:
            await self.log_event(
                event_type=event_type,
                severity=severity,
                source=source,
                actor_id=actor_id,
                request_id=request_id,
                payload=payload,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "audit_event_write_failed",
                event_type=event_type,
                error=str(exc),
            )

    async def list_events(
        self,
        *,
        limit: int,
        offset: int,
        event_type: str | None = None,
        severity: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return paginated audit events with optional filters."""
        await self._ensure_initialized()
        async with get_db_session() as session:
            base_query = select(AuditEventRecord)
            count_query = select(func.count()).select_from(AuditEventRecord)

            if event_type:
                base_query = base_query.where(AuditEventRecord.event_type == event_type)
                count_query = count_query.where(AuditEventRecord.event_type == event_type)
            if severity:
                base_query = base_query.where(AuditEventRecord.severity == severity)
                count_query = count_query.where(AuditEventRecord.severity == severity)

            total = int((await session.execute(count_query)).scalar() or 0)
            rows = (
                (
                    await session.execute(
                        base_query.order_by(
                            desc(AuditEventRecord.created_at), desc(AuditEventRecord.id)
                        )
                        .offset(offset)
                        .limit(limit)
                    )
                )
                .scalars()
                .all()
            )

        items = [self._to_item(row) for row in rows]
        return items, total

    async def reset(self) -> None:
        """Clear audit events (used by tests)."""
        await self._ensure_initialized()
        async with get_db_session() as session:
            await session.execute(delete(AuditEventRecord))
            await session.commit()

    @staticmethod
    def _to_item(record: AuditEventRecord) -> dict[str, Any]:
        created_at = record.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        return {
            "id": record.id,
            "created_at": created_at.isoformat(),
            "event_type": record.event_type,
            "severity": record.severity,
            "source": record.source,
            "actor_id": record.actor_id,
            "request_id": record.request_id,
            "payload": record.payload,
        }


audit_event_store = AuditEventStore()

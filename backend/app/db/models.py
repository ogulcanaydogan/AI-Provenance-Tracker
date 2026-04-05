"""Database models for persisted analyses, audit events, and social queue state."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base


class AnalysisRecord(Base):
    """Persisted detection result with metadata."""

    __tablename__ = "analysis_records"
    __table_args__ = (
        Index("ix_analysis_type_created", "content_type", "created_at"),
        Index("ix_analysis_source_created", "source", "created_at"),
    )

    analysis_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    content_type: Mapped[str] = mapped_column(String(16), index=True)
    result: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
    )
    source: Mapped[str] = mapped_column(String(32), default="api", index=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    input_size: Mapped[int] = mapped_column(Integer)
    filename: Mapped[str | None] = mapped_column(String(512), nullable=True)


class AuditEventRecord(Base):
    """Persisted audit event for security/compliance observability."""

    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_type_created", "event_type", "created_at"),
        Index("ix_audit_actor_created", "actor_id", "created_at"),
        Index("ix_audit_severity_created", "severity", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(16), default="info", index=True)
    source: Mapped[str] = mapped_column(String(32), default="api", index=True)
    actor_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class SocialEventRecord(Base):
    """Persisted social intake event with queue and reply state."""

    __tablename__ = "social_events"
    __table_args__ = (
        Index("ix_social_platform_status_created", "platform", "status", "created_at"),
        Index("ix_social_actor_created", "actor_platform_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform_event_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    reply_channel: Mapped[str] = mapped_column(String(32), default="dm")
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    platform_media_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    platform_comment_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    actor_platform_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    analysis_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    response_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    response_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        index=True,
    )

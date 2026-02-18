"""Persistent storage for analysis history and dashboard stats."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy import delete, desc, func, select

from app.db.models import AnalysisRecord
from app.db.session import get_db_session, init_database

ContentType = Literal["text", "image", "audio", "video"]


@dataclass(slots=True)
class StoredAnalysis:
    """Stored detection result with metadata."""

    analysis_id: str
    content_type: ContentType
    result: dict[str, Any]
    created_at: datetime
    source: str
    source_url: str | None
    content_hash: str
    input_size: int
    filename: str | None = None


class AnalysisStore:
    """Thread-safe persistent store for analysis records."""

    def __init__(self, max_items: int = 1000) -> None:
        self._max_items = max_items
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        await init_database()
        self._initialized = True

    async def save_text_result(
        self,
        text: str,
        result: BaseModel,
        source: str = "api",
        source_url: str | None = None,
    ) -> str:
        """Store text detection output and return analysis id."""
        return await self._save_result(
            content_type="text",
            result=result,
            content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            input_size=len(text),
            source=source,
            source_url=source_url,
        )

    async def save_image_result(
        self,
        image_data: bytes,
        filename: str,
        result: BaseModel,
        source: str = "api",
        source_url: str | None = None,
    ) -> str:
        """Store image detection output and return analysis id."""
        return await self._save_result(
            content_type="image",
            result=result,
            content_hash=hashlib.sha256(image_data).hexdigest(),
            input_size=len(image_data),
            source=source,
            source_url=source_url,
            filename=filename,
        )

    async def save_audio_result(
        self,
        audio_data: bytes,
        filename: str,
        result: BaseModel,
        source: str = "api",
        source_url: str | None = None,
    ) -> str:
        """Store audio detection output and return analysis id."""
        return await self._save_result(
            content_type="audio",
            result=result,
            content_hash=hashlib.sha256(audio_data).hexdigest(),
            input_size=len(audio_data),
            source=source,
            source_url=source_url,
            filename=filename,
        )

    async def save_video_result(
        self,
        video_data: bytes,
        filename: str,
        result: BaseModel,
        source: str = "api",
        source_url: str | None = None,
    ) -> str:
        """Store video detection output and return analysis id."""
        return await self._save_result(
            content_type="video",
            result=result,
            content_hash=hashlib.sha256(video_data).hexdigest(),
            input_size=len(video_data),
            source=source,
            source_url=source_url,
            filename=filename,
        )

    async def _save_result(
        self,
        content_type: ContentType,
        result: BaseModel,
        content_hash: str,
        input_size: int,
        source: str,
        source_url: str | None,
        filename: str | None = None,
    ) -> str:
        await self._ensure_initialized()
        analysis_id = str(uuid.uuid4())
        dumped_result = result.model_dump(mode="json")
        dumped_result["analysis_id"] = analysis_id

        async with get_db_session() as session:
            session.add(
                AnalysisRecord(
                    analysis_id=analysis_id,
                    content_type=content_type,
                    result=dumped_result,
                    source=source,
                    source_url=source_url,
                    content_hash=content_hash,
                    input_size=input_size,
                    filename=filename,
                )
            )
            await session.commit()

            count_query = select(func.count()).select_from(AnalysisRecord)
            total = int((await session.execute(count_query)).scalar() or 0)
            overflow = total - self._max_items
            if overflow > 0:
                oldest_ids_query = (
                    select(AnalysisRecord.analysis_id)
                    .order_by(AnalysisRecord.created_at.asc())
                    .limit(overflow)
                )
                oldest_ids = [row[0] for row in (await session.execute(oldest_ids_query)).all()]
                if oldest_ids:
                    await session.execute(
                        delete(AnalysisRecord).where(AnalysisRecord.analysis_id.in_(oldest_ids))
                    )
                    await session.commit()

        return analysis_id

    async def get_record(self, analysis_id: str) -> StoredAnalysis | None:
        """Get stored analysis by id."""
        await self._ensure_initialized()
        async with get_db_session() as session:
            query = select(AnalysisRecord).where(AnalysisRecord.analysis_id == analysis_id)
            row = (await session.execute(query)).scalar_one_or_none()
            if row is None:
                return None
            return self._to_stored_analysis(row)

    async def get_history(self, limit: int, offset: int) -> tuple[list[dict[str, Any]], int]:
        """Return paginated history in reverse chronological order."""
        await self._ensure_initialized()
        async with get_db_session() as session:
            total = int(
                (await session.execute(select(func.count()).select_from(AnalysisRecord))).scalar()
                or 0
            )
            query = (
                select(AnalysisRecord)
                .order_by(desc(AnalysisRecord.created_at))
                .offset(offset)
                .limit(limit)
            )
            rows = (await session.execute(query)).scalars().all()
        items = [self._to_history_item(self._to_stored_analysis(row)) for row in rows]
        return items, total

    async def get_stats(self) -> dict[str, Any]:
        """Compute aggregate stats from stored analyses."""
        await self._ensure_initialized()
        records = await self._all_records()
        total = len(records)
        ai_detected_count = sum(
            1 for record in records if bool(record.result.get("is_ai_generated"))
        )
        average_confidence = (
            round(
                sum(float(record.result.get("confidence", 0.0)) for record in records) / total,
                3,
            )
            if total > 0
            else 0.0
        )

        by_type = {"text": 0, "image": 0, "audio": 0, "video": 0}
        for record in records:
            by_type[record.content_type] = by_type.get(record.content_type, 0) + 1

        return {
            "total_analyses": total,
            "ai_detected_count": ai_detected_count,
            "human_detected_count": total - ai_detected_count,
            "average_confidence": average_confidence,
            "by_type": by_type,
        }

    async def get_dashboard(self, days: int = 14) -> dict[str, Any]:
        """Return analytics dashboard data for recent activity."""
        await self._ensure_initialized()
        days = max(1, min(days, 90))
        cutoff = datetime.now(UTC) - timedelta(days=days - 1)
        records = await self._all_records()

        total_all_time = len(records)
        recent_records = [record for record in records if record.created_at >= cutoff]
        total_recent = len(recent_records)
        ai_recent = sum(
            1 for record in recent_records if bool(record.result.get("is_ai_generated"))
        )

        by_type_recent = {"text": 0, "image": 0, "audio": 0, "video": 0}
        by_source_recent: dict[str, int] = {}
        by_day: dict[date, dict[str, int]] = {}

        for record in recent_records:
            by_type_recent[record.content_type] = by_type_recent.get(record.content_type, 0) + 1
            by_source_recent[record.source] = by_source_recent.get(record.source, 0) + 1
            day = record.created_at.date()
            bucket = by_day.setdefault(day, {"total": 0, "ai": 0})
            bucket["total"] += 1
            if bool(record.result.get("is_ai_generated")):
                bucket["ai"] += 1

        timeline = []
        start_day = cutoff.date()
        for i in range(days):
            current_day = start_day + timedelta(days=i)
            bucket = by_day.get(current_day, {"total": 0, "ai": 0})
            timeline.append(
                {
                    "date": current_day.isoformat(),
                    "total": bucket["total"],
                    "ai_detected": bucket["ai"],
                    "human_detected": max(bucket["total"] - bucket["ai"], 0),
                }
            )

        average_confidence_recent = (
            round(
                sum(float(record.result.get("confidence", 0.0)) for record in recent_records)
                / total_recent,
                3,
            )
            if total_recent
            else 0.0
        )
        ai_rate_recent = round(ai_recent / total_recent, 3) if total_recent else 0.0

        top_models_counter: dict[str, int] = {}
        for record in recent_records:
            model = record.result.get("model_prediction")
            if model:
                key = str(model)
                top_models_counter[key] = top_models_counter.get(key, 0) + 1
        top_models = sorted(
            ({"model": model, "count": count} for model, count in top_models_counter.items()),
            key=lambda item: item["count"],
            reverse=True,
        )[:5]

        alerts: list[dict[str, Any]] = []
        if total_recent >= 10 and ai_rate_recent >= 0.7:
            alerts.append(
                {
                    "code": "high_ai_rate",
                    "severity": "medium",
                    "message": "AI detection rate is elevated in the selected window.",
                }
            )
        if total_recent >= 25:
            peak_day = max(timeline, key=lambda item: item["total"])
            if peak_day["total"] >= max(10, int(total_recent * 0.35)):
                alerts.append(
                    {
                        "code": "volume_spike",
                        "severity": "low",
                        "message": f"Volume spike detected on {peak_day['date']}.",
                    }
                )

        return {
            "window_days": days,
            "summary": {
                "total_analyses_all_time": total_all_time,
                "total_analyses_window": total_recent,
                "ai_detected_window": ai_recent,
                "human_detected_window": max(total_recent - ai_recent, 0),
                "ai_rate_window": ai_rate_recent,
                "average_confidence_window": average_confidence_recent,
            },
            "by_type_window": by_type_recent,
            "by_source_window": by_source_recent,
            "top_models_window": top_models,
            "timeline": timeline,
            "alerts_window": alerts,
        }

    async def reset(self) -> None:
        """Clear persisted records (test helper)."""
        await self._ensure_initialized()
        async with get_db_session() as session:
            await session.execute(delete(AnalysisRecord))
            await session.commit()

    async def _all_records(self) -> list[StoredAnalysis]:
        async with get_db_session() as session:
            query = select(AnalysisRecord).order_by(AnalysisRecord.created_at.asc())
            rows = (await session.execute(query)).scalars().all()
        return [self._to_stored_analysis(row) for row in rows]

    @staticmethod
    def _to_stored_analysis(record: AnalysisRecord) -> StoredAnalysis:
        created_at = record.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        return StoredAnalysis(
            analysis_id=record.analysis_id,
            content_type=record.content_type,  # type: ignore[arg-type]
            result=record.result,
            created_at=created_at,
            source=record.source,
            source_url=record.source_url,
            content_hash=record.content_hash,
            input_size=record.input_size,
            filename=record.filename,
        )

    @staticmethod
    def _to_history_item(record: StoredAnalysis) -> dict[str, Any]:
        return {
            "analysis_id": record.analysis_id,
            "content_type": record.content_type,
            "is_ai_generated": record.result.get("is_ai_generated"),
            "confidence": record.result.get("confidence"),
            "model_prediction": record.result.get("model_prediction"),
            "created_at": record.created_at.isoformat(),
            "source": record.source,
            "source_url": record.source_url,
            "explanation": record.result.get("explanation"),
        }


analysis_store = AnalysisStore()

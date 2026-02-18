import hashlib
import json
import uuid

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.detectors.text.ensemble import get_text_ensemble
from app.models.analysis import Analysis
from app.schemas.common import DetectionResult

CACHE_TTL = 3600  # 1 hour


async def analyze_text(
    text: str,
    db: AsyncSession | None = None,
    redis: Redis | None = None,
) -> DetectionResult:
    content_hash = hashlib.sha256(text.encode()).hexdigest()

    # Check cache
    if redis:
        cached = await redis.get(f"text:{content_hash}")
        if cached:
            return DetectionResult.model_validate_json(cached)

    analysis_id = str(uuid.uuid4())
    ensemble = await get_text_ensemble()
    result = await ensemble.analyze(text, analysis_id)

    # Cache result
    if redis:
        await redis.setex(
            f"text:{content_hash}",
            CACHE_TTL,
            result.model_dump_json(),
        )

    # Persist to database
    if db:
        record = Analysis(
            id=uuid.UUID(analysis_id),
            content_type="text",
            content_hash=content_hash,
            confidence_score=result.confidence_score,
            verdict=result.verdict,
            signals=[s.model_dump() for s in result.signals],
            summary=result.summary,
        )
        db.add(record)
        await db.commit()

    return result

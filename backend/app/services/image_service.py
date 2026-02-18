import hashlib
import uuid

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.detectors.image.ensemble import get_image_ensemble
from app.models.analysis import Analysis
from app.schemas.common import DetectionResult

CACHE_TTL = 3600  # 1 hour


async def analyze_image(
    image_bytes: bytes,
    db: AsyncSession | None = None,
    redis: Redis | None = None,
) -> DetectionResult:
    content_hash = hashlib.sha256(image_bytes).hexdigest()

    # Check cache
    if redis:
        cached = await redis.get(f"image:{content_hash}")
        if cached:
            return DetectionResult.model_validate_json(cached)

    analysis_id = str(uuid.uuid4())
    ensemble = await get_image_ensemble()
    result = await ensemble.analyze(image_bytes, analysis_id)

    # Cache result
    if redis:
        await redis.setex(
            f"image:{content_hash}",
            CACHE_TTL,
            result.model_dump_json(),
        )

    # Persist to database
    if db:
        record = Analysis(
            id=uuid.UUID(analysis_id),
            content_type="image",
            content_hash=content_hash,
            confidence_score=result.confidence_score,
            verdict=result.verdict,
            signals=[s.model_dump() for s in result.signals],
            summary=result.summary,
        )
        db.add(record)
        await db.commit()

    return result

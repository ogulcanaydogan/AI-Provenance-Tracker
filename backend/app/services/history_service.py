import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis
from app.schemas.common import DetectionResult, DetectionSignal


def _row_to_result(row: Analysis) -> DetectionResult:
    signals = [DetectionSignal(**s) for s in row.signals]
    return DetectionResult(
        id=str(row.id),
        content_type=row.content_type,
        confidence_score=row.confidence_score,
        verdict=row.verdict,
        signals=signals,
        summary=row.summary,
        analyzed_at=row.created_at,
    )


async def get_history(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
) -> dict:
    offset = (page - 1) * per_page

    count_query = select(func.count()).select_from(Analysis)
    total = (await db.execute(count_query)).scalar() or 0

    query = (
        select(Analysis)
        .order_by(Analysis.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(query)
    rows = result.scalars().all()

    return {
        "items": [_row_to_result(r) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


async def get_analysis_by_id(
    db: AsyncSession,
    analysis_id: str,
) -> DetectionResult | None:
    try:
        uid = uuid.UUID(analysis_id)
    except ValueError:
        return None

    query = select(Analysis).where(Analysis.id == uid)
    result = await db.execute(query)
    row = result.scalar_one_or_none()

    if row is None:
        return None

    return _row_to_result(row)

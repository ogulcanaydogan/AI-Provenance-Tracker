"""Batch processing API endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.detection.text.detector import TextDetector
from app.models.detection import (
    BatchTextDetectionRequest,
    BatchTextDetectionResponse,
    BatchTextResultItem,
)
from app.services.analysis_store import analysis_store
from app.services.provider_consensus import provider_consensus_engine

router = APIRouter()
text_detector = TextDetector()


@router.post("/text", response_model=BatchTextDetectionResponse)
async def batch_detect_text(request: BatchTextDetectionRequest) -> BatchTextDetectionResponse:
    """
    Process multiple text detection requests in a single API call.

    Each item is processed independently, and results are returned in request order.
    """
    if len(request.items) > settings.max_batch_items:
        raise HTTPException(
            status_code=400,
            detail=f"Batch exceeds maximum size of {settings.max_batch_items} items",
        )

    batch_id = str(uuid.uuid4())
    results: list[BatchTextResultItem] = []
    succeeded = 0
    failed = 0

    for index, item in enumerate(request.items):
        item_id = item.item_id or str(index)
        text = item.text.strip()

        if not text:
            failed += 1
            results.append(
                BatchTextResultItem(
                    item_id=item_id,
                    status="error",
                    error="Text cannot be empty",
                )
            )
            if request.stop_on_error:
                break
            continue

        if len(text) > settings.max_text_length:
            failed += 1
            results.append(
                BatchTextResultItem(
                    item_id=item_id,
                    status="error",
                    error=f"Text exceeds maximum length of {settings.max_text_length:,} characters",
                )
            )
            if request.stop_on_error:
                break
            continue

        try:
            detection = await text_detector.detect(text)
            detection.consensus = await provider_consensus_engine.build_consensus(
                content_type="text",
                internal_probability=detection.confidence,
                text=text,
            )
            detection.confidence = detection.consensus.final_probability
            detection.is_ai_generated = detection.consensus.is_ai_generated
            detection.analysis_id = await analysis_store.save_text_result(
                text=text,
                result=detection,
                source="batch",
            )
        except Exception as exc:  # noqa: BLE001
            failed += 1
            results.append(
                BatchTextResultItem(
                    item_id=item_id,
                    status="error",
                    error=str(exc),
                )
            )
            if request.stop_on_error:
                break
            continue

        succeeded += 1
        results.append(
            BatchTextResultItem(
                item_id=item_id,
                status="ok",
                result=detection,
            )
        )

    return BatchTextDetectionResponse(
        batch_id=batch_id,
        total=len(request.items),
        succeeded=succeeded,
        failed=failed,
        processed_at=datetime.now(UTC),
        items=results,
    )

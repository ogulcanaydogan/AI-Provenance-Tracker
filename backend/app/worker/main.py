"""Background worker entrypoint for scheduler and retry queue draining."""

from __future__ import annotations

import asyncio

import structlog

from app.core.config import settings
from app.db import close_database, init_database
from app.services.job_scheduler import x_pipeline_scheduler
from app.services.webhook_dispatcher import webhook_dispatcher

logger = structlog.get_logger()


async def run_worker() -> None:
    """Run the worker loop until interrupted."""
    tick_seconds = max(5, int(settings.worker_tick_seconds))
    logger.info(
        "worker_starting",
        tick_seconds=tick_seconds,
        enable_scheduler=settings.worker_enable_scheduler,
        drain_webhook_queue=settings.worker_drain_webhook_queue,
    )

    await init_database()
    if settings.worker_enable_scheduler:
        await x_pipeline_scheduler.start()

    try:
        while True:
            if settings.worker_drain_webhook_queue:
                drained = await webhook_dispatcher.drain_retry_queue()
                if drained.get("processed") or drained.get("dead_lettered"):
                    logger.info("worker_webhook_drain", **drained)
            await asyncio.sleep(tick_seconds)
    finally:
        if settings.worker_enable_scheduler:
            await x_pipeline_scheduler.stop()
        await close_database()
        logger.info("worker_stopped")


def main() -> int:
    """CLI entrypoint."""
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("worker_interrupted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

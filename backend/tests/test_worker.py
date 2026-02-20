"""Tests for worker entrypoint."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.worker.main import main, run_worker


@pytest.mark.asyncio
async def test_run_worker_starts_and_stops() -> None:
    """Worker should init DB, enter loop, and exit when cancelled."""
    with (
        patch("app.worker.main.init_database", new_callable=AsyncMock) as mock_init,
        patch("app.worker.main.close_database", new_callable=AsyncMock),
        patch("app.worker.main.x_pipeline_scheduler"),
        patch("app.worker.main.webhook_dispatcher"),
        patch("app.worker.main.settings") as mock_settings,
    ):
        mock_settings.worker_tick_seconds = 1
        mock_settings.worker_enable_scheduler = False
        mock_settings.worker_drain_webhook_queue = False

        task = asyncio.create_task(run_worker())
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        mock_init.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_worker_drains_webhook_queue() -> None:
    """Worker should drain webhook queue when enabled."""
    with (
        patch("app.worker.main.init_database", new_callable=AsyncMock),
        patch("app.worker.main.close_database", new_callable=AsyncMock),
        patch("app.worker.main.x_pipeline_scheduler"),
        patch("app.worker.main.webhook_dispatcher") as mock_dispatcher,
        patch("app.worker.main.settings") as mock_settings,
    ):
        mock_settings.worker_tick_seconds = 1
        mock_settings.worker_enable_scheduler = False
        mock_settings.worker_drain_webhook_queue = True
        mock_dispatcher.drain_retry_queue = AsyncMock(
            return_value={"processed": 0, "dead_lettered": 0}
        )

        task = asyncio.create_task(run_worker())
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        mock_dispatcher.drain_retry_queue.assert_awaited()


@pytest.mark.asyncio
async def test_run_worker_starts_scheduler() -> None:
    """Worker should start scheduler when enabled."""
    with (
        patch("app.worker.main.init_database", new_callable=AsyncMock),
        patch("app.worker.main.close_database", new_callable=AsyncMock),
        patch("app.worker.main.x_pipeline_scheduler") as mock_scheduler,
        patch("app.worker.main.webhook_dispatcher"),
        patch("app.worker.main.settings") as mock_settings,
    ):
        mock_settings.worker_tick_seconds = 1
        mock_settings.worker_enable_scheduler = True
        mock_settings.worker_drain_webhook_queue = False
        mock_scheduler.start = AsyncMock()
        mock_scheduler.stop = AsyncMock()

        task = asyncio.create_task(run_worker())
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        mock_scheduler.start.assert_awaited_once()


def test_main_returns_zero_on_keyboard_interrupt() -> None:
    """main() should catch KeyboardInterrupt and return 0."""
    with patch("app.worker.main.asyncio.run", side_effect=KeyboardInterrupt):
        assert main() == 0

"""Unit tests for AsyncScheduler.
"""
from __future__ import annotations

import asyncio
import pytest

from src.common.scheduler import AsyncScheduler


@pytest.mark.asyncio
async def test_scheduler_init_and_status():
    scheduler = AsyncScheduler(interval_seconds=60, enabled=False)
    status = scheduler.get_status()
    assert status["enabled"] is False
    assert status["interval_seconds"] == 60
    assert status["is_executing"] is False
    assert status["run_count"] == 0
    assert status["last_run_at"] is None


@pytest.mark.asyncio
async def test_scheduler_trigger_now():
    executed = False

    async def _sample_task():
        nonlocal executed
        executed = True
        return {"items_processed": 5}

    scheduler = AsyncScheduler(task_fn=_sample_task, interval_seconds=100)
    res = await scheduler.trigger_now()

    assert executed is True
    assert res.get("items_processed") == 5
    status = scheduler.get_status()
    assert status["run_count"] == 1
    assert status["last_run_at"] is not None


@pytest.mark.asyncio
async def test_scheduler_overlap_lock():
    release_event = asyncio.Event()

    async def _long_task():
        await release_event.wait()
        return {"done": True}

    scheduler = AsyncScheduler(task_fn=_long_task)

    # Start first task in background
    task1 = asyncio.create_task(scheduler.trigger_now())
    await asyncio.sleep(0.01)

    # Attempt second trigger while first is running
    res2 = await scheduler.trigger_now()
    assert res2.get("status") == "busy"

    # Finish first task
    release_event.set()
    res1 = await task1
    assert res1.get("done") is True


@pytest.mark.asyncio
async def test_scheduler_toggle():
    scheduler = AsyncScheduler(interval_seconds=300, enabled=False)
    assert scheduler.enabled is False

    is_on = scheduler.toggle()
    assert is_on is True
    assert scheduler.enabled is True

    is_off = scheduler.toggle()
    assert is_off is False
    assert scheduler.enabled is False


@pytest.mark.asyncio
async def test_scheduler_error_isolation():
    async def _faulty_task():
        raise RuntimeError("의도된 외부 연동 실패")

    scheduler = AsyncScheduler(task_fn=_faulty_task)
    res = await scheduler.trigger_now()

    assert res.get("status") == "error"
    assert "의도된 외부 연동 실패" in res.get("error", "")
    assert scheduler.get_status()["run_count"] == 1
    # Check that scheduler is not locked
    assert scheduler._is_executing is False


@pytest.mark.asyncio
async def test_scheduler_loop_short_interval():
    count = 0

    async def _fast_task():
        nonlocal count
        count += 1
        return {"count": count}

    scheduler = AsyncScheduler(task_fn=_fast_task, interval_seconds=1)
    # Manually trigger execute task to simulate interval
    await scheduler._execute_task()
    await scheduler._execute_task()

    assert count == 2
    assert scheduler.get_status()["run_count"] == 2

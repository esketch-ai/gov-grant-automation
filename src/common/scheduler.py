"""Async background scheduler for periodic pipeline execution.
(src/common/scheduler.py)
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable, Coroutine, Dict, Optional

from .logging_config import get_logger

logger = get_logger("scheduler")


class AsyncScheduler:
    """Coordinates periodic automatic execution of tasks with overlap locking."""

    def __init__(
        self,
        task_fn: Optional[Callable[[], Coroutine[Any, Any, Any]]] = None,
        interval_seconds: int = 1800,  # 30 minutes default
        enabled: bool = False,
    ) -> None:
        self.task_fn = task_fn
        self.interval_seconds = interval_seconds
        self.enabled = enabled
        self._is_executing = False
        self._loop_task: Optional[asyncio.Task] = None
        self.last_run_at: Optional[datetime] = None
        self.next_run_at: Optional[datetime] = None
        self.run_count = 0
        self.last_result: Optional[Dict[str, Any]] = None

    def start(self) -> None:
        """Starts the scheduler background task loop."""
        if self._loop_task is not None and not self._loop_task.done():
            return
        self.enabled = True
        self._loop_task = asyncio.create_task(self._run_loop())
        logger.info("비동기 스케줄러 시작됨 (주기: %d초)", self.interval_seconds)

    def stop(self) -> None:
        """Stops the scheduler loop."""
        self.enabled = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
        self.next_run_at = None
        logger.info("비동기 스케줄러 중지됨")

    def toggle(self) -> bool:
        """Toggles scheduler active state."""
        if self.enabled:
            self.stop()
            return False
        else:
            self.start()
            return True

    async def trigger_now(self) -> Dict[str, Any]:
        """Manually triggers execution immediately, respecting overlap lock."""
        if self._is_executing:
            return {"status": "busy", "message": "작업이 이미 실행 중입니다."}
        return await self._execute_task()

    async def _run_loop(self) -> None:
        while self.enabled:
            self.next_run_at = datetime.now() + timedelta(seconds=self.interval_seconds)
            try:
                await asyncio.sleep(self.interval_seconds)
                if self.enabled:
                    await self._execute_task()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("스케줄러 루프 예외 (Safe Degrade 지속): %s", e)
                await asyncio.sleep(5)

    async def _execute_task(self) -> Dict[str, Any]:
        if self._is_executing:
            return {"status": "skipped", "message": "이전 작업 실행 중으로 건너뜀"}

        self._is_executing = True
        self.last_run_at = datetime.now()
        self.run_count += 1
        res = {}
        try:
            if self.task_fn:
                logger.info("스케줄러 작업 실행 #%d 시작", self.run_count)
                res = await self.task_fn()
                self.last_result = res if isinstance(res, dict) else {"result": str(res)}
            else:
                self.last_result = {"status": "no_op", "message": "등록된 태스크 함수 없음"}
        except Exception as e:
            logger.exception("스케줄러 작업 실행 중 예외 발생: %s", e)
            self.last_result = {"status": "error", "error": str(e)}
        finally:
            self._is_executing = False

        return self.last_result or {}

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "interval_seconds": self.interval_seconds,
            "interval_minutes": round(self.interval_seconds / 60, 1),
            "is_executing": self._is_executing,
            "run_count": self.run_count,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "last_result": self.last_result,
        }

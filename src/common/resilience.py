"""REQ-018 · 네트워크 장애 복원력: 지수 백오프(Exponential Backoff) 및 서킷 브레이커(Circuit Breaker).
(src/common/resilience.py)
"""
from __future__ import annotations

import asyncio
import functools
import inspect
import random
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple, Type

from .logging_config import get_logger

logger = get_logger("resilience")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"      # 정상 통신 가능
    OPEN = "OPEN"          # 장애 감지로 인한 빠른 실패 (차단)
    HALF_OPEN = "HALF_OPEN"  # 복구 여부 시험 모드


class CircuitBreakerOpenException(Exception):
    """서킷 브레이커 OPEN 상태로 인한 즉시 차단 예외."""
    pass


class CircuitBreaker:
    """포털 및 외부 엔드포인트별 장애 격리 서킷 브레이커."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._last_state_change: float = time.time()
        self._half_open_in_flight: bool = False

    @property
    def state(self) -> str:
        """현재 서킷 상태를 확인하고 타임아웃 경과 시 HALF_OPEN으로 갱신."""
        if self._state == CircuitState.OPEN:
            elapsed = time.time() - self._last_state_change
            if elapsed >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._last_state_change = time.time()
                self._half_open_in_flight = False
                logger.info("서킷 [%s] HALF_OPEN 전이 (복구 시험 모드)", self.name)
        return self._state.value

    def can_execute(self) -> bool:
        """호출 실행 가능 여부 판정 (OPEN 상태 시 빠른 실패)."""
        current_state = self.state
        if current_state == CircuitState.CLOSED:
            return True
        elif current_state == CircuitState.HALF_OPEN:
            if not self._half_open_in_flight:
                self._half_open_in_flight = True
                return True
            return False
        return False  # OPEN

    def record_success(self) -> None:
        """호출 성공 시 실패 카운트 리셋 및 서킷 정상 복구."""
        if self._state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
            logger.info("서킷 [%s] 복구 성공 -> CLOSED 전이", self.name)
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_in_flight = False
        self._last_state_change = time.time()

    def record_failure(self) -> None:
        """호출 실패 시 카운트 증가 및 임계치 초과 시 서킷 OPEN."""
        self._failure_count += 1
        if self._state == CircuitState.HALF_OPEN:
            # 복구 시험 중 실패 시 즉시 OPEN 재진입
            self._state = CircuitState.OPEN
            self._last_state_change = time.time()
            self._half_open_in_flight = False
            logger.warning("서킷 [%s] HALF_OPEN 시험 실패 -> OPEN 재차단", self.name)
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            self._last_state_change = time.time()
            self._half_open_in_flight = False
            logger.warning(
                "서킷 [%s] 연속 %d회 실패 -> OPEN 전이 (요청 임시 차단)",
                self.name,
                self._failure_count,
            )

    def reset(self) -> None:
        """수동 서킷 리셋."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_in_flight = False
        self._last_state_change = time.time()


# ---------------------------------------------------------------------------
# 전역 서킷 브레이커 레지스트리
# ---------------------------------------------------------------------------
_REGISTRY: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    failure_threshold: Optional[int] = None,
    recovery_timeout: Optional[float] = None,
) -> CircuitBreaker:
    """지정된 이름의 서킷 브레이커 조회 또는 등록."""
    if name not in _REGISTRY:
        _REGISTRY[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold if failure_threshold is not None else 3,
            recovery_timeout=recovery_timeout if recovery_timeout is not None else 30.0,
        )
    else:
        if failure_threshold is not None:
            _REGISTRY[name].failure_threshold = failure_threshold
        if recovery_timeout is not None:
            _REGISTRY[name].recovery_timeout = recovery_timeout
    return _REGISTRY[name]


def get_all_circuit_statuses() -> Dict[str, str]:
    """등록된 모든 서킷의 실시간 상태 딕셔너리 반환."""
    return {name: cb.state for name, cb in _REGISTRY.items()}


def reset_all_circuits() -> None:
    """전체 서킷 초기화 (테스트용)."""
    for cb in _REGISTRY.values():
        cb.reset()


# ---------------------------------------------------------------------------
# 지수 백오프(Exponential Backoff) 재시도
# ---------------------------------------------------------------------------
def retry_with_backoff(
    fn: Optional[Callable] = None,
    *,
    max_retries: int = 3,
    initial_delay: float = 0.05,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    circuit_name: Optional[str] = None,
):
    """지수 백오프 + 지터 재시도 및 서킷 브레이커 연동 데코레이터."""

    def decorator(func: Callable) -> Callable:
        cb = get_circuit_breaker(circuit_name) if circuit_name else None

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            if cb and not cb.can_execute():
                raise CircuitBreakerOpenException(f"Circuit '{circuit_name}' is OPEN. Fast-failing.")

            delay = initial_delay
            last_err = None
            for attempt in range(1, max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if cb:
                        cb.record_success()
                    return result
                except retry_exceptions as e:
                    last_err = e
                    if attempt == max_retries:
                        if cb:
                            cb.record_failure()
                        logger.warning(
                            "[%s] 최대 %d회 재시도 실패: %s",
                            func.__name__,
                            max_retries,
                            e,
                        )
                        raise

                    sleep_time = delay * (random.uniform(0.8, 1.2) if jitter else 1.0)
                    logger.info(
                        "[%s] 재시도 #%d/%d (%s) -> %.2f초 대기",
                        func.__name__,
                        attempt,
                        max_retries,
                        e,
                        sleep_time,
                    )
                    time.sleep(sleep_time)
                    delay *= backoff_factor

            raise last_err

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            if cb and not cb.can_execute():
                raise CircuitBreakerOpenException(f"Circuit '{circuit_name}' is OPEN. Fast-failing.")

            delay = initial_delay
            last_err = None
            for attempt in range(1, max_retries + 1):
                try:
                    result = await func(*args, **kwargs)
                    if cb:
                        cb.record_success()
                    return result
                except retry_exceptions as e:
                    last_err = e
                    if attempt == max_retries:
                        if cb:
                            cb.record_failure()
                        logger.warning(
                            "[%s] 비동기 최대 %d회 재시도 실패: %s",
                            func.__name__,
                            max_retries,
                            e,
                        )
                        raise

                    sleep_time = delay * (random.uniform(0.8, 1.2) if jitter else 1.0)
                    logger.info(
                        "[%s] 비동기 재시도 #%d/%d (%s) -> %.2f초 대기",
                        func.__name__,
                        attempt,
                        max_retries,
                        e,
                        sleep_time,
                    )
                    await asyncio.sleep(sleep_time)
                    delay *= backoff_factor

            raise last_err

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    if fn is None:
        return decorator
    return decorator(fn)

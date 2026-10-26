"""Tests for Exponential Backoff and Circuit Breaker Resilience (REQ-018).
"""
import time
import pytest

from src.common.resilience import (
    CircuitBreaker,
    CircuitBreakerOpenException,
    CircuitState,
    get_circuit_breaker,
    reset_all_circuits,
    retry_with_backoff,
)


@pytest.fixture(autouse=True)
def cleanup_circuits():
    reset_all_circuits()
    yield
    reset_all_circuits()


def test_exponential_backoff_retry_success():
    call_count = 0

    @retry_with_backoff(max_retries=3, initial_delay=0.01, backoff_factor=1.5, jitter=False)
    def flaky_task():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Temporary timeout")
        return "SUCCESS"

    result = flaky_task()
    assert result == "SUCCESS"
    assert call_count == 3


def test_exponential_backoff_retry_exhausted():
    call_count = 0

    @retry_with_backoff(max_retries=3, initial_delay=0.01, backoff_factor=1.5, jitter=False)
    def broken_task():
        nonlocal call_count
        call_count += 1
        raise ConnectionResetError("Fatal connection reset")

    with pytest.raises(ConnectionResetError):
        broken_task()
    assert call_count == 3


def test_circuit_breaker_closed_to_open():
    cb = CircuitBreaker("test_portal", failure_threshold=2, recovery_timeout=0.1)
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

    # First failure
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED

    # Second failure -> triggers OPEN
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False


def test_circuit_breaker_fast_failing():
    cb = get_circuit_breaker("fast_fail_service", failure_threshold=1)
    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    @retry_with_backoff(circuit_name="fast_fail_service", max_retries=2, initial_delay=0.01)
    def should_not_run():
        pytest.fail("Should not have executed while circuit is open")

    with pytest.raises(CircuitBreakerOpenException):
        should_not_run()


def test_circuit_breaker_recovery_half_open_to_closed():
    cb = CircuitBreaker("recovery_test", failure_threshold=1, recovery_timeout=0.05)
    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    # Sleep beyond recovery timeout
    time.sleep(0.06)
    assert cb.state == CircuitState.HALF_OPEN
    assert cb.can_execute() is True

    # Trial request succeeds -> recovers to CLOSED
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True


@pytest.mark.asyncio
async def test_multi_collector_circuit_isolation(tmp_path):
    from src.collector.multi_collector import MultiPortalCollector
    collector = MultiPortalCollector(download_root=tmp_path / "downloads")

    # Deliberately trip the circuit for 'ntis'
    ntis_cb = get_circuit_breaker("ntis", failure_threshold=1)
    ntis_cb.record_failure()
    assert ntis_cb.state == "OPEN"

    mock_profile = {
        "collection_scope": {
            "selected_bookmarks": ["ntis", "unregistered_test"],
            "enable_open_web_discovery": False,
        },
        "domain_routing": {"core_keywords": ["AI"]},
    }
    mock_portals = {
        "portals": {
            "ntis": {"adapter_type": "TypeC_RndAggregator"},
            "unregistered_test": {"adapter_type": "TypeA_OpenAPI_Scrape"},
        }
    }

    # Should safely degrade and bypass 'ntis' without raising uncaught exception
    notices = await collector.collect_for_item(mock_profile, mock_portals)
    assert isinstance(notices, list)

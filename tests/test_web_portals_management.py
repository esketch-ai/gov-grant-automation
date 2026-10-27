"""
tests/test_web_portals_management.py
REQ-026: 포털 운영 관리 대시보드 및 각 사이트별 접속/인증/크롤링 현황판 단위 및 API 테스트.
"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from src.web.app import app
from src.common.portal_manager import PortalStatusService
from src.common.resilience import get_circuit_breaker, reset_all_circuits


@pytest.fixture
def client():
    return TestClient(app)


def test_portals_view_renders_html_200(client):
    """GET /portals 웹 화면이 정상적으로 200 OK와 포털 목록을 렌더링하는지 검증."""
    response = client.get("/portals")
    assert response.status_code == 200
    html = response.text
    assert "각 사이트별 수집·접속" in html
    assert "K-Startup" in html
    assert "g2b" in html
    assert "공동인증서" in html
    assert "실시간 핑 (Latency)" in html


def test_api_portals_status_json(client):
    """GET /api/portals/status API가 12개 포털의 메타데이터와 상태를 올바른 스키마로 반환하는지 검증."""
    response = client.get("/api/portals/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["count"] >= 12
    portals = {p["portal_id"]: p for p in data["portals"]}

    # G2B 검증
    g2b = portals.get("g2b")
    assert g2b is not None
    assert g2b["login_required_for_web"] is True
    assert g2b["required_env_key"] == "G2B_API_KEY"
    assert g2b["auth_type"] == "LOGIN_CERT_REQUIRED"

    # K-Startup 검증
    kstartup = portals.get("k_startup")
    assert kstartup is not None
    assert kstartup["required_env_key"] == "DATA_GO_KR_KEY"
    assert kstartup["auth_type"] == "API_KEY_REQUIRED"

    # IRIS (공개 게시판) 검증
    iris = portals.get("iris")
    assert iris is not None
    assert iris["auth_type"] == "PUBLIC_BOARD"
    assert iris["required_env_key"] is None


@pytest.mark.asyncio
async def test_ping_single_portal_mocked():
    """PortalStatusService.ping_portal이 응답 시간과 도달 상태를 정상 측정하는지 검증."""
    service = PortalStatusService()
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value.status_code = 200
        res = await service.ping_portal("k_startup", timeout_sec=1.0)
        assert res["portal_id"] == "k_startup"
        assert res["is_reachable"] is True
        assert res["status_code"] == 200
        assert res["latency_ms"] >= 0.0
        assert res["error"] is None


@pytest.mark.asyncio
async def test_ping_single_portal_failure_handled():
    """대상 서버 오류나 타임아웃 발생 시 크래시 없이 안전하게 에러를 반환하는지 검증."""
    service = PortalStatusService()
    with patch("httpx.AsyncClient.get", side_effect=Exception("Connection timed out")):
        res = await service.ping_portal("non_existent_portal", timeout_sec=1.0)
        assert res["is_reachable"] is False
        assert res["error"] is not None


def test_circuit_breaker_reflection_in_portal_status():
    """서킷 브레이커가 OPEN 상태일 때 포털 운영 상태가 CIRCUIT_OPEN으로 표출되는지 검증."""
    reset_all_circuits()
    cb = get_circuit_breaker("smtech", failure_threshold=1, recovery_timeout=60.0)
    cb.record_failure()  # 1회 실패로 즉시 OPEN
    assert cb.state == "OPEN"

    service = PortalStatusService()
    portals = {p["portal_id"]: p for p in service.get_all_portal_statuses()}
    smtech = portals.get("smtech")
    assert smtech is not None
    assert smtech["circuit_state"] == "OPEN"
    assert smtech["operational_status"] == "CIRCUIT_OPEN"
    assert smtech["operational_status_color"] == "red"

    reset_all_circuits()

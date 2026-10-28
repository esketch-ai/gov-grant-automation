"""REQ-010, REQ-011, REQ-012, REQ-007 · 웹 관리자 대시보드 및 스케줄러/감사 통합 테스트."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.web.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_root_redirect(client):
    res = client.get("/", follow_redirects=False)
    assert res.status_code == 307
    assert res.headers["location"] == "/intro"


def test_dashboard_view(client):
    res = client.get("/dashboard")
    assert res.status_code == 200
    assert "2026년도 정부 R&D/조달 자동 매칭 대시보드" in res.text
    assert "영속화 공고" in res.text
    assert "QA 스웜 감사" in res.text
    assert "자동 스케줄러" in res.text


def test_announcements_view(client):
    res = client.get("/announcements")
    assert res.status_code == 200
    assert "2026년 공고 아카이브 및 관리" in res.text


def test_items_view(client):
    res = client.get("/items")
    assert res.status_code == 200
    assert "사업 아이템 프로파일 관리" in res.text
    assert "item_01_carbon_dmrv" in res.text or "item_02_voice_ai" in res.text


def test_matches_view(client):
    res = client.get("/matches")
    assert res.status_code == 200
    assert "알림 발송 이력" in res.text


def test_audit_view(client):
    res = client.get("/audit")
    assert res.status_code == 200
    assert "다각도 시스템 무결성 종합 감사 현황" in res.text
    assert "Agent-YearAudit" in res.text
    assert "Agent-WebQA" in res.text
    assert "QA 스웜 즉시 재검수" in res.text


def test_api_status(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert data["year_policy"] == "2026_strict"
    assert data["database_connected"] is True
    assert "scheduler" in data
    assert "qa_swarm" in data
    assert data["qa_swarm"]["total_score"] == 100.0
    assert data["qa_swarm"]["all_passed"] is True


def test_api_pipeline_run(client, monkeypatch):
    import src.main as mainmod
    # fake pipeline runner for safe offline test
    async def _fake_run(*a, **k):
        return {"items": [], "errors": 0}
    monkeypatch.setattr(mainmod, "run_daily_pipeline", _fake_run)

    res = client.post("/api/pipeline/run")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"


def test_api_audit_run(client):
    res = client.post("/api/audit/run")
    assert res.status_code == 200
    data = res.json()
    assert data["all_passed"] is True
    assert data["total_score"] == 100.0
    assert data["status"] == "APPROVED (Deploy-Ready)"


def test_scheduler_apis(client):
    # Test GET status
    res_status = client.get("/api/scheduler/status")
    assert res_status.status_code == 200
    data_status = res_status.json()
    assert "enabled" in data_status
    assert "interval_seconds" in data_status

    # Test POST toggle
    res_toggle = client.post("/api/scheduler/toggle")
    assert res_toggle.status_code == 200
    data_toggle = res_toggle.json()
    assert "enabled" in data_toggle
    assert "message" in data_toggle

    # Toggle back to ensure clean state
    res_toggle_back = client.post("/api/scheduler/toggle")
    assert res_toggle_back.status_code == 200
    assert res_toggle_back.json()["enabled"] is False


def test_req041_template_dom_elements_healed(client):
    """REQ-041 Round 1: announcements.html 및 audit_logs.html 복원 DOM ID 검증."""
    # announcements.html 내 simNote, simChecks 검증
    res_ann = client.get("/announcements")
    assert res_ann.status_code == 200
    assert 'id="simNote"' in res_ann.text
    assert 'id="simChecks"' in res_ann.text
    assert 'id="simResult"' in res_ann.text

    # audit_logs.html 내 verify-result 검증
    res_audit = client.get("/admin/audit-logs")
    assert res_audit.status_code == 200
    assert 'id="verify-result"' in res_audit.text


def test_req041_fastapi_openapi_and_endpoints(client):
    """REQ-041 Round 2: FastAPI OpenAPI schema 및 양방향 라우트 무결성 검증."""
    import warnings
    with warnings.catch_warnings(record=True) as recorded_warnings:
        warnings.simplefilter("always")
        schema = app.openapi()
        user_warnings = [
            w for w in recorded_warnings
            if issubclass(w.category, UserWarning) and "Duplicate Operation ID" in str(w.message)
        ]
        assert len(user_warnings) == 0, f"Duplicate Operation ID warnings detected: {user_warnings}"

    # Verify operation IDs exist in schema
    paths = schema.get("paths", {})
    assert "/api/export/hwpx" in paths
    hwpx_path = paths["/api/export/hwpx"]
    assert hwpx_path["get"]["operationId"] == "export_hwpx"
    assert hwpx_path["post"]["operationId"] == "export_hwpx_post"

    # Endpoints response integrity
    # 1. HWPX export GET & POST
    r_hwpx_get = client.get("/api/export/hwpx")
    assert r_hwpx_get.status_code == 200
    assert r_hwpx_get.json()["status"] == "success"

    r_hwpx_post = client.post("/api/export/hwpx", json={"title": "test_req041"})
    assert r_hwpx_post.status_code == 200
    assert r_hwpx_post.json()["status"] == "success"

    # 2. DOCX export GET & POST
    r_docx_get = client.get("/api/export/docx")
    assert r_docx_get.status_code == 200
    assert r_docx_get.json()["status"] == "success"

    r_docx_post = client.post("/api/export/docx", json={"title": "test_req041"})
    assert r_docx_post.status_code == 200
    assert r_docx_post.json()["status"] == "success"

    # 3. Audit verify GET & POST
    r_verify_get = client.get("/api/admin/audit/verify")
    assert r_verify_get.status_code == 200
    assert "ok" in r_verify_get.json()

    r_verify_post = client.post("/api/admin/audit/verify")
    assert r_verify_post.status_code == 200
    assert "ok" in r_verify_post.json()


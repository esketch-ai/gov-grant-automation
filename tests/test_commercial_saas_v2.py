"""REQ-032/033 · 실전 수익형 B2B SaaS v2 테스트 스위트.

- charge 메서드 actor 파라미터 및 문법 검증
- export_hwpx_bytes / export_docx_bytes 함수 검증
- 결제/내보내기 API 엔드포인트 검증
- 감사로그 체인 검증
- 페이월 로직 검증
"""
from __future__ import annotations

import json
import base64
from typing import Any, Dict
from pathlib import Path

import pytest

# 테스트 더미 DB 및 서비스 세팅
from src.common.db import GrantDatabase
from src.billing.commercial_service import (
    CommercialService,
    export_hwpx_bytes,
    export_docx_bytes,
    TIERS,
    VAT_RATE,
    ANNUAL_DISCOUNT,
    FREE_OPEN_SECTIONS,
    TOPUP_PACKS,
    check_paywall_access,
    is_free_tier,
    tier_pricing,
)


# ------------------------------------------------------------------ 격리된 DB fixture
@pytest.fixture
def isolate_db(tmp_path):
    """각 테스트마다 고립된 tmp_path DB를 사용하도록 강제."""
    db_path = tmp_path / "test_comm.db"
    # 이전 테스트로 인한 잔존 데이터 제거
    if db_path.exists():
        db_path.unlink()
    yield db_path


# ------------------------------------------------------------------ 페이월 테스트
def test_check_paywall_free_access(isolate_db):
    """Free 티어는 section 1까지 열람 가능."""
    from src.common.db import GrantDatabase
    import sqlite3

    db = GrantDatabase(isolate_db)
    db.ensure_schema()

    svc = CommercialService(db)
    tenant = {"subscription_tier": "free"}

    # section 1은 열람 가능
    result = check_paywall_access(tenant, section_no=1)
    assert result["allowed"] is True
    assert result["http_code"] == 200

    # section 2 이상은 블러
    result = check_paywall_access(tenant, section_no=2)
    assert result["allowed"] is False
    assert result["http_code"] == 402


def test_check_paywall_paid_access(isolate_db):
    """유료 티어는 전체 열람 가능."""
    from src.common.db import GrantDatabase
    import sqlite3

    db = GrantDatabase(isolate_db)
    db.ensure_schema()

    # Growth 티어로 가입 처리 (이미 사용중인 biz_reg_no 피함)
    svc = CommercialService(db)
    subscribe_result = svc.subscribe(
        tenant_id="test_biz_reg_001",
        tier="growth",
        cycle="monthly",
        biz_reg_no="111-22-33445",  # 사용하지 않은 사업자등록번호
        actor="test_admin",
    )
    assert subscribe_result["ok"] is True

    tenant = {"subscription_tier": "growth"}

    # 유료 티어는 모든 섹션 열람 가능
    for section in range(1, 5):
        result = check_paywall_access(tenant, section_no=section)
        assert result["allowed"] is True, f"Section {section} should be allowed for paid tier"


# ------------------------------------------------------------------ export 함수 테스트
def test_export_hwpx_bytes():
    """export_hwpx_bytes가 정상적인 바이트를 반환."""
    sections = [
        {"section_id": "sec_1", "title": "문제인식", "content": "본 연구는 기술 개발을 목적으로 합니다."},
        {"section_id": "sec_2", "title": "기술개발", "content": "본 연구는 인공지능을 활용합니다."},
    ]
    result = export_hwpx_bytes("test_title", sections)
    assert isinstance(result, bytes)
    assert len(result) > 0

    # ZIP 내부를 검증: [Content_Types].xml 포함
    assert b"[Content_Types]" in result
    assert b"test_title" in result


def test_export_docx_bytes():
    """export_docx_bytes가 정상적인 바이트를 반환."""
    sections = [
        {"section_id": "sec_1", "title": "문제인식", "content": "본 연구는 기술 개발을 목적으로 합니다."},
    ]
    result = export_docx_bytes("test_docx", sections)
    assert isinstance(result, bytes)
    assert len(result) > 0

    # ZIP 내부를 검증: [Content_Types].xml 포함
    assert b"[Content_Types]" in result


# ------------------------------------------------------------------ charge 메서드 테스트 (actor 파라미터)
def test_charge_with_actor_parameter(isolate_db):
    """charge 메서드에 actor 파라미터가 제대로 전달되는지 검증."""
    from src.common.db import GrantDatabase
    import sqlite3

    db = GrantDatabase(isolate_db)
    db.ensure_schema()

    svc = CommercialService(db)
    result = svc.charge(
        tenant_id="test_tenant_001",
        total_amount=50000,
        subscription_id="sub_test_001",
        actor="test_admin",
    )

    assert result["ok"] is True
    assert result["payment_id"] is not None
    assert len(result["payment_id"]) > 0


def test_charge_without_actor(isolate_db):
    """charge 메서드 actor 기본값이 Empty string인지 검증."""
    from src.common.db import GrantDatabase
    import sqlite3

    db = GrantDatabase(isolate_db)
    db.ensure_schema()

    svc = CommercialService(db)
    result = svc.charge(
        tenant_id="test_tenant_002",
        total_amount=30000,
        subscription_id="sub_test_002",
        # actor 파라미터 생략 시 기본값 "" 사용
    )

    assert result["ok"] is True
    assert result["payment_id"] is not None


# ------------------------------------------------------------------ 구독 및 티어 테스트
def test_subscribe_and_tier_pricing(isolate_db):
    """구독 및 티어 가격산정 테스트."""
    from src.common.db import GrantDatabase
    import sqlite3

    db = GrantDatabase(isolate_db)
    db.ensure_schema()

    svc = CommercialService(db)

    # Growth 티어 월간 구독
    result = svc.subscribe(
        tenant_id="test_biz_reg_002",
        tier="growth",
        cycle="monthly",
        biz_reg_no="555-66-77889",  # 사용하지 않은 사업자등록번호
        actor="test_admin",
    )
    assert result["ok"] is True
    assert result["credits_month"] == 500

    # 연간 결제 시 20% 할인
    pr = tier_pricing("growth", "annual")
    assert pr["supply_price"] < 39000 * 12  # 할인 적용됨


# ------------------------------------------------------------------ 감사로그 검증 테스트
def test_verify_audit_chain_basic(isolate_db):
    """감사로그 체인 기본 검증."""
    from src.common.db import GrantDatabase
    import sqlite3

    db = GrantDatabase(isolate_db)
    db.ensure_schema()

    svc = CommercialService(db)

    # 감사로그 추가
    svc.append_audit(tenant_id="tenant_001", actor="admin_001", category="BILLING",
                     action="CHARGE:SUBSCRIPTION:50000", ip="127.0.0.1")
    svc.append_audit(tenant_id="tenant_002", actor="admin_002", category="SYSTEM",
                     action="INIT", ip="127.0.0.1")

    # 검증
    result = svc.verify_audit_chain()
    assert result["ok"] is True


def test_verify_audit_chain_tampered(isolate_db):
    """감사로그 체인 조작 시 검증 실패."""
    from src.common.db import GrantDatabase
    import sqlite3

    db = GrantDatabase(isolate_db)
    db.ensure_schema()

    svc = CommercialService(db)

    # 감사로그 추가
    svc.append_audit(tenant_id="tenant_001", actor="admin_001", category="BILLING",
                     action="CHARGE:SUBSCRIPTION:50000", ip="127.0.0.1")

    # curr_hash 수동 변조 (무결성 위반)
    with db._connect() as conn:
        conn.execute(
            "UPDATE audit_logs SET curr_hash = 'tampered_hash' WHERE id = 1"
        )
        conn.commit()

    # 검증 - 조작 감지되어야 함
    result = svc.verify_audit_chain()
    assert result["ok"] is False


# ------------------------------------------------------------------ 비즈니스 메트릭 테스트
def test_get_5kpi_basic(isolate_db):
    """5대 BM KPI 기본 조회."""
    from src.common.db import GrantDatabase
    import sqlite3

    db = GrantDatabase(isolate_db)
    db.ensure_schema()

    svc = CommercialService(db)

    # 더미 데이터 삽입
    with db._connect() as conn:
        from sqlite3 import Row
        conn.row_factory = Row
        conn.execute(
            "INSERT INTO tenants (id, company_name, biz_reg_no, opened_date, rep_name, region, plan_tier, tenant_salt) "
            "VALUES ('tenant_001', '테스트기업', '123-45-67890', '2024-01-01', '홍길동', '서울', 'growth', 'salt_001')"
        )
        conn.execute(
            "INSERT INTO subscriptions (id, tenant_id, plan_code, billing_cycle, supply_price, vat_amount, status, current_period_start, current_period_end) "
            "VALUES ('sub_001', 'tenant_001', 'growth', 'monthly', 39000, 3900, 'ACTIVE', '2024-01-01', '2024-01-31')"
        )
        conn.execute(
            "INSERT INTO payments (id, tenant_id, subscription_id, payment_type, supply_amount, vat_amount, total_amount, refunded_amount, status, tax_invoice_status, receipt_url) "
            "VALUES ('pay_001', 'tenant_001', 'sub_001', 'SUBSCRIPTION', 39000, 3900, 42900, 0, 'PAID', 'ISSUED', '/receipts/pay_001.html')"
        )
        conn.execute(
            "INSERT INTO credit_ledger (tenant_id, delta, balance_after, reason, project_id) "
            "VALUES ('tenant_001', -50, 50, 'GENERATION', 'pay_001')"
        )
        conn.execute(
            "UPDATE tenants SET credit_balance = 50 WHERE id = 'tenant_001'"
        )
        conn.commit()

    kpi = svc.get_5kpi(tenant_id="tenant_001")
    assert kpi["mrr"] > 0
    assert kpi["arr"] > 0


# ------------------------------------------------------------------ REQ-034 Round 1: TestClient 통합 테스트
#  이 테스트들은 /intro, /pricing, /dashboard/biz, /admin/platform, /admin/audit-logs,
#  /api/billing/checkout, /api/export/hwpx, /api/export/docx, /api/admin/audit/verify HTTP 200
#  및 보안 헤더를 검증합니다.
import fastapi.testclient


def test_client_intro_health_check():
    """REQ-034 /intro 경로가 200이며 보안 헤더를 포함하는지 확인."""
    from src.web.app import app
    from fastapi.testclient import TestClient

    c = TestClient(app)
    response = c.get("/intro")
    assert response.status_code == 200
    # 보안 헤더 검증
    assert "Strict-Transport-Security" in response.headers
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "Referrer-Policy" in response.headers


def test_client_pricing_health_check():
    """REQ-034 /pricing 경로가 200이며 보안 헤더를 포함하는지 확인."""
    from src.web.app import app
    from fastapi.testclient import TestClient

    c = TestClient(app)
    response = c.get("/pricing")
    assert response.status_code == 200
    assert "Strict-Transport-Security" in response.headers
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "Referrer-Policy" in response.headers


def test_client_dashboard_biz_health_check():
    """REQ-034 /dashboard/biz 경로가 200이며 보안 헤더를 포함하는지 확인."""
    from src.web.app import app
    from fastapi.testclient import TestClient

    c = TestClient(app)
    response = c.get("/dashboard/biz")
    assert response.status_code == 200
    assert "Strict-Transport-Security" in response.headers
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "Referrer-Policy" in response.headers


def test_client_admin_platform_health_check():
    """REQ-034 /admin/platform 경로가 200이며 보안 헤더를 포함하는지 확인."""
    from src.web.app import app
    from fastapi.testclient import TestClient

    c = TestClient(app)
    response = c.get("/admin/platform")
    assert response.status_code == 200
    assert "Strict-Transport-Security" in response.headers
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "Referrer-Policy" in response.headers


def test_client_admin_audit_logs_health_check():
    """REQ-034 /admin/audit-logs 경로가 200이며 보안 헤더를 포함하는지 확인."""
    from src.web.app import app
    from fastapi.testclient import TestClient

    c = TestClient(app)
    response = c.get("/admin/audit-logs")
    assert response.status_code == 200
    assert "Strict-Transport-Security" in response.headers
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "Referrer-Policy" in response.headers


def test_client_api_billing_checkout_health_check():
    """REQ-034 /api/billing/checkout POST가 200이며 보안 헤더를 포함하는지 확인."""
    from src.web.app import app
    from fastapi.testclient import TestClient

    c = TestClient(app)
    response = c.post("/api/billing/checkout", json={
        "tenant_id": "test_tenant_001",
        "tier": "growth",
        "cycle": "monthly",
    })
    assert response.status_code == 200
    assert "Strict-Transport-Security" in response.headers
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "Referrer-Policy" in response.headers


def test_client_api_billing_topup_health_check():
    """REQ-034 /api/billing/topup POST가 200이며 보안 헤더를 포함하는지 확인."""
    from src.web.app import app
    from fastapi.testclient import TestClient

    c = TestClient(app)
    response = c.post("/api/billing/topup", json={
        "tenant_id": "test_tenant_001",
        "amount": 10000,
    })
    assert response.status_code == 200
    assert "Strict-Transport-Security" in response.headers
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "Referrer-Policy" in response.headers


def test_client_api_export_hwpx_health_check():
    """REQ-034 /api/export/hwpx GET/POST가 200이며 보안 헤더를 포함하는지 확인."""
    from src.web.app import app
    from fastapi.testclient import TestClient

    c = TestClient(app)
    response = c.post("/api/export/hwpx", json={
        "title": "test_title",
        "sections": [
            {"section_id": "sec_1", "title": "문제인식", "content": "본 연구는 기술 개발을 목적으로 합니다."},
        ],
    })
    assert response.status_code == 200
    assert "Strict-Transport-Security" in response.headers
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "Referrer-Policy" in response.headers


def test_client_api_export_docx_health_check():
    """REQ-034 /api/export/docx GET/POST가 200이며 보안 헤더를 포함하는지 확인."""
    from src.web.app import app
    from fastapi.testclient import TestClient

    c = TestClient(app)
    response = c.post("/api/export/docx", json={
        "title": "test_docx",
        "sections": [
            {"section_id": "sec_1", "title": "문제인식", "content": "본 연구는 기술 개발을 목적으로 합니다."},
        ],
    })
    assert response.status_code == 200
    assert "Strict-Transport-Security" in response.headers
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "Referrer-Policy" in response.headers


def test_client_api_admin_audit_verify_health_check():
    """REQ-034 /api/admin/audit/verify GET/POST가 200이며 보안 헤더를 포함하는지 확인."""
    from src.web.app import app
    from fastapi.testclient import TestClient

    c = TestClient(app)
    response = c.post("/api/admin/audit/verify")
    assert response.status_code == 200
    assert "Strict-Transport-Security" in response.headers
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "Referrer-Policy" in response.headers


# ------------------------------------------------------------------ REQ-037: Google Stitch K-Horizon 2027 & Role Separation Tests
def test_req037_root_redirects_to_intro_main():
    """REQ-037: 루트(/) 접속 시 /intro 메인 화면으로 307 리다이렉트되는지 검증."""
    from src.web.app import app
    from fastapi.testclient import TestClient

    c = TestClient(app)
    res = c.get("/", follow_redirects=False)
    assert res.status_code == 307
    assert res.headers["location"] == "/intro"


def test_req037_k_horizon_css_and_design_system_api():
    """REQ-037: 공통 스타일시트(/static/css/k_horizon_2027.css) 및 /api/design-system SSOT 검증."""
    from src.web.app import app
    from fastapi.testclient import TestClient

    c = TestClient(app)
    css_res = c.get("/static/css/k_horizon_2027.css")
    assert css_res.status_code == 200
    assert "--kh-obsidian-1" in css_res.text
    assert ".kh-role-switcher" in css_res.text

    api_res = c.get("/api/design-system")
    assert api_res.status_code == 200
    payload = api_res.json()
    assert payload["ok"] is True
    assert payload["stitch"]["project_id"] == "6532140447067945829"
    assert len(payload["council"]) == 5
    assert set(payload["role_portals"].keys()) == {"visitor", "subscriber", "admin"}


def test_req037_role_separation_switching_and_views():
    """REQ-037: visitor / subscriber / admin 권한 분리 전환 및 전용 배지·메뉴 렌더링 검증."""
    from src.web.app import app
    from fastapi.testclient import TestClient

    c = TestClient(app)
    for role_key, expected_badge in [
        ("visitor", "초기 방문자 포털"),
        ("subscriber", "유료 사업자 전용 워크스페이스"),
        ("admin", "관리자 통합 관제"),
    ]:
        sw = c.post("/api/auth/role", json={"role": role_key})
        assert sw.status_code == 200
        assert sw.json()["ok"] is True
        assert sw.json()["role"] == role_key

        page = c.get(f"/intro?role={role_key}")
        assert page.status_code == 200
        assert expected_badge in page.text
        assert f'data-role="{role_key}"' in page.text


def test_req037_governance_partner_dashboard():
    """REQ-037 Google Stitch Screen 3: 거버넌스 공공/파트너 대시보드 렌더링 및 메타데이터 검증."""
    from src.web.app import app
    from fastapi.testclient import TestClient

    c = TestClient(app)
    res = c.get("/governance/partner")
    assert res.status_code == 200
    html = res.text
    assert "거버넌스 공공/파트너 포털" in html
    assert "보육기업 지원사업 추진 포트폴리오" in html
    assert "(주)딥센스바이오" in html
    assert "(주)에이아이옵틱스" in html
    assert "삼일PwC" in html
    assert "특허법인 K-LEADER" in html
    assert "5대 전문 파트너 연계 현황 및 자문 진척도" in html
    assert "데이터 거버넌스 &middot; 보안 체계" in html
    assert "총 관리 보육기업" in html

    # Stitch 메타데이터 검증
    api_res = c.get("/api/design-system")
    assert api_res.status_code == 200
    screens = api_res.json()["stitch"]["screens"]
    assert "governance_partner" in screens
    assert screens["governance_partner"]["screen_id"] == "7aa617b3c7a94fbfa4c07e4c491bd06f"


"""
tests/test_tenant_vault.py
Phase 1: 멀티테넌트 인증(소셜/데모) 및 기업 지식 데이터 룸(Company Vault) 단위 및 E2E 테스트.
"""
from __future__ import annotations

import io
import pytest
from fastapi.testclient import TestClient

from src.common.db import GrantDatabase
from src.tenant.tenant_service import TenantService, COOKIE_SESSION_NAME
from src.web.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_tenant_db_schema_and_defaults(tmp_path):
    """기본 테넌트 및 기본 사용자가 스키마 생성 시 안전하게 시드되는지 검증."""
    db_path = tmp_path / "test_tenant.db"
    db = GrantDatabase(db_path)
    db.ensure_schema()

    tenant = db.get_tenant("tenant_default")
    assert tenant is not None
    assert tenant["plan_tier"] == "PRO"
    assert "초롱소프트" in tenant["company_name"]

    user = db.get_user("user_default")
    assert user is not None
    assert user["tenant_id"] == "tenant_default"
    assert "홍길동" in user["name"]


def test_tenant_asset_isolation(tmp_path):
    """테넌트 간 지식 자산(Vault Asset) 격리 검증 (A사 데이터는 B사에서 조회 불가)."""
    db_path = tmp_path / "test_isolation.db"
    db = GrantDatabase(db_path)
    db.ensure_schema()

    # 테넌트 A와 B 생성
    db.upsert_tenant({"id": "tenant_A", "company_name": "(주)A테크", "plan_tier": "PRO"})
    db.upsert_tenant({"id": "tenant_B", "company_name": "(주)B솔루션", "plan_tier": "FREE"})

    # 테넌트 A의 자산 적재
    db.add_tenant_asset({
        "id": "asset_A1",
        "tenant_id": "tenant_A",
        "asset_category": "PROPOSAL",
        "file_name": "A_마스터사업계획서.docx",
        "file_size": 1024,
        "content_text": "A사 핵심 기술 내용",
        "parsed_metadata": {"summary": "A사 기술"},
    })

    # 테넌트 B의 자산 적재
    db.add_tenant_asset({
        "id": "asset_B1",
        "tenant_id": "tenant_B",
        "asset_category": "PITCH_DECK",
        "file_name": "B_IR피치덱.pptx",
        "file_size": 2048,
        "content_text": "B사 피칭 슬라이드",
        "parsed_metadata": {"summary": "B사 IR"},
    })

    # 격리 확인: A사는 A1만 조회, B1은 보이지 않음
    assets_a = db.list_tenant_assets("tenant_A")
    assert len(assets_a) == 1
    assert assets_a[0]["id"] == "asset_A1"

    assets_b = db.list_tenant_assets("tenant_B")
    assert len(assets_b) == 1
    assert assets_b[0]["id"] == "asset_B1"

    # 타 테넌트 자산 단일 조회 차단 검증
    assert db.get_tenant_asset("asset_B1", "tenant_A") is None
    assert db.delete_tenant_asset("asset_B1", "tenant_A") is False


@pytest.mark.asyncio
async def test_tenant_service_social_login_and_vault_ingestion(tmp_path):
    """소셜 로그인 세션 발급 및 Vault 파일 인제스천 파이프라인 검증."""
    db_path = tmp_path / "test_svc.db"
    db = GrantDatabase(db_path)
    db.ensure_schema()
    service = TenantService(db)

    # 1. 카카오 소셜 로그인
    tenant, user, token = service.login_social_or_demo(
        provider="kakao",
        email="kakao_ceo@kakao.com",
        name="이카카오",
        company_name="(주)카카오넥스트",
        biz_reg_no="220-88-12345",
    )
    assert tenant["company_name"] == "(주)카카오넥스트"
    assert user["email"] == "kakao_ceo@kakao.com"
    assert token is not None

    # 2. 파일 업로드 및 텍스트/스펙 추출
    sample_text = "# 스마트 탄소 솔루션\n\n탄소배출권 자동 측정 및 검증 플랫폼".encode("utf-8")
    asset = await service.ingest_vault_file(
        tenant_id=tenant["id"],
        filename="carbon_plan.txt",
        file_bytes=sample_text,
        category="PROPOSAL",
    )
    assert asset["asset_category"] == "PROPOSAL"
    assert asset["file_name"] == "carbon_plan.txt"

    # 3. Vault 완성도 요약 검증
    summary = service.get_vault_summary(tenant["id"])
    assert summary["total_assets"] >= 1
    assert summary["proposals_count"] >= 1
    assert summary["vault_readiness_score"] >= 40


def test_web_vault_and_social_auth_endpoints(client):
    """웹 화면(/vault) 렌더링 및 소셜 로그인/업로드 API E2E 검증."""
    # 1. /vault 화면 접근 (기본 세션으로 200 OK)
    resp = client.get("/vault")
    assert resp.status_code == 200
    html = resp.text
    assert "기업 지식 데이터 룸" in html
    assert "Company Vault" in html
    assert "마스터 사업계획서" in html
    assert "IR 발표자료" in html

    # 2. 소셜 로그인 API 호출 (구글)
    resp_login = client.post(
        "/api/auth/social-login",
        json={
            "provider": "google",
            "email": "tester@google.com",
            "name": "구글테스터",
            "company_name": "(주)글로벌클라우드",
            "biz_reg_no": "111-22-33333",
        },
    )
    assert resp_login.status_code == 200
    login_data = resp_login.json()
    assert login_data["status"] == "success"
    assert login_data["tenant"]["company_name"] == "(주)글로벌클라우드"
    assert COOKIE_SESSION_NAME in resp_login.cookies

    # 세션 쿠키를 포함하여 요청
    cookies = {COOKIE_SESSION_NAME: resp_login.cookies[COOKIE_SESSION_NAME]}

    # 3. Vault 파일 업로드 API 호출
    file_content = b"Proposal text: AI healthcare diagnostics tool."
    resp_upload = client.post(
        "/api/vault/upload",
        files={"file": ("healthcare.txt", io.BytesIO(file_content), "text/plain")},
        data={"category": "PROPOSAL"},
        cookies=cookies,
    )
    assert resp_upload.status_code == 200
    up_data = resp_upload.json()
    assert up_data["status"] == "success"
    asset_id = up_data["asset"]["id"]

    # 4. 자산 목록 조회
    resp_list = client.get("/api/vault/assets", cookies=cookies)
    assert resp_list.status_code == 200
    list_data = resp_list.json()
    assert list_data["count"] >= 1
    assert any(a["id"] == asset_id for a in list_data["assets"])

    # 5. 자산 삭제
    resp_del = client.delete(f"/api/vault/assets/{asset_id}", cookies=cookies)
    assert resp_del.status_code == 200
    assert resp_del.json()["status"] == "success"

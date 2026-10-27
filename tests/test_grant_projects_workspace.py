"""
tests/test_grant_projects_workspace.py
REQ-029 · Vault 자산 기반 초정밀 매칭기 + /projects 도전 과제 워크스페이스
    - VaultPreflightMatcher: 가상 company_specs 산출 / RED 자동제거 / final_score 정렬 / bonus count
    - DB 레벨 테넌트 격리 (create/list/get/update/delete 모두 tenant_id 스코핑)
    - E2E: /projects 200, 도전과제 CRUD, 타 테넌트 차단
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.common.db import GrantDatabase
from src.common.schemas import RawNotice
from src.matcher.vault_preflight import VaultPreflightMatcher
from src.tenant.tenant_service import TenantService, COOKIE_SESSION_NAME
import src.web.app as app_module
from src.web.app import app


# ---------------------------------------------------------------------------
# 1. VaultPreflightMatcher 단위 테스트 (가상 프로파일 + RED 자동제거 + 정렬)
# ---------------------------------------------------------------------------
class _FakePreflight:
    """run() 결과를 제어하는 더블 — 실제 매칭 로직에 의존하지 않고
     RED 제외/정렬/bonus count만 검증."""

    def __init__(self, verdicts):
        self.verdicts = list(verdicts)
        self.calls = 0

    def run(self, specs, notice):
        v = self.verdicts[self.calls]
        self.calls += 1
        return v


def _notice(portal_id, title="테스트공고", org="한국기술투자", ministry="산업부",
            deadline="2026-12-15", url=""):
    return RawNotice(portal_id=portal_id, title=title, organization=org,
                     ministry=ministry, deadline=deadline, detail_url=url)


def test_vault_matcher_red_excluded_and_sorted(tmp_path):
    """RED(사전탈락)는 결과에서 제외되고, 나머지는 final_score 내림차순으로 정렬."""
    db = GrantDatabase(tmp_path / "m.db")
    db.ensure_schema()

    verdicts = [
        {"signal_light": "red", "final_score": 0, "bonus_points": [],
         "matched_track": "X", "tags": [], "pass_reasons": [], "disqualification_reasons": ["유력 자격 미충족"]},
        {"signal_light": "yellow", "final_score": 72, "bonus_points": ["a", "b"],
         "matched_track": "Y", "tags": [], "pass_reasons": [], "disqualification_reasons": []},
        {"signal_light": "green", "final_score": 95, "bonus_points": ["a", "b", "c", "d"],
         "matched_track": "G", "tags": ["여성대표"], "pass_reasons": [], "disqualification_reasons": []},
    ]
    notices = [_notice("n1"), _notice("n2"), _notice("n3")]
    fake = _FakePreflight(verdicts)

    m = VaultPreflightMatcher(db=db, preflight=fake)
    res = m.match("tenant_A", notices)

    # RED(n1) 제외 → 2건만 남음
    assert len(res) == 2
    # final_score 내림차순 → n3(95) 먼저, n2(72) 다음
    assert [r["canonical_id"] for r in res] == ["n3", "n2"]
    # bonus_points는 리스트 → 개수(int)로 표현
    assert res[0]["bonus_points"] == 4
    assert res[1]["bonus_points"] == 2
    # canonical_id는 notice.portal_id에서 온다
    assert res[0]["match_score"] == 95
    assert res[0]["tags"] == ["여성대표"]


def test_vault_matcher_build_company_specs_from_assets(tmp_path):
    """tenants + tenant_assets.parsed_metadata를 취합해 가상 company_specs를 산출."""
    db = GrantDatabase(tmp_path / "m2.db")
    db.ensure_schema()
    db.upsert_tenant({"id": "tenant_A", "company_name": "(주)A테크", "region": "경기",
                      "biz_reg_no": "110-22-33333", "opened_date": "2021-03-01"})
    db.add_tenant_asset({
        "id": "pa1", "tenant_id": "tenant_A", "asset_category": "IP",
        "file_name": "특허.json", "file_size": 10,
        "parsed_metadata": {"has_patents": True, "patents_count": 3, "trl": 6,
                            "certifications": ["ISO14001", "ISO9001"]},
    })
    m = VaultPreflightMatcher(db=db)
    specs = m.build_company_specs("tenant_A")
    assert specs["company_name"] == "(주)A테크"
    assert specs["has_patents"] is True
    assert specs["patents_count"] == 3
    assert specs["trl_levels"] == [6]
    assert set(specs["certifications"]) == {"ISO14001", "ISO9001"}


# ---------------------------------------------------------------------------
# 2. DB 레벨 테넌트 격리 (도전 과제 CRUD)
# ---------------------------------------------------------------------------
def _seed_notice(db, canonical_id="ANN-REQ029-01"):
    return db.upsert_announcement(
        _notice(canonical_id, "국가지원 도전과제", "한국산업기술평가관리원", "중기부",
                "2026-11-30", "https://www.sbir.or.kr/ann/1"),
        canonical_id, target_year=2026,
    )


def test_grant_projects_cross_tenant_db_isolation(tmp_path):
    """A사 프로젝트는 B사에서 조회/수정/삭제 불가 (모든 경로 tenant_id 스코핑)."""
    db = GrantDatabase(tmp_path / "iso.db")
    db.ensure_schema()
    db.upsert_tenant({"id": "tenant_A", "company_name": "(주)A테크"})
    db.upsert_tenant({"id": "tenant_B", "company_name": "(주)B솔루션"})
    _seed_notice(db)

    pid = db.create_grant_project({
        "tenant_id": "tenant_A", "announcement_id": "ANN-REQ029-01",
        "announcement_title": "국가지원 도전과제", "template_id": "PSST",
        "status": "INIT", "progress_pct": 0,
    })

    # 목록 격리
    a_list = db.list_grant_projects("tenant_A")
    b_list = db.list_grant_projects("tenant_B")
    assert len(a_list) == 1 and a_list[0]["id"] == pid
    assert b_list == []

    # 단일 조회 격리
    assert db.get_grant_project(pid, "tenant_A") is not None
    assert db.get_grant_project(pid, "tenant_B") is None

    # 수정 격리: B가 A의 프로젝트를 수정하면 rowcount=0 (False)
    assert db.update_grant_project(pid, "tenant_B", status="DONE", progress_pct=50) is False
    assert db.get_grant_project(pid, "tenant_A")["status"] == "INIT"  # 그대로

    # A가 정당한 수정
    assert db.update_grant_project(pid, "tenant_A", status="DONE", progress_pct=90) is True
    assert db.get_grant_project(pid, "tenant_A")["progress_pct"] == 90

    # 삭제 격리: B의 삭제는 실패, A의 삭제는 성공
    assert db.delete_grant_project(pid, "tenant_B") is False
    assert db.get_grant_project(pid, "tenant_A") is not None
    assert db.delete_grant_project(pid, "tenant_A") is True
    assert db.get_grant_project(pid, "tenant_A") is None


def test_grant_project_allowlist_and_clamp(tmp_path):
    """허용 컬럼만 반영, progress 0-100 클램프, no-op은 존재 여부만 반환."""
    db = GrantDatabase(tmp_path / "clamp.db")
    db.ensure_schema()
    db.upsert_tenant({"id": "tenant_A", "company_name": "(주)A"})
    _seed_notice(db)
    pid = db.create_grant_project({"tenant_id": "tenant_A", "announcement_id": "ANN-REQ029-01"})

    # 허용리스트 외부 컬럼은 무시 (존재 여부만 True 반환 — 변경 없음)
    assert db.update_grant_project(pid, "tenant_A", announcement_title="변경", evil="x") is True
    row = db.get_grant_project(pid, "tenant_A")
    assert row["announcement_title"] == "변경"

    # 진행률 클램프
    db.update_grant_project(pid, "tenant_A", progress_pct=150)
    assert db.get_grant_project(pid, "tenant_A")["progress_pct"] == 100
    db.update_grant_project(pid, "tenant_A", progress_pct=-5)
    assert db.get_grant_project(pid, "tenant_A")["progress_pct"] == 0

    # no-op (변경 컬럼 없음) → 존재 여부만
    assert db.update_grant_project(pid, "tenant_A") is True
    assert db.update_grant_project("nope", "tenant_A") is False


# ---------------------------------------------------------------------------
# 3. E2E (테넌트 격리 워크스페이스) — 앱 globals을 tmp db로 바인드
# ---------------------------------------------------------------------------
@pytest.fixture
def bound_app(tmp_path):
    """app 모듈의 _get_db/_tenant_service/_vault_matcher를 tmp db로 바인드 후 복구."""
    db = GrantDatabase(tmp_path / "e2e.db")
    db.ensure_schema()
    _seed_notice(db, "ANN-REQ029-01")

    orig_db = app_module._get_db
    orig_svc = app_module._tenant_service
    orig_matcher = app_module._vault_matcher
    app_module._get_db = lambda: db
    app_module._tenant_service = TenantService(db)
    app_module._vault_matcher = None
    try:
        yield db, TestClient(app)
    finally:
        app_module._get_db = orig_db
        app_module._tenant_service = orig_svc
        app_module._vault_matcher = orig_matcher


def test_projects_view_renders(bound_app):
    """/projects 화면이 기본 세션으로 200 렌더링."""
    _, client = bound_app
    resp = client.get("/projects")
    assert resp.status_code == 200
    assert "도전" in resp.text or "Project" in resp.text or "challenge" in resp.text.lower()


def _login(client, email, name, company):
    r = client.post("/api/auth/social-login", json={
        "provider": "kakao", "email": email, "name": name,
        "company_name": company, "biz_reg_no": "111-22-33333",
    })
    assert r.status_code == 200
    return {COOKIE_SESSION_NAME: r.cookies[COOKIE_SESSION_NAME]}


def test_project_crud_and_cross_tenant_e2e(bound_app):
    """동일 공고로 A가 등록 → B는 조회/수정/삭제 불가 (E2E 격리)."""
    db, client = bound_app
    # 동일 이메일 재로그인은 동일 테넌트 / 다른 이메일은 다른 테넌트
    cookies_a1 = _login(client, "ceoA@a.co.kr", "A대표", "(주)A테크")
    dbA = app_module._get_db()
    tA = dbA.get_user_by_email("ceoA@a.co.kr")["tenant_id"]
    assert _login(client, "ceoA@a.co.kr", "A대표", "(주)A테크")  # same tenant
    assert dbA.get_user_by_email("ceoA@a.co.kr")["tenant_id"] == tA

    # A가 도전 과제 등록
    resp = client.post("/api/projects", json={"canonical_id": "ANN-REQ029-01",
                                              "template_id": "PSST"}, cookies=cookies_a1)
    assert resp.status_code == 200
    pid = resp.json()["project_id"]
    assert pid

    # 유효하지 않은 canonical_id → 400
    r_bad = client.post("/api/projects", json={"canonical_id": "x..;DROP"}, cookies=cookies_a1)
    assert r_bad.status_code == 400
    # 존재하지 않는 공고 → 404
    r_404 = client.post("/api/projects", json={"canonical_id": "NOT-EXISTS"}, cookies=cookies_a1)
    assert r_404.status_code == 404

    # A의 목록/수정/삭제
    la = client.get("/api/projects", cookies=cookies_a1)
    assert la.status_code == 200
    assert any(p["id"] == pid for p in la.json()["projects"])

    up = client.patch(f"/api/projects/{pid}", json={"status": "DRAFTING", "progress_pct": 42},
                      cookies=cookies_a1)
    assert up.status_code == 200
    lp = client.get("/api/projects", cookies=cookies_a1).json()["projects"]
    assert next(p for p in lp if p["id"] == pid)["progress_pct"] == 42

    # B는 A의 프로젝트를 수정/삭제 불가
    client_b = TestClient(app)
    cookies_b = _login(client_b, "ceoB@b.co.kr", "B대표", "(주)B솔루션")
    lb = client_b.get("/api/projects", cookies=cookies_b).json()
    assert not any(p["id"] == pid for p in lb["projects"])

    up_b = client_b.patch(f"/api/projects/{pid}", json={"status": "DONE"}, cookies=cookies_b)
    assert up_b.status_code == 404
    del_b = client_b.delete(f"/api/projects/{pid}", cookies=cookies_b)
    assert del_b.status_code == 404

    # A가 삭제
    d = client.delete(f"/api/projects/{pid}", cookies=cookies_a1)
    assert d.status_code == 200
    # 중복 삭제 → 404
    assert client.delete(f"/api/projects/{pid}", cookies=cookies_a1).status_code == 404

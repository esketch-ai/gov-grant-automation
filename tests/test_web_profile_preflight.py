"""
REQ-020 · 사업주 프로필 및 사전 비행점검 웹 연동 단위 테스트
- GET /api/profile
- POST /api/profile
- POST /api/matcher/preflight
- /announcements (트랙 탭 및 배너)
- /dashboard (맞춤 추천 및 배너)
"""
import pytest
from starlette.testclient import TestClient
from src.web.app import app, PROJECT_ROOT
from src.common.db import GrantDatabase


@pytest.fixture
def client():
    db = GrantDatabase(PROJECT_ROOT / "storage" / "grant_master.db")
    db.ensure_schema()
    original_prof = db.get_company_profile()
    try:
        yield TestClient(app)
    finally:
        if original_prof and original_prof.get("company_name"):
            db.upsert_company_profile(original_prof)
        else:
            db.clear_company_profile()



def test_api_profile_empty_or_configured(client):
    """프로필 조회 API 기본 동작 테스트."""
    res = client.get("/api/profile")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "configured" in data


def test_api_profile_save_and_retrieve(client):
    """프로필 저장 및 자격 태그 자동 산출 테스트."""
    payload = {
        "company_name": "(주)마음숲연구소",
        "biz_reg_no": "607-81-12345",
        "opened_date": "2024-03-01",
        "founder_birth": "1994-05-15",
        "founder_gender": "F",
        "address": "부산광역시 해운대구 센텀중앙로 48",
        "debt_ratio_pct": 180.5,
        "has_rnd_lab": False,
        "is_capital_impaired": False,
        "has_tax_arrears": False,
        "current_pi_projects": 1,
        "registered_patents_count": 2,
        "prior_grant_history": ["예비창업패키지"],
        "certifications": ["여성기업", "벤처기업"],
    }
    res = client.post("/api/profile", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["profile"]["company_name"] == "(주)마음숲연구소"
    assert data["calculated"] is not None
    assert data["calculated"]["is_female_founder"] is True
    assert data["calculated"]["is_youth_39"] is True
    assert any("여성기업" in t for t in data["tags"])

    # GET 재조회 검증
    get_res = client.get("/api/profile")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["configured"] is True
    assert get_data["profile"]["company_name"] == "(주)마음숲연구소"


def test_api_preflight_validation(client):
    """사전 비행점검(Preflight) API 테스트."""
    # 1) 잘못된 요청 (canonical_id 누락)
    bad_res = client.post("/api/matcher/preflight", json={})
    assert bad_res.status_code == 400

    # 2) 존재하지 않는 공고 ID -> 404
    notfound_res = client.post("/api/matcher/preflight", json={"canonical_id": "none:nonexistent"})
    assert notfound_res.status_code == 404

    # 3) 실제 공고에 대한 비행점검
    pf_res = client.post(
        "/api/matcher/preflight",
        json={"canonical_id": "k_startup:2026_master_biz"}
    )
    assert pf_res.status_code == 200
    pf_data = pf_res.json()
    assert pf_data["status"] == "success"
    assert "preflight" in pf_data
    pf = pf_data["preflight"]
    assert pf["status"] in ("GREEN", "YELLOW", "RED")
    assert pf["signal_light"] in ("green", "yellow", "red")
    assert "final_score" in pf
    assert "matched_track" in pf
    assert isinstance(pf["pass_reasons"], list)
    assert isinstance(pf["warnings"], list)


def test_web_announcements_track_tab_rendering(client):
    """공고 목록 뷰에서 트랙 탭 및 배너 렌더링 검증."""
    res = client.get("/announcements?tab=ALL")
    assert res.status_code == 200
    html = res.text
    assert "다차원 맞춤 필터" in html
    assert "사전 비행점검" in html
    assert "profileModal" in html
    assert "preflightModal" in html

    # 특정 트랙 필터링
    res_track = client.get("/announcements?tab=EARLY_STARTUP")
    assert res_track.status_code == 200


def test_web_dashboard_recommendation_rendering(client):
    """대시보드 뷰에서 맞춤 추천 카드 및 프로필 배너 렌더링 검증."""
    res = client.get("/dashboard")
    assert res.status_code == 200
    html = res.text
    assert "맞춤 추천 (GREEN)" in html
    assert "현재 적용 사업주 프로필" in html or "사업주 프로필 미등록" in html

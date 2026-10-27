"""
tests/test_master_grant_directory.py
K-Startup 통합공고 종합 정리함 마스터 디렉토리 및 로드맵 API 단위 테스트.
"""
import pytest
from fastapi.testclient import TestClient
from src.web.app import app
from src.common.master_grant_directory import (
    MASTER_GRANT_CATALOG,
    MasterGrantService,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_master_grant_catalog_coverage():
    """대한민국 17개 지자체 및 중앙부처 통합공고 30선 이상 커버리지 검증."""
    service = MasterGrantService()
    programs = service.get_all_programs()
    assert len(programs) >= 30

    # 1. 17개 지자체 전역 커버리지 확인
    all_regions = {"서울", "부산", "경기", "인천", "대구", "대전", "광주", "울산", "세종", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"}
    covered_regions = {p["region_scope"] for p in programs if p["region_scope"] != "전국"}
    assert all_regions.issubset(covered_regions), f"누락된 지자체: {all_regions - covered_regions}"

    # 2. 7대 핵심 중앙부처 커버리지 확인
    ministries = {p["supervising_ministry"] for p in programs}
    assert "중소벤처기업부" in ministries
    assert "과학기술정보통신부" in ministries
    assert "산업통상자원부" in ministries
    assert "보건복지부" in ministries
    assert "농림축산식품부" in ministries
    assert "방위사업청" in ministries


def test_master_grant_filter_by_region():
    """지역별 필터링 시 전국 공고와 해당 지역 전용 공고가 정확히 추출되는지 검증."""
    service = MasterGrantService()

    # 부산 지역 필터
    busan_list = service.get_all_programs(region="부산")
    assert len(busan_list) > 0
    # 전국 공고 + 부산 전용 공고만 포함되어야 함 (타 지자체 전용은 배제)
    for p in busan_list:
        assert p["region_scope"] in ("전국", "부산")

    # 부산 브라이트클럽 포함 확인
    bright_club = [p for p in busan_list if "브라이트클럽" in p["program_name"]]
    assert len(bright_club) == 1
    assert bright_club[0]["region_scope"] == "부산"
    assert bright_club[0]["operating_agency"] == "부산테크노파크 / 부산창조경제혁신센터"


def test_master_grant_monthly_timeline():
    """월별(개략적 공고 시기) 타임라인 분포가 정상 생성되는지 검증."""
    service = MasterGrantService()
    timeline = service.get_monthly_timeline()

    assert "1월" in timeline and len(timeline["1월"]) >= 1  # 청년사관학교, 초격차
    assert "2월" in timeline and len(timeline["2월"]) >= 5  # 예비창업, 초기창업, AI바우처 등
    assert "3월" in timeline and len(timeline["3월"]) >= 5  # 도약패키지, 서울형R&D 등
    assert "연중 수시" in timeline and len(timeline["연중 수시"]) >= 1  # TIPS


def test_master_grant_recommendation_for_item():
    """사업 아이템의 프로필(지역, 키워드, 업력)에 따라 맞춤형 연간 과제가 추천되는지 검증."""
    service = MasterGrantService()

    # 부산 소재 AI/기후테크 기업 프로필 모의
    profile = {
        "item_meta": {"item_id": "test_busan_ai", "item_name": "부산 해양 AI 플랫폼"},
        "company_specs": {
            "address": "부산광역시 해운대구 센텀중앙로",
            "business_age_years": 1.5,
        },
        "domain_routing": {
            "core_keywords": ["AI", "빅데이터", "플랫폼"],
        },
    }

    recs = service.recommend_roadmap_for_item(profile)
    assert len(recs) > 0

    # 추천 상위 과제에 부산 브라이트클럽 또는 초기창업/AI바우처가 포함되어야 함
    rec_names = [r["program_name"] for r in recs[:5]]
    assert any("부산" in name or "AI" in name or "초기창업" in name for name in rec_names)
    assert recs[0]["recommendation_score"] >= 70


def test_api_master_grants_endpoints(client):
    """GET /api/portals/master-grants 및 타임라인 API 검증."""
    # 1. 전체 마스터 과제 조회
    r1 = client.get("/api/portals/master-grants")
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["status"] == "success"
    assert d1["count"] >= 30

    # 2. 지역 및 분야 필터 조회
    r2 = client.get("/api/portals/master-grants", params={"region": "서울", "category": "기술개발(R&D)"})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["status"] == "success"
    assert any("서울형 R&D" in p["program_name"] for p in d2["programs"])

    # 3. 월별 타임라인 API
    r3 = client.get("/api/portals/master-grants/timeline")
    assert r3.status_code == 200
    d3 = r3.json()
    assert "2월" in d3["timeline"]

    # 4. 사업 아이템 연간 과제 추천 API
    r4 = client.get("/api/portals/master-grants/recommend/item_01_carbon_dmrv")
    assert r4.status_code == 200
    d4 = r4.json()
    assert d4["status"] == "success"
    assert d4["count"] > 0

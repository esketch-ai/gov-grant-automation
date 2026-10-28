"""
tests/test_global_grants_portal.py
해외 주요 선진국 및 거점 도시 특화 유치 지원사업 및 포털 연동 테스트.
(영국 DBT GEP, 프랑스 Cité/Station F, 호주 Austrade/Landing Pad, UAE Hub71, 대한민국 KSC)
"""
import pytest
from fastapi.testclient import TestClient
from src.web.app import app
from src.common.global_grant_directory import (
    GLOBAL_GRANTS_CATALOG,
    GlobalGrantsService,
    GlobalGrantProgram,
)
from src.common.portal_manager import PortalStatusService


@pytest.fixture
def client():
    return TestClient(app)


def test_global_grants_catalog_content():
    """5대 글로벌 거점(영국, 프랑스, 호주, UAE, 대한민국)의 대표 과제 커버리지 검증."""
    service = GlobalGrantsService()
    programs = service.get_all_programs()
    assert len(programs) >= 8

    countries = {p["country"] for p in programs}
    assert "영국" in countries
    assert "프랑스" in countries
    assert "호주" in countries
    assert "UAE" in countries
    assert "대한민국" in countries

    # 1. 영국 GEP 비자 특혜 확인
    uk_gep = [p for p in programs if p["program_id"] == "UK-DBT-GEP-2026"][0]
    assert "딜메이커" in uk_gep["operating_entity"]
    assert "혁신가 창업자 비자" in uk_gep["visa_benefit"]
    assert "3년" in uk_gep["visa_benefit"]

    # 2. 프랑스 Cité 40m² 레지던시 확인
    fr_cite = [p for p in programs if p["program_id"] == "FR-CITE-SAMSUNG-2026"][0]
    assert "40m²" in fr_cite["space_facility_benefit"]
    assert "전액" in fr_cite["financial_benefit"]

    # 3. 호주 Landing Pad West Tech Fest 확인
    au_pad = [p for p in programs if p["program_id"] == "AU-DFAT-LANDING-PAD-2026"][0]
    assert "Spacecubed" in au_pad["operating_entity"]
    assert "호스피탈리티" in au_pad["specialized_fields"]

    # 4. UAE 아부다비 Hub71 750,000 AED 확인
    uae_hub = [p for p in programs if p["program_id"] == "UAE-ADGM-HUB71-2026"][0]
    assert "750,000 AED" in uae_hub["financial_benefit"]
    assert "골든 비자" in uae_hub["visa_benefit"]


def test_global_grants_filter_by_country_and_field():
    """국가별 및 특화 분야별 필터링 기능 검증."""
    service = GlobalGrantsService()

    # 영국 필터
    uk_list = service.get_all_programs(country="영국")
    assert len(uk_list) >= 2
    for p in uk_list:
        assert p["country"] == "영국"

    # AI 분야 필터
    ai_list = service.get_all_programs(field="AI")
    assert len(ai_list) >= 3
    for p in ai_list:
        assert any("AI" in f for f in p["specialized_fields"])

    # 비자 혜택 필수 필터
    visa_list = service.get_all_programs(visa_required=True)
    assert len(visa_list) >= 5
    for p in visa_list:
        assert "비자" in p["visa_benefit"] or "영주권" in p["visa_benefit"]


def test_portals_view_renders_global_tab(client):
    """GET /portals 웹 화면에 탭 4(해외 거점 정부 및 글로벌 특화 유치 포털)가 렌더링되는지 검증."""
    resp = client.get("/portals")
    assert resp.status_code == 200
    html = resp.text

    # 탭 4 텍스트 및 거점 정보 확인
    assert "해외 거점 정부" in html or "글로벌 유치 포털" in html
    assert "UK-DBT-GEP-2026" in html
    assert "Cité" in html or "Station F" in html
    assert "Hub71" in html
    assert "Spacecubed" in html
    assert "750,000 AED" in html


def test_api_portals_status_includes_global_portals(client):
    """GET /api/portals/status에 글로벌 5대 포털 메타데이터가 포함되는지 검증."""
    resp = client.get("/api/portals/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"

    portals_map = {p["portal_id"]: p for p in data["portals"]}
    assert "uk_dbt_gep" in portals_map
    assert "fr_cite_stationf" in portals_map
    assert "au_austrade_landing" in portals_map
    assert "uae_hub71_adgm" in portals_map
    assert "kr_ksc_global" in portals_map

    uk = portals_map["uk_dbt_gep"]
    assert uk["is_global"] is True
    assert uk["country"] == "영국"
    assert "TypeG" in uk["adapter_type"]


def test_api_global_grants_endpoints(client):
    """GET /api/portals/global-grants 및 /summary 엔드포인트 응답 검증."""
    # 1. 전체 목록
    resp1 = client.get("/api/portals/global-grants")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["status"] == "success"
    assert data1["count"] >= 8

    # 2. 필터링 (UAE)
    resp2 = client.get("/api/portals/global-grants", params={"country": "UAE"})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["count"] >= 1
    assert data2["programs"][0]["country"] == "UAE"

    # 3. 요약 (Summary)
    resp3 = client.get("/api/portals/global-grants/summary")
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["status"] == "success"
    summary = data3["summary"]
    assert "영국" in summary
    assert "프랑스" in summary
    assert "호주" in summary
    assert "UAE" in summary

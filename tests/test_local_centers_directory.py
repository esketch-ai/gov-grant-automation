"""
tests/test_local_centers_directory.py
전국 지자체별 과제지원 및 사무실(입주) 지원 센터 총람 서비스 및 API 테스트.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.web.app import app
from src.common.local_centers_directory import LocalCentersService, LOCAL_CENTERS_CATALOG


@pytest.fixture
def client():
    return TestClient(app)


def test_local_centers_catalog_coverage():
    """송파구 사회적경제지원센터 등 전국 핵심 지자체 센터 커버리지 검증."""
    service = LocalCentersService()
    centers = service.get_centers()
    assert len(centers) >= 20

    # 송파구 사회적경제지원센터 필수 포함 검증
    songpa = next((c for c in centers if "송파구 사회적경제" in c["name"]), None)
    assert songpa is not None
    assert songpa["region"] == "서울"
    assert songpa["sub_region"] == "송파구"
    assert songpa["supports_office"] is True
    assert songpa["supports_grants"] is True
    assert "https://www.songpase.org" in songpa["website_url"]

    # 강남구, 성남 판교, 인천 송도 필수 포함 검증
    names = [c["name"] for c in centers]
    assert any("강남" in n for n in names)
    assert any("판교" in n or "성남" in n for n in names)
    assert any("인천 스타트업파크" in n for n in names)


def test_local_centers_filtering_logic():
    """지역, 카테고리, 사무실/과제 조건별 필터링 기능 검증."""
    service = LocalCentersService()

    # 1. 서울 지역 필터
    seoul_centers = service.get_centers(region="서울")
    assert len(seoul_centers) >= 5
    assert all(c["region"] == "서울" for c in seoul_centers)

    # 2. 사회적경제 카테고리 필터
    se_centers = service.get_centers(category="사회적경제")
    assert len(se_centers) >= 3
    assert all("사회적경제" in c["category"] for c in se_centers)

    # 3. 사무실 지원 기업만 필터
    office_centers = service.get_centers(office_only=True)
    assert all(c["supports_office"] is True for c in office_centers)

    # 4. 키워드 검색 ("판교")
    pangyo_centers = service.get_centers(keyword="판교")
    assert len(pangyo_centers) >= 1
    assert any("판교" in c["office_details"] or "판교" in c["name"] for c in pangyo_centers)

    # 5. MICE·판로지원 카테고리 필터 (COEX, KINTEX, BEXCO 등)
    mice_centers = service.get_centers(category="MICE·판로지원")
    assert len(mice_centers) >= 9
    mice_names = [c["name"] for c in mice_centers]
    assert any("코엑스" in n for n in mice_names)
    assert any("킨텍스" in n for n in mice_names)
    assert any("벡스코" in n for n in mice_names)
    assert any("김대중" in n for n in mice_names)


def test_municipal_and_social_economy_centers():
    """지초지자체 청년창업 및 사회적경제 전담센터 검증."""
    service = LocalCentersService()
    centers = service.get_centers()
    names = [c["name"] for c in centers]

    # 기초 지자체 청년센터 검증 (마포, 강북, 남동구, 해운대)
    assert any("마포청년" in n for n in names)
    assert any("강북청년" in n for n in names)
    assert any("남동구" in n for n in names)
    assert any("해운대" in n for n in names)

    # 사회적경제 센터 검증 (사람과세상, 광주, 대구, 부산, 전남, 파주)
    assert any("사람과세상" in n for n in names)
    assert any("부산광역시 사회적경제" in n for n in names)
    assert any("광주광역시 사회적경제" in n for n in names)
    assert any("전라남도 사회적경제" in n for n in names)


def test_local_centers_api_endpoint(client):
    """GET /api/portals/local-centers API 엔드포인트 응답 스키마 검증."""
    resp = client.get("/api/portals/local-centers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["count"] >= 20
    assert "regions_summary" in data
    assert data["regions_summary"].get("서울", 0) >= 5

    # 조건부 쿼리스트링 검색
    resp_filtered = client.get("/api/portals/local-centers?region=경기&category=산업진흥원")
    assert resp_filtered.status_code == 200
    d_filtered = resp_filtered.json()
    assert d_filtered["status"] == "success"
    assert all(c["region"] == "경기" for c in d_filtered["centers"])


def test_portals_view_renders_local_centers_tab(client):
    """GET /portals 웹 뷰에 탭 3(지자체별 사무실·과제 지원센터)이 렌더링되는지 검증."""
    resp = client.get("/portals")
    assert resp.status_code == 200
    html = resp.text
    assert "지자체별 사무실·과제 지원센터" in html
    assert "송파구 사회적경제지원센터" in html
    assert "판교 스타트업캠퍼스" in html
    assert "인천 스타트업파크" in html
    assert "localCentersGrid" in html

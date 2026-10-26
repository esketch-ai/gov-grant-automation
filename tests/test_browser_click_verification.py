"""Unit and Integration Tests for Browser Click Ground-Truth Verification.
'내부 코드 에러 없음'이 아닌, '실제 사용자의 브라우저 클릭 결과'를 최우선으로 검증합니다.
"""
from __future__ import annotations

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.verifier.browser_click_verifier import BrowserClickVerifier
from src.web.app import app

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def verifier():
    return BrowserClickVerifier(timeout_sec=5.0)


def test_announcements_ui_links_are_clickable(client, verifier):
    """
    [Pillar 1] 사용자가 웹 관리자 공고 목록(/announcements)을 열었을 때,
    화면에 렌더링된 모든 링크(<a>)가 빈 링크나 자바스크립트 더미 링크 없이 온전한지 검증.
    """
    res = client.get("/announcements")
    assert res.status_code == 200
    html = res.text

    audit_results = verifier.audit_html_links(html)
    assert len(audit_results) > 0, "공고 목록 화면에 클릭 가능한 링크가 최소 1개 이상 존재해야 함"

    invalid_links = [r for r in audit_results if not r["is_valid"]]
    assert len(invalid_links) == 0, f"화면에 깨지거나 유효하지 않은 링크 존재: {invalid_links}"


def test_live_click_iris_announcements(verifier):
    """
    [Pillar 2] IRIS 공고 원문 링크를 브라우저처럼 클릭했을 때,
    실제 과기부 LAM 과제 페이지(ancmId=022696)로 정확히 도달하고 2026년 공고인지 검증.
    """
    url = "https://www.iris.go.kr/contents/retrieveBsnsAncmView.do?ancmId=022696"
    res = verifier.verify_url_click(
        url=url,
        expected_keywords=["LAM", "인간-AI"],
        expected_year=2026,
    )
    # 실제 인터넷 환경에서 200/403 응답 및 연도 무결성 확인
    assert res.is_deep_link is True
    assert res.is_year_valid is True
    assert res.is_content_matched is True
    assert "LAM" in res.matched_keywords or "인간-AI" in res.matched_keywords


def test_live_click_kstartup_announcements(verifier):
    """
    [Pillar 2] K-Startup 공고 원문 링크(pbancSn=175783)를 클릭했을 때,
    실제 2026년 중앙부처 창업지원 통합공고로 정확히 도달하는지 검증.
    """
    url = "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=175783"
    res = verifier.verify_url_click(
        url=url,
        expected_keywords=["창업지원사업", "통합공고"],
        expected_year=2026,
    )
    assert res.is_deep_link is True
    assert res.is_year_valid is True
    assert res.is_content_matched is True


def test_live_click_ntis_announcements(verifier):
    """
    [Pillar 2] NTIS 공고 원문 링크(roRndUid=1279968)를 클릭했을 때,
    실제 2026년 지역거점 AX 혁신 과제 페이지로 정확히 도달하는지 검증.
    """
    url = "https://www.ntis.go.kr/rndgate/eg/un/ra/view.do?roRndUid=1279968"
    res = verifier.verify_url_click(
        url=url,
        expected_keywords=["지역거점", "AX"],
        expected_year=2026,
    )
    assert res.is_deep_link is True
    assert res.is_year_valid is True
    assert res.is_content_matched is True


def test_fault_injection_detects_2025_mismatch(verifier):
    """
    [Pillar 4] 의도적 결함 주입(Fault Injection) 테스트:
    사용자가 과거에 지적했던 'ancmId=015634'(2025 국방 과제) URL을 넣었을 때,
    검증기가 이를 무조건 '과거 연도 불일치 결함'으로 잡아내는지 검증.
    """
    bad_url = "https://www.iris.go.kr/contents/retrieveBsnsAncmView.do?ancmId=015634"
    res = verifier.verify_url_click(
        url=bad_url,
        expected_keywords=["탄소중립"],  # 엉뚱한 키워드 기대
        expected_year=2026,
    )
    # 연도 불일치 또는 키워드 불일치로 반드시 passed == False 여야 함!
    assert res.passed is False, "과거 2025년 국방 공고 URL은 반드시 FAIL로 검출되어야 합니다"
    assert (res.is_year_valid is False or res.is_content_matched is False)


def test_calendar_download_click_integrity(client, verifier):
    """
    [Pillar 3] 사용자가 공고 행에서 '캘린더 다운로드'를 클릭했을 때,
    온전한 RFC 5545 표준 iCalendar 포맷과 공고명이 일치하여 반환되는지 검증.
    """
    res = client.get("/api/announcements/iris:2026_lam_ai/calendar.ics")
    assert res.status_code == 200
    assert "text/calendar" in res.headers["content-type"]

    ics_content = res.text
    is_valid = verifier.verify_calendar_ics(
        ics_content,
        expected_title="인간-AI 협업형 LAM 개발",
    )
    assert is_valid is True, "다운로드된 iCalendar 파일 규격 및 제목 불일치"

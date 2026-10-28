"""
tests/test_visitor_portal.py
초기 방문자 포털(/intro, /pricing, 5막 스토리, 5대 파트너, 블러 페이월, 요금제) 전용 단위 및 통합 테스트 스위트.
"""
from __future__ import annotations

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.web.app import app
from src.web.design_system import (
    ROLE_PORTALS,
    STORY_5ACTS,
    GROWTH_ROADMAP_3STEPS,
    PARTNER_5ECOSYSTEM,
    PRICING_4TIERS,
)


@pytest.fixture
def client():
    return TestClient(app, follow_redirects=True)


class TestVisitorPortalStructure:
    """초기 방문자 포털 구조 및 정보 아키텍처(IA) 검증."""

    def test_visitor_intro_renders_200_and_role_context(self, client):
        """GET /intro가 200 OK와 함께 visitor 권한 컨텍스트를 정상 렌더링하는지 검증."""
        res = client.get("/intro")
        assert res.status_code == 200
        html = res.text

        # 1. 역할 컨텍스트 및 GNB
        assert 'data-role="visitor"' in html
        assert "초기 방문자 포털" in html

        # 2. GNB 4개 메뉴 항목 확인
        assert "서비스 소개" in html
        assert "성장 스토리" in html
        assert "전문 파트너" in html
        assert "요금제 안내" in html

        # 3. 우측 컨트롤 박스 및 CTA
        assert "1분 과제 진단" in html
        assert "/vault?role=subscriber" in html

    def test_visitor_intro_hero_and_multimedia(self, client):
        """히어로 섹션, 60초 공감 쇼릴 비디오 및 포스터 이미지 렌더링 검증."""
        res = client.get("/intro")
        assert res.status_code == 200
        html = res.text

        # 비디오 및 포스터
        assert "/static/media/intro/intro_showreel.mp4" in html
        assert "/static/media/intro/hero_fatigue_vs_winning_edge.jpg" in html

        # 핵심 가치 제안 문구
        assert "과제사업을 일일이 찾아다니고" in html
        assert "1분 무료 과제 매칭 시작하기" in html
        assert "사업자 워크스페이스 둘러보기" in html

    def test_visitor_5acts_storyboard(self, client):
        """5막 공감 스토리보드 카드 5종 및 시각 자산 정합성 검증."""
        res = client.get("/intro")
        assert res.status_code == 200
        html = res.text

        for act in STORY_5ACTS:
            assert act["act_no"] in html
            assert act["badge"] in html
            assert act["title"] in html
            assert act["img"] in html

    def test_visitor_growth_roadmap_and_5partners(self, client):
        """성장 3단계 로드맵 및 5대 전문 파트너 생태계 렌더링 검증."""
        res = client.get("/intro")
        assert res.status_code == 200
        html = res.text

        # 성장 3단계
        for step in GROWTH_ROADMAP_3STEPS:
            assert step["step"] in html
            assert step["grant_scale"] in html

        # 5대 파트너 네트워크
        for p in PARTNER_5ECOSYSTEM:
            assert p["name"] in html
            assert p["desc"] in html

    def test_visitor_sample_preview_and_blurred_paywall(self, client):
        """작성 가이드 샘플 및 블러 페이월(Blurred Paywall) 유료 잠금 보호 검증."""
        res = client.get("/intro")
        assert res.status_code == 200
        html = res.text

        # 샘플 뷰
        assert "작성 가이드 샘플" in html
        assert "문제인식" in html
        assert "기술개발" in html

        # 블러 페이월 잠금
        assert "blur-sm" in html
        assert "select-none" in html
        assert "성장형 플랜으로 시작하기" in html

    def test_visitor_pricing_tiers_and_annual_discount(self, client):
        """4-Tier 요금제 및 연간 20% 할인 토글 스펙 검증."""
        res = client.get("/intro")
        assert res.status_code == 200
        html = res.text

        # 4대 요금제
        for plan in PRICING_4TIERS:
            assert plan["name"] in html
            assert plan["price_id"] in html

        # 연간 할인 토글
        assert "annual-toggle" in html
        assert "20% 특별 할인" in html

    def test_pricing_route_activates_pricing_tab(self, client):
        """GET /pricing 경로 접근 시 200 OK와 active_page=pricing 렌더링 검증."""
        res = client.get("/pricing")
        assert res.status_code == 200
        html = res.text

        # pricing 탭이 기본 활성화 상태인지 확인
        assert 'data-tab="pricing-plan"' in html
        assert "월간 / 연간 요금 안내" in html


class TestVisitorMediaAssetsIntegrity:
    """초기 방문자 포털에 사용되는 정적 미디어 파일의 디스크 실존 여부 및 무결성 검증."""

    def test_intro_media_files_exist_on_disk(self):
        base_dir = Path(__file__).resolve().parent.parent
        media_dir = base_dir / "src" / "web" / "static" / "media" / "intro"

        required_files = [
            "intro_showreel.mp4",
            "hero_fatigue_vs_winning_edge.jpg",
            "story_act1_exhaustion.jpg",
            "story_act2_morning_alert.jpg",
            "story_act3_warm_guide.jpg",
            "story_act4_winning_joy.jpg",
            "story_act5_growth_network_fortune.jpg",
        ]

        for fname in required_files:
            target_path = media_dir / fname
            assert target_path.exists(), f"미디어 파일 부재: {fname}"
            assert target_path.stat().st_size > 0, f"빈 미디어 파일: {fname}"


class TestVisitorSubmenuAndScrollSync:
    """REQ-040: 방문자 포털 서브 메뉴 및 3대 탭 동작 무결성(84px 스크롤 오프셋, ScrollSpy, 탭 상태 동기화) 검증."""

    def test_css_scroll_offset_and_target_utility(self):
        """CSS 스타일시트에 scroll-padding-top: 84px 및 .kh-scroll-target 정의 검증."""
        base_dir = Path(__file__).resolve().parent.parent
        css_path = base_dir / "src" / "web" / "static" / "css" / "k_horizon_2027.css"
        assert css_path.exists(), "k_horizon_2027.css 파일 부재"
        css_content = css_path.read_text(encoding="utf-8")

        assert "scroll-padding-top: 84px" in css_content, "html scroll-padding-top: 84px 정의 누락"
        assert ".kh-scroll-target" in css_content, ".kh-scroll-target 클래스 정의 누락"
        assert "scroll-margin-top: 84px" in css_content, "scroll-margin-top: 84px 정의 누락"

    def test_visitor_gnb_nav_items_and_target_hashes(self, client):
        """방문자 GNB 4대 서브 링크 및 타깃 앵커 해시 정합성 검증."""
        res = client.get("/intro")
        assert res.status_code == 200
        html = res.text

        # GNB 링크 타깃
        assert 'href="/intro"' in html
        assert 'href="/intro#story-5acts"' in html
        assert 'href="/intro#growth-partners"' in html
        assert 'href="/pricing"' in html

        # data-nav-page 속성
        assert 'data-nav-page="intro"' in html
        assert 'data-nav-page="story"' in html
        assert 'data-nav-page="partners"' in html
        assert 'data-nav-page="pricing"' in html

    def test_sections_have_kh_scroll_target_class(self, client):
        """4대 주요 섹션에 헤더 가림 방지 .kh-scroll-target 클래스 렌더링 검증."""
        res = client.get("/intro")
        assert res.status_code == 200
        html = res.text

        assert 'id="hero-intro"' in html and "kh-scroll-target" in html
        assert 'id="story-5acts" class="kh-scroll-target"' in html
        assert 'id="growth-partners" class="kh-scroll-target"' in html
        assert 'id="section-pricing-plan" class="kh-scroll-target"' in html

    def test_three_subtabs_and_hash_sync_markup(self, client):
        """3대 서브 탭(샘플/잠금/요금) 식별자 및 양방향 해시 동기화 마크업/스크립트 검증."""
        res = client.get("/intro")
        assert res.status_code == 200
        html = res.text

        # 3대 탭 버튼
        assert 'data-tab="sample-overview"' in html
        assert 'data-tab="paywall-preview"' in html
        assert 'data-tab="pricing-plan"' in html

        # 3대 탭 컨텐츠
        assert 'id="tab-sample-overview"' in html
        assert 'id="tab-paywall-preview"' in html
        assert 'id="tab-pricing-plan"' in html

        # JavaScript 핵심 함수 탑재
        assert "function switchTab(targetTab" in html
        assert "function activateGnbItem(pageKey)" in html
        assert "function handleHashAndPricing()" in html
        assert "IntersectionObserver" in html

    def test_mobile_nav_auto_close_onclick(self, client):
        """모바일 드롭다운 메뉴 링크 클릭 시 toggleMobileNav() 자동 닫힘 핸들러 탑재 검증."""
        res = client.get("/intro")
        assert res.status_code == 200
        html = res.text

        # 모바일 드롭다운 내부 링크에 toggleMobileNav 호출 탑재
        assert 'id="mobileNavMenu"' in html
        assert 'onclick="toggleMobileNav()"' in html


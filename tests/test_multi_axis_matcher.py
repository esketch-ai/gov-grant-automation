"""Unit Tests for Multi-Axis Matcher.
사용자가 제기한 '심리상담 플랫폼이 청년/여성/지역경제/사회서비스 공고에 매칭되어야 하는 현실'을 완벽하게 검증합니다.
"""
from __future__ import annotations

import pytest

from src.common.schemas import RawNotice
from src.matcher.multi_axis_matcher import (
    ApplicantProfile,
    MultiAxisMatcher,
    NoticeTrack,
)


@pytest.fixture
def matcher():
    return MultiAxisMatcher()


@pytest.fixture
def psychology_startup_profile():
    """사용자가 예시로 든 실제 사업주 프로필: 심리상담 플랫폼 (부산 소재, 32세 여성 청년, 업력 2년차)"""
    return ApplicantProfile(
        company_name="마인드케어 플랫폼",
        biz_age_years=2.0,
        founder_age=32,
        is_female_founder=True,
        location="부산",
        is_social_venture=True,
        tags=["심리상담", "비대면플랫폼", "멘탈헬스케어"],
    )


def test_psychological_platform_matches_general_startup_package(matcher, psychology_startup_profile):
    """
    [시나리오 1: 일반 창업패키지]
    공고문에 '심리상담'이라는 기술명이 전혀 없어도,
    초기창업패키지(일반분야)는 업력 2년 + 청년 자격만으로 95점 고득점 매칭 통과해야 함.
    """
    notice = RawNotice(
        portal_id="k_startup",
        title="2026년도 초기창업패키지(일반분야) 창업기업 모집공고",
        organization="창업진흥원",
        ministry="중소벤처기업부",
        deadline="2026-11-20 18:00",
        detail_url="https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=176019",
        body_text="유망 창업아이템을 보유한 초기창업기업(3년 이내)의 사업안정화와 성장을 지원하기 위한 일반분야 모집",
    )

    result = matcher.evaluate(psychology_startup_profile, notice)

    assert result.is_eligible is True
    assert result.match_score >= 90
    assert result.matched_track == NoticeTrack.GENERAL_STARTUP
    assert any("초기창업(3년 이내)" in r for r in result.pass_reasons)
    assert any("아이템 제한 없이" in r for r in result.pass_reasons)


def test_psychological_platform_matches_female_entrepreneur_track(matcher, psychology_startup_profile):
    """
    [시나리오 2: 신분/여성기업 특화]
    여성 창업지원 공고에 여성 대표자 자격 및 가점으로 95점 이상 매칭 통과해야 함.
    """
    notice = RawNotice(
        portal_id="k_startup",
        title="2026년 여성기업 특화 창업지원사업 공고",
        organization="여성기업종합지원센터",
        ministry="중소벤처기업부",
        deadline="2026-11-30 18:00",
        detail_url="https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=177000",
        body_text="여성 대표자가 운영하는 7년 이내 창업기업의 사업화 자금 및 마케팅 지원",
    )

    result = matcher.evaluate(psychology_startup_profile, notice)

    assert result.is_eligible is True
    assert result.match_score >= 95
    assert result.matched_track == NoticeTrack.DEMOGRAPHIC_FOCUSED
    assert any("여성 대표자" in r for r in result.pass_reasons)
    assert any("여성기업 특화 가점" in b for b in result.bonus_points)


def test_psychological_platform_matches_local_busan_track(matcher, psychology_startup_profile):
    """
    [시나리오 3: 지역경제 / 로컬 특화]
    부산 소재 로컬크리에이터 및 지역특화 지원사업에 부산 지역 가점으로 매칭 통과해야 함.
    """
    notice = RawNotice(
        portal_id="k_startup",
        title="2026년 부산 로컬크리에이터 활성화 및 지역 비즈니스 육성사업",
        organization="부산창조경제혁신센터",
        ministry="중소벤처기업부",
        deadline="2026-11-25 18:00",
        detail_url="https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=178000",
        body_text="부산 지역 자원과 연계하여 지역경제 활성화에 기여하는 7년 이내 청년 로컬 기업 지원",
    )

    result = matcher.evaluate(psychology_startup_profile, notice)

    assert result.is_eligible is True
    assert result.match_score >= 90
    assert result.matched_track == NoticeTrack.REGIONAL_LOCAL
    assert any("부산" in r for r in result.pass_reasons)
    assert any("부산 지역 특화 가점" in b for b in result.bonus_points)


def test_psychological_platform_matches_social_service_mental_health(matcher, psychology_startup_profile):
    """
    [시나리오 4: 사회서비스 / 마음건강 온톨로지 확장 매칭]
    '심리상담'이라는 단어가 없어도 온톨로지 확장으로 '마음건강/사회서비스' 공고에 자동 매칭되어야 함.
    """
    notice = RawNotice(
        portal_id="iris",
        title="2026년 국민체감형 사회서비스 R&D (고립은둔 청년 마음건강 케어)",
        organization="한국보건산업진흥원",
        ministry="보건복지부",
        deadline="2026-12-10 18:00",
        detail_url="https://www.iris.go.kr/contents/retrieveBsnsAncmView.do?ancmId=029999",
        body_text="취약계층 및 고립은둔 청년의 마음건강 증진과 정신건강 회복을 위한 디지털 사회서비스 모델 실증",
    )

    result = matcher.evaluate(psychology_startup_profile, notice)

    assert result.is_eligible is True
    assert result.match_score >= 90
    assert result.matched_track == NoticeTrack.SOCIAL_POLICY
    assert any("마음건강" in r or "사회서비스" in r for r in result.pass_reasons)


def test_disqualified_when_biz_age_exceeds_requirement(matcher):
    """
    [시나리오 5: 결격 사유 정확한 판정]
    업력 5년 차 기업이 '초기창업(3년 이내)' 공고에 신청할 경우, 점수 0점 및 탈락 사유가 명시되어야 함.
    """
    senior_profile = ApplicantProfile(
        company_name="5년차 멘탈헬스 기업",
        biz_age_years=5.0,
        founder_age=35,
        is_female_founder=False,
        location="서울",
        tags=["심리상담"],
    )

    notice = RawNotice(
        portal_id="k_startup",
        title="2026년도 초기창업패키지(일반분야) 창업기업 모집공고",
        organization="창업진흥원",
        ministry="중소벤처기업부",
        deadline="2026-11-20 18:00",
        detail_url="https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=176019",
        body_text="3년 이내 초기창업기업 지원",
    )

    result = matcher.evaluate(senior_profile, notice)

    assert result.is_eligible is False
    assert result.match_score == 0
    assert any("초기창업(3년 이내) 요건 초과" in d for d in result.disqualification_reasons)

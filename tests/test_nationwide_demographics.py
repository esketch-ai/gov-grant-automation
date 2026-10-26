"""Unit Tests for Nationwide 17 Regions and Applicant Demographics Profiler.
전국구 지자체 포털 커버리지와 사업주 상태(여성, 청년, 업력, 지역)의 기계식 자동 판정을 검증합니다.
"""
from __future__ import annotations

from datetime import date
import pytest

from src.common.nationwide_regions import NATIONWIDE_REGIONS, detect_region_from_text
from src.matcher.applicant_profiler import ApplicantProfiler, BizStage
from src.matcher.notice_demographics_extractor import NoticeDemographicsExtractor


def test_nationwide_17_regions_coverage():
    """대한민국 17개 광역시·도가 빠짐없이 정의되어 있고 TP와 도메인이 매핑되어 있는지 검증."""
    assert len(NATIONWIDE_REGIONS) == 17
    expected_codes = {"11", "26", "27", "28", "29", "30", "31", "36", "41", "42", "43", "44", "45", "46", "47", "48", "50"}
    assert set(NATIONWIDE_REGIONS.keys()) == expected_codes

    # 부산 확인
    busan = NATIONWIDE_REGIONS["26"]
    assert busan.name == "부산"
    assert busan.tp_name == "부산테크노파크"
    assert "busan.go.kr" in busan.portal_domain


def test_applicant_profiler_calculates_age_youth_and_female():
    """
    [사업주 상태 자동 판정]
    2024년 4월 15일 개업, 1994년 6월 20일생 여성 대표, 부산 소재 주소 입력 시:
    - 업력 약 2.5년 (초기창업기업)
    - 만 32세 (청년창업 만 39세 이하 충족)
    - 여성기업 True
    - 부산 지역 감지 True
    가 1초 만에 자동 계산되는지 검증.
    """
    ref_date = date(2026, 10, 26)
    profiler = ApplicantProfiler(reference_date=ref_date)

    profile = profiler.profile_from_data(
        company_name="마인드케어 플랫폼",
        biz_reg_no="602-81-12345",
        opened_at_str="2024-04-15",
        founder_birth_str="1994-06-20",
        founder_gender="F",
        address="부산광역시 해운대구 센텀중앙로 78",
    )

    assert profile.biz_age_years == 2.5
    assert profile.biz_stage == BizStage.EARLY_STAGE
    assert profile.founder_age == 32
    assert profile.is_youth_39 is True
    assert profile.is_youth_34 is True
    assert profile.is_female_founder is True
    assert profile.region is not None
    assert profile.region.name == "부산"
    assert profile.biz_reg_no == "602-81-12345"


def test_applicant_profiler_mature_company():
    """2015년 개업 50대 남성 대표인 경우, 중소기업 단계 및 청년/여성 False 판정 검증."""
    ref_date = date(2026, 10, 26)
    profiler = ApplicantProfiler(reference_date=ref_date)

    profile = profiler.profile_from_data(
        company_name="삼진정밀",
        biz_reg_no="1234567890",
        opened_at_str="20150310",
        founder_birth_str="19720515",
        founder_gender="M",
        address="경상남도 창원시 성산구 공단로",
    )

    assert profile.biz_age_years >= 11.0
    assert profile.biz_stage == BizStage.SCALEUP_MATURE
    assert profile.is_youth_39 is False
    assert profile.is_female_founder is False
    assert profile.region is not None
    assert profile.region.name == "경남"


def test_notice_demographics_extractor_local_and_bonus():
    """
    [공고문 자격·가점 기계식 추출]
    부산 로컬크리에이터 공고문에서 지역(부산), 청년가점, 여성우대 등이 정확히 추출되는지 검증.
    """
    extractor = NoticeDemographicsExtractor()
    title = "2026년 부산 로컬크리에이터 활성화 지원사업 공고"
    body = "부산 관내 본사를 둔 만 39세 이하 청년 창업기업을 대상으로 하며, 여성기업 및 벤처기업은 가점을 부여합니다."

    criteria = extractor.extract(title, body)

    assert "부산" in criteria.target_regions
    assert criteria.is_youth_priority is True
    assert criteria.is_female_priority is True
    assert any("관내(부산)" in b for b in criteria.bonus_items)
    assert any("여성기업" in b for b in criteria.bonus_items)
    assert any("벤처기업" in b for b in criteria.bonus_items)


def test_notice_demographics_extractor_general_track_and_biz_age():
    """
    초기창업패키지 공고문에서 '일반분야(전업종)' 및 '업력 3년 이내' 요건이 정확히 추출되는지 검증.
    """
    extractor = NoticeDemographicsExtractor()
    title = "2026년도 초기창업패키지(일반분야) 창업기업 모집공고"
    body = "업종 무관 전 분야 유망 아이템을 보유한 3년 이내 초기창업기업 지원"

    criteria = extractor.extract(title, body)

    assert criteria.is_general_track is True
    assert criteria.min_biz_age_years == 0.0
    assert criteria.max_biz_age_years == 3.0

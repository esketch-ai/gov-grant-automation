"""
안드레이 카파시 4원칙 준수 - 하드코딩 제거 및 무결성 검증 테스트
(tests/test_karpathy_hardcoding_cleanup.py)

1. Think Before Coding: 성별, 주소, 이메일 등의 임의 가정/하드코딩 배제 검증
2. Simplicity First: constants.py 단일 진실 공급원(SSOT) 구조 검증
3. Surgical Changes: 기존 시스템 동작과의 100% 호환성 유지 검증
4. Goal-Driven Execution: 테스트 선행 기반 검증
"""
import pytest
from datetime import date
from src.common.constants import (
    YOUTH_AGE_LIMIT_GENERAL,
    YOUTH_AGE_LIMIT_SPECIAL,
    BIZ_AGE_EARLY_STAGE_YEARS,
    BIZ_AGE_GROWTH_STAGE_YEARS,
    DEFAULT_MIN_MATCH_SCORE,
)
from src.matcher.multi_axis_matcher import ApplicantProfile
from src.matcher.applicant_profiler import ApplicantProfiler


def test_constants_definitions():
    """도메인 핵심 상수가 올바른 값과 타입으로 정의되어 있는지 확인."""
    assert YOUTH_AGE_LIMIT_GENERAL == 39
    assert YOUTH_AGE_LIMIT_SPECIAL == 34
    assert BIZ_AGE_EARLY_STAGE_YEARS == 3.0
    assert BIZ_AGE_GROWTH_STAGE_YEARS == 7.0
    assert DEFAULT_MIN_MATCH_SCORE == 75


def test_applicant_profile_location_default_is_empty():
    """ApplicantProfile의 location 기본값이 '서울'이 아닌 빈 문자열('')인지 검증."""
    prof = ApplicantProfile(
        company_name="테스트기업",
        biz_age_years=1.0,
        founder_age=30,
    )
    assert prof.location == "", "기본 소재지는 '서울'로 하드코딩되지 않고 빈 문자열('')이어야 합니다."


def test_applicant_profiler_gender_none_is_strictly_not_female():
    """성별이 'NONE'(미지정/비공개) 또는 ''인 경우 어떠한 경우에도 여성기업 판정을 내리지 않음."""
    profiler = ApplicantProfiler()

    # 1. NONE 성별
    res_none = profiler.profile_from_data(
        company_name="A사",
        biz_reg_no="123-45-67890",
        founder_gender="NONE",
        certifications=["여성기업"],  # 잘못 섞여 들어왔더라도
    )
    assert res_none.is_female_founder is False

    # 2. 미기재('') 성별
    res_empty = profiler.profile_from_data(
        company_name="B사",
        biz_reg_no="123-45-67891",
        founder_gender="",
        certifications=["여성기업"],
    )
    assert res_empty.is_female_founder is False

    # 3. 명시적 F 성별인 경우만 True
    res_female = profiler.profile_from_data(
        company_name="C사",
        biz_reg_no="123-45-67892",
        founder_gender="F",
        certifications=["여성기업"],
    )
    assert res_female.is_female_founder is True


def test_youth_age_boundary_with_constants():
    """상수 기준(39세, 34세) 경계값 정확성 검증."""
    ref = date(2026, 6, 1)
    profiler = ApplicantProfiler(reference_date=ref)

    # 만 39세 (1986-06-02 -> 만 39세)
    res_39 = profiler.profile_from_data(
        company_name="청년기업",
        biz_reg_no="111-22-33333",
        founder_birth_str="1986-06-02",
    )
    assert res_39.is_youth_39 is True
    assert res_39.is_youth_34 is False

    # 만 40세 (1986-05-30 -> 만 40세)
    res_40 = profiler.profile_from_data(
        company_name="비청년기업",
        biz_reg_no="111-22-33334",
        founder_birth_str="1986-05-30",
    )
    assert res_40.is_youth_39 is False
    assert res_40.is_youth_34 is False


def test_g2b_portal_url_integrity():
    """조달청 나라장터(G2B) URL 정합성 및 비표준 포트(8081) 배제 검증."""
    from src.verifier.browser_click_verifier import BrowserClickVerifier
    from src.qaqc.agency_notice_pool import AGENCY_NOTICE_POOL

    verifier = BrowserClickVerifier()

    # 1. 벤치마크 풀 내 G2B 공고 URL에 8081 포트가 없어야 함
    g2b_benchmarks = [b for b in AGENCY_NOTICE_POOL if b["raw_notice"].portal_id == "g2b"]
    assert len(g2b_benchmarks) > 0
    for b in g2b_benchmarks:
        url = b["raw_notice"].detail_url
        assert ":8081" not in url, f"G2B URL에 비표준 8081 포트가 포함되어선 안 됩니다: {url}"
        assert verifier._check_deep_link(url) is True, f"차세대 나라장터 딥링크 규격을 만족해야 합니다: {url}"

    # 2. BrowserClickVerifier가 차세대 나라장터 해시 딥링크를 유효한 딥링크로 인식하는지 검증
    next_gen_url = "https://www.g2b.go.kr#PNPE027_01?bidPbancNo=20261009120&bidPbancOrd=00"
    assert verifier._check_deep_link(next_gen_url) is True
    assert verifier._check_deep_link("https://www.g2b.go.kr") is False  # 단순 메인은 딥링크 탈락


"""Unit Tests for Advanced Eligibility Validator (6 Domains, 25 Hidden Conditions).
정부과제 서류 심사에서 사업주들이 실제로 겪는 숨겨진 조건(부채비율, 연구소, 3책5공, 중복수혜, 자부담)을 검증합니다.
"""
from __future__ import annotations

import pytest

from src.matcher.advanced_eligibility_validator import (
    AdvancedEligibilityValidator,
    CompanyFinancialAndTechSpec,
    NoticeAdvancedRequirements,
    PreFlightStatus,
)


@pytest.fixture
def validator():
    return AdvancedEligibilityValidator()


def test_debt_ratio_800_exempted_for_early_startup(validator):
    """
    [TC-01: 창업 3년 미만 부채비율 특례]
    부채비율이 800%에 달하지만, 창업 2년 차 초기기업인 경우
    정부과제 3년 미만 예외 조항에 따라 결격(탈락)되지 않고 합격 처리되는지 검증.
    """
    spec = CompanyFinancialAndTechSpec(
        biz_age_years=2.0,
        debt_ratio_pct=800.0,
        has_tax_arrears=False,
    )
    req = NoticeAdvancedRequirements(
        notice_title="2026 초기창업패키지",
        max_debt_ratio_pct=500.0,
        exempt_3year_rule=True,
    )

    report = validator.validate(spec, req)

    assert report.is_eligible is True
    assert report.status in (PreFlightStatus.GREEN, PreFlightStatus.YELLOW)
    assert len(report.fatal_red_flags) == 0
    assert any("창업 3년 미만" in w for w in report.warnings)


def test_debt_ratio_800_disqualified_for_mature_company(validator):
    """
    [TC-02: 창업 3년 초과 부채비율 결격]
    업력 5년 차 기업이 부채비율 800%인 경우,
    부채비율 500% 초과 결격 사유로 즉시 RED(0점 탈락)되는지 검증.
    """
    spec = CompanyFinancialAndTechSpec(
        biz_age_years=5.0,
        debt_ratio_pct=800.0,
    )
    req = NoticeAdvancedRequirements(
        notice_title="2026 중기부 기술개발사업",
        max_debt_ratio_pct=500.0,
        exempt_3year_rule=True,
    )

    report = validator.validate(spec, req)

    assert report.is_eligible is False
    assert report.status == PreFlightStatus.RED
    assert report.final_score == 0
    assert any("부채비율 800%가 허용 기준(500%)을 초과" in r for r in report.fatal_red_flags)


def test_rnd_lab_mandatory_disqualification(validator):
    """
    [TC-03: 연구소 필수 요건 검증]
    과기부/산업부 R&D 공고에 기업부설연구소 또는 전담부서가 없는 기업이 신청할 경우
    서류 부적격으로 즉시 탈락(RED)되는지 검증.
    """
    spec = CompanyFinancialAndTechSpec(
        biz_age_years=3.5,
        has_rnd_lab=False,  # 연구소 미보유
    )
    req = NoticeAdvancedRequirements(
        notice_title="2026년 첨단 바이오 R&D 실증과제",
        requires_rnd_lab=True,  # 연구소 필수
    )

    report = validator.validate(spec, req)

    assert report.is_eligible is False
    assert report.status == PreFlightStatus.RED
    assert any("기업부설연구소 또는 전담부서 보유가 필수" in r for r in report.fatal_red_flags)


def test_double_dipping_restriction_on_packages(validator):
    """
    [TC-04: 중복수혜 제한 검증]
    과거 '초기창업패키지'를 이미 수혜받았던 기업이 다시 초기창업패키지에 신청할 경우
    중복수혜 제한 규정에 따라 탈락(RED)되는지 검증.
    """
    spec = CompanyFinancialAndTechSpec(
        biz_age_years=2.8,
        prior_grant_history=["2024년 초기창업패키지 선정 및 협약완료"],
    )
    req = NoticeAdvancedRequirements(
        notice_title="2026 초기창업패키지 창업기업 모집",
        restricted_prior_grants=["초기창업패키지", "청년창업사관학교"],
    )

    report = validator.validate(spec, req)

    assert report.is_eligible is False
    assert report.status == PreFlightStatus.RED
    assert any("중복수혜 제한" in r for r in report.fatal_red_flags)


def test_3projects_limit_violation(validator):
    """
    [TC-05: 국가연구개발혁신법 3책 5공 제한 검증]
    현재 연구책임자(PI) 과제를 이미 3개 수행 중인 대표자가 신규 과제의 책임자로 지원 시
    3책 제한 초과로 즉시 탈락(RED)되는지 검증.
    """
    spec = CompanyFinancialAndTechSpec(
        biz_age_years=4.0,
        current_pi_projects=3,  # 이미 3개 수행 중
    )
    req = NoticeAdvancedRequirements(
        notice_title="2026년 범부처 넷제로 혁신기술개발",
        max_pi_allowed=3,
    )

    report = validator.validate(spec, req)

    assert report.is_eligible is False
    assert report.status == PreFlightStatus.RED
    assert any("3책 제한 위반" in r for r in report.fatal_red_flags)


def test_multi_bonus_points_and_matching_cash(validator):
    """
    [TC-06: 복합 가점 및 자부담 능력 완비]
    벤처기업 + 이노비즈 + 여성기업 + 특허 2건 보유 및 자부담 현금이 충분한 우수 기업이
    최고 가점을 획득하고 95점 이상 GREEN 판정을 받는지 검증.
    """
    spec = CompanyFinancialAndTechSpec(
        biz_age_years=3.0,
        debt_ratio_pct=150.0,
        has_rnd_lab=True,
        certifications=["벤처기업", "이노비즈", "여성기업"],
        registered_patents_count=2,
        available_cash_fund=50_000_000,  # 5천만원 보유
    )
    req = NoticeAdvancedRequirements(
        notice_title="2026년 중소기업 기술혁신개발사업(수출지향형)",
        requires_rnd_lab=True,
        required_cash_matching=30_000_000,  # 자부담 3천만원 요구
    )

    report = validator.validate(spec, req)

    assert report.is_eligible is True
    assert report.status == PreFlightStatus.GREEN
    assert report.final_score >= 95
    assert len(report.bonus_points) >= 4
    assert any("벤처기업" in b for b in report.bonus_points)
    assert any("이노비즈" in b for b in report.bonus_points)
    assert any("여성기업" in b for b in report.bonus_points)
    assert any("등록 특허 2건" in b for b in report.bonus_points)

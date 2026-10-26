"""Advanced Eligibility Validator: 정부과제의 6대 영역 복합 자격·결격·가점 조건을 종합 검증하는 엔진.
단순 업력/나이를 넘어 부채비율, 자본잠식, 체납, 연구소 보유, 3책5공, 중복수혜, 자부담 현금 등
실제 정부과제 서류 심사에서 탈락하는 숨겨진 지뢰들을 사전에 완벽히 진단합니다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class PreFlightStatus(str, Enum):
    """비행 전 점검 신호등 상태"""
    GREEN = "GREEN (신청 적합 - 서류 통과 유력)"
    YELLOW = "YELLOW (주의 요망 - 보완 서류 필요)"
    RED = "RED (신청 불가 - 사전 탈락 사유 존재)"


@dataclass
class CompanyFinancialAndTechSpec:
    """기업의 정밀 재무, R&D 역량, 이력 종합 스펙"""
    biz_age_years: float                       # 업력 (년 단위)
    debt_ratio_pct: Optional[float] = None     # 부채비율 (%, 예: 350.0, 800.0)
    is_capital_impaired: bool = False          # 완전 자본잠식 여부
    has_tax_arrears: bool = False              # 국세/지방세 체납 여부
    has_rnd_lab: bool = False                  # 기업부설연구소 또는 전담부서 보유 여부
    current_pi_projects: int = 0               # 현재 수행 중인 연구책임자(PI) 과제 수 (최대 3개)
    current_member_projects: int = 0           # 현재 수행 중인 참여연구원 과제 수 (최대 5개)
    prior_grant_history: List[str] = field(default_factory=list) # 과거 수혜 정부지원사업 이력
    certifications: List[str] = field(default_factory=list)      # 벤처, 이노비즈, 여성기업 등
    registered_patents_count: int = 0          # 등록 특허 건수
    available_cash_fund: int = 0               # 통장 잔고/자부담 가용 현금 (원 단위)


@dataclass
class NoticeAdvancedRequirements:
    """공고문에 명시된 6대 영역 종합 자격 요건"""
    notice_title: str
    max_debt_ratio_pct: Optional[float] = 500.0   # 부채비율 상한 (보통 500%)
    exempt_3year_rule: bool = True               # 창업 3년 미만 기업 부채비율 예외 적용 여부
    allow_capital_impaired: bool = False         # 자본잠식 허용 여부 (일반적으로 불가)
    requires_rnd_lab: bool = False               # 기업부설연구소 필수 여부 (과기/산업부 R&D)
    max_pi_allowed: int = 3                      # 3책 허용 상한
    max_total_allowed: int = 5                   # 5공 허용 상한
    restricted_prior_grants: List[str] = field(default_factory=list) # 중복수혜 제한 과거 사업들
    required_cash_matching: int = 0              # 기업이 필수로 부담해야 하는 현금 자부담 (원)


@dataclass
class PreFlightValidationReport:
    """종합 사전 진단 결과 보고서"""
    status: PreFlightStatus
    is_eligible: bool
    final_score: int                            # 0 ~ 100
    fatal_red_flags: List[str] = field(default_factory=list) # 탈락 사유 (Red)
    warnings: List[str] = field(default_factory=list)        # 주의 사항 (Yellow)
    bonus_points: List[str] = field(default_factory=list)    # 획득 가점 (Bonus)


class AdvancedEligibilityValidator:
    """정부과제 종합 사전 비행점검 검증기"""

    def validate(
        self,
        spec: CompanyFinancialAndTechSpec,
        req: NoticeAdvancedRequirements,
    ) -> PreFlightValidationReport:
        red_flags: List[str] = []
        warnings: List[str] = []
        bonus_points: List[str] = []

        base_score = 80

        # [검증 1] 세금 체납 (절대 결격)
        if spec.has_tax_arrears:
            red_flags.append("국세 또는 지방세 체납 사실이 있어 정부지원사업 접수 자체가 불가합니다 (완납증명 필요).")

        # [검증 2] 자본잠식
        if spec.is_capital_impaired and not req.allow_capital_impaired:
            if spec.biz_age_years > 3.0:
                red_flags.append("최근 결산 기준 완전 자본잠식 상태로 지원 대상에서 제외됩니다.")
            else:
                warnings.append("자본잠식 상태이나 창업 3년 미만 기업으로 심사 시 예외 검토 대상입니다.")

        # [검증 3] 부채비율 (창업 3년 미만 예외 룰 적용)
        # [Blue Team 수정 2026-10-26] 경계값 포함 비교(>=)로 상한 초과를 차단하도록 엄격화 (500% 이상 탈락)
        if spec.debt_ratio_pct is not None and req.max_debt_ratio_pct is not None:
            if spec.debt_ratio_pct >= req.max_debt_ratio_pct:
                if req.exempt_3year_rule and spec.biz_age_years < 3.0:  # [Blue Team 수정] 창업 3년 미만 = strict under 3.0
                    warnings.append(
                        f"부채비율이 {spec.debt_ratio_pct:.0f}%로 상한({req.max_debt_ratio_pct:.0f}%)을 초과하지만, "
                        f"창업 3년 미만(업력 {spec.biz_age_years}년) 특례 조항에 따라 결격에서 제외됩니다."
                    )
                else:
                    red_flags.append(
                        f"부채비율 {spec.debt_ratio_pct:.0f}%가 허용 기준({req.max_debt_ratio_pct:.0f}%)을 초과하여 사전 탈락 대상입니다."
                    )

        # [검증 4] 연구개발 조직 (기업부설연구소/전담부서)
        if req.requires_rnd_lab:
            if not spec.has_rnd_lab:
                red_flags.append("본 과제는 한국산업기술진흥협회(KOITA) 인정 기업부설연구소 또는 전담부서 보유가 필수입니다.")
            else:
                bonus_points.append("기업부설연구소 보유 요건 충족 (+5점)")

        # [검증 5] 3책 5공 제한 검증
        if spec.current_pi_projects >= req.max_pi_allowed:
            red_flags.append(
                f"국가연구개발혁신법 3책 제한 위반: 현재 연구책임자(PI) 과제를 이미 {spec.current_pi_projects}개 수행 중입니다 (최대 3개)."
            )
        total_projects = spec.current_pi_projects + spec.current_member_projects
        if total_projects >= req.max_total_allowed:
            red_flags.append(
                f"국가연구개발혁신법 5공 제한 위반: 현재 총 {total_projects}개 과제를 동시 수행 중입니다 (최대 5개)."
            )

        # [검증 6] 중복수혜 제한 검증
        for past_grant in spec.prior_grant_history:
            if any(restricted in past_grant for restricted in req.restricted_prior_grants):
                red_flags.append(f"중복수혜 제한: 과거 '{past_grant}' 수혜 이력으로 동일 단계 과제 재신청이 불가합니다.")

        # [검증 7] 자부담 현금 준비도 검증
        if req.required_cash_matching > 0:
            if spec.available_cash_fund < req.required_cash_matching:
                warnings.append(
                    f"필수 현금 자부담(약 {req.required_cash_matching:,}원) 대비 가용 현금({spec.available_cash_fund:,}원)이 "
                    f"부족하여 협약 시 자금 증빙 대책이 필요합니다."
                )
            else:
                bonus_points.append("자부담 현금 매칭 능력 확보")

        # [검증 8] 정부 인증 및 가점 항목 합산
        if "벤처기업" in spec.certifications:
            bonus_points.append("벤처기업 인증 보유 (+2점)")
        if "이노비즈" in spec.certifications:
            bonus_points.append("이노비즈(기술혁신형 중소기업) 인증 보유 (+2점)")
        if "여성기업" in spec.certifications:
            bonus_points.append("여성기업 확인서 보유 (+2점)")
        if spec.registered_patents_count >= 1:
            bonus_points.append(f"과제 관련 등록 특허 {spec.registered_patents_count}건 보유 (+2점)")

        # 최종 신호등 판정 및 점수 계산
        if red_flags:
            status = PreFlightStatus.RED
            is_eligible = False
            final_score = 0
        elif warnings:
            status = PreFlightStatus.YELLOW
            is_eligible = True
            final_score = min(100, base_score + len(bonus_points) * 3 - len(warnings) * 5)
        else:
            status = PreFlightStatus.GREEN
            is_eligible = True
            final_score = min(100, base_score + len(bonus_points) * 4)

        return PreFlightValidationReport(
            status=status,
            is_eligible=is_eligible,
            final_score=max(0, final_score),
            fatal_red_flags=red_flags,
            warnings=warnings,
            bonus_points=bonus_points,
        )

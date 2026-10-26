"""
REQ-020 · 사전 비행점검 서비스 (PreflightService, 이승엽/박준호 담당)

사업주 프로필(사업자등록정보 + 재무/R&D 스펙)과 특정 공고를 입력받아
이미 검증된 2대 엔진 — `MultiAxisMatcher`(4대 다차원 트랙) +
`AdvancedEligibilityValidator`(25대 숨은 조건 신호등) — 를 1초 내 순서 실행해
신호등(GREEN/YELLOW/RED) 종합 판정을 산출합니다.

설계 원칙 (안전 degrade):
- 프로필 미설정/누락 시 '기본 빈 프로필'으로 폴백 → 크래시 없이 RED/YELLOW 진단.
- 모든 계산을 예외로 감싸 파이프라인을 막지 않는다.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from src.common.logging_config import get_logger
from src.common.schemas import RawNotice
from src.matcher.applicant_profiler import ApplicantProfiler, BizStage
from src.matcher.multi_axis_matcher import ApplicantProfile, MultiAxisMatcher, NoticeTrack
from src.matcher.advanced_eligibility_validator import (
    AdvancedEligibilityValidator,
    CompanyFinancialAndTechSpec,
    NoticeAdvancedRequirements,
    PreFlightStatus,
)

logger = get_logger("preflight")


# 사업주 프로필 기본 템플릿 (미설정 시 폴백)
DEFAULT_PROFILE: Dict[str, Any] = {
    "company_name": "",
    "biz_reg_no": "",
    "opened_date": "",
    "founder_birth": "",
    "founder_gender": "F",
    "address": "",
    "debt_ratio_pct": None,
    "has_rnd_lab": False,
    "is_capital_impaired": False,
    "has_tax_arrears": False,
    "current_pi_projects": 0,
    "current_member_projects": 0,
    "registered_patents_count": 0,
    "available_cash_fund": 0,
    "prior_grant_history": [],
    "certifications": [],
    "tags": [],
}

# 생애주기 -> 배너/라벨용 약어
_STAGE_SHORT = {
    BizStage.PRE_STARTUP: "예비창업",
    BizStage.EARLY_STAGE: "초기창업",
    BizStage.GROWTH_STAGE: "도약기업",
    BizStage.SCALEUP_MATURE: "성숙기업",
}


class PreflightService:
    """공고 × 사업주 프로필 -> 신호등 종합 진단 orchestrator."""

    def __init__(
        self,
        profiler: Optional[ApplicantProfiler] = None,
        matcher: Optional[MultiAxisMatcher] = None,
        validator: Optional[AdvancedEligibilityValidator] = None,
    ) -> None:
        self.profiler = profiler or ApplicantProfiler()
        self.matcher = matcher or MultiAxisMatcher()
        self.validator = validator or AdvancedEligibilityValidator()

    # ------------------------------------------------------------------ 입력 정규화
    @staticmethod
    def normalize_profile(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """입력 프로필을 DEFAULT 스키마로 정규화 (부재 필드는 기본값 보강)."""
        raw = raw or {}
        if not isinstance(raw, dict):
            raw = {}
        out = dict(DEFAULT_PROFILE)
        out.update({k: v for k, v in raw.items() if v is not None})
        # 리스트 타입 보강
        for key in ("prior_grant_history", "certifications", "tags", "keywords"):
            val = out.get(key)
            if isinstance(val, str):
                out[key] = [x.strip() for x in val.split(",") if x.strip()]
            elif val is None:
                out[key] = []
        if not out.get("tags") and out.get("keywords"):
            out["tags"] = list(out["keywords"])
        return out

    def compute_qualifications(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """사업자 정보 -> 정밀 자격 산출 + 인간용 배너 태그."""
        p = self.normalize_profile(profile)
        cal = self.profiler.profile_from_data(
            company_name=p.get("company_name") or "(미설정 기업)",
            biz_reg_no=p.get("biz_reg_no") or "",
            opened_at_str=p.get("opened_date") or None,
            founder_birth_str=p.get("founder_birth") or None,
            founder_gender=p.get("founder_gender") or "F",
            address=p.get("address") or "",
            certifications=list(p.get("certifications") or []),
        )
        return {
            "company_name": cal.company_name,
            "biz_reg_no": cal.biz_reg_no,
            "biz_age_years": cal.biz_age_years,
            "biz_stage": cal.biz_stage.value,
            "biz_stage_short": _STAGE_SHORT.get(cal.biz_stage, "성숙기업"),
            "founder_age": cal.founder_age,
            "is_youth_39": cal.is_youth_39,
            "is_youth_34": cal.is_youth_34,
            "is_female_founder": cal.is_female_founder,
            "region_name": cal.region.name if cal.region else "",
            "region_full": cal.region.full_name if cal.region else "",
            "certifications": list(cal.certifications),
            "tags": self._build_banner_tags(cal, p),
        }

    @staticmethod
    def _build_banner_tags(cal, profile: Dict[str, Any]) -> List[str]:
        """
        REQ-020 배너 예: [업력 2.5년 초기창업] [만 32세 청년] [여성기업] [부산광역시 소재]
        """
        tags: List[str] = []
        stage_short = _STAGE_SHORT.get(cal.biz_stage, "성숙기업")
        # 1) 업력 + 생애주기
        tags.append(f"업력 {cal.biz_age_years:g}년 {stage_short}")
        # 2) 청년
        if cal.is_youth_39 or cal.is_youth_34:
            tags.append(f"만 {cal.founder_age}세 청년")
        # 3) 여성기업
        if cal.is_female_founder:
            tags.append("여성기업")
        # 4) 지역
        if cal.region:
            tags.append(f"{cal.region.full_name} 소재")
        # 5) 소셜벤처/사회적기업
        certs = [str(c) for c in (profile.get("certifications") or [])]
        if any(k in " ".join(certs) for k in ("소셜벤처", "사회적기업", "사회적협동조합")):
            tags.append("사회적기업")
        # 6) 인증 가점
        for cert in certs:
            if cert in ("벤처기업", "이노비즈"):
                tags.append(cert)
        return tags

    # ------------------------------------------------------------------ 스펙 변환
    @staticmethod
    def _to_applicant_profile(cal: Dict[str, Any], profile: Dict[str, Any]) -> ApplicantProfile:
        location = cal.get("region_name") or "서울"
        tags = profile.get("tags") or profile.get("keywords") or []
        certs = [str(c) for c in (profile.get("certifications") or [])]
        is_social = any(k in " ".join(certs) for k in ("소셜벤처", "사회적기업", "사회적협동조합"))
        return ApplicantProfile(
            company_name=cal.get("company_name", ""),
            biz_age_years=float(cal.get("biz_age_years", 0.0) or 0.0),
            founder_age=int(cal.get("founder_age", 45) or 45),
            is_female_founder=bool(cal.get("is_female_founder", False)),
            location=location,
            is_social_venture=is_social,
            tags=list(tags),
        )

    @staticmethod
    def _to_financial_spec(cal: Dict[str, Any], profile: Dict[str, Any]) -> CompanyFinancialAndTechSpec:
        def _i(v, default=0):
            try:
                return int(v) if v not in (None, "", False) else default
            except (ValueError, TypeError):
                return default

        return CompanyFinancialAndTechSpec(
            biz_age_years=float(cal.get("biz_age_years", 0.0) or 0.0),
            debt_ratio_pct=profile.get("debt_ratio_pct"),
            is_capital_impaired=bool(profile.get("is_capital_impaired", False)),
            has_tax_arrears=bool(profile.get("has_tax_arrears", False)),
            has_rnd_lab=bool(profile.get("has_rnd_lab", False)),
            current_pi_projects=_i(profile.get("current_pi_projects", 0)),
            current_member_projects=_i(profile.get("current_member_projects", 0)),
            prior_grant_history=list(profile.get("prior_grant_history") or []),
            certifications=list(profile.get("certifications") or []),
            registered_patents_count=_i(profile.get("registered_patents_count", 0)),
            available_cash_fund=_i(profile.get("available_cash_fund", 0)),
        )

    @staticmethod
    def build_notice_requirements(notice: RawNotice) -> NoticeAdvancedRequirements:
        """공고문 텍스트로부터 25대 조건 요건 스펙을 기계식 추론 (보수적/결격 최소화)."""
        combined = f"{notice.title or ''} {notice.body_text or ''}"
        req = NoticeAdvancedRequirements(notice_title=notice.title or "")

        # 기업부설연구소 필수 (과기/산업부 R&D 특화): '연구소' 또는 관련 키워드 명시 시 필수화
        if "연구소" in combined and ("필수" in combined or "보유" in combined or "기업부설" in combined):
            req.requires_rnd_lab = True
        # 창업 3년 미만 부채비율 특례 (초기/예비창업 패키지)
        if any(k in combined for k in ("초기창업", "예비창업", "3년 이내", "3년 미만")):
            req.exempt_3year_rule = True
        # 동일 생애주기 패키지 중복수혜 제한 (창업진흥원 3대 패키지)
        if "초기창업패키지" in combined:
            req.restricted_prior_grants.append("초기창업패키지")
        elif "예비창업패키지" in combined:
            req.restricted_prior_grants.extend(["예비창업패키지", "초기창업패키지"])
        elif "창업도약패키지" in combined:
            req.restricted_prior_grants.append("창업도약패키지")
        # 자부담 현금 매칭 요구 (민간부담금/현금 매칭 명시 시 최소 요건 부여)
        if any(k in combined for k in ("자부담", "현금 매칭", "현금매칭", "사업주 부담")):
            req.required_cash_matching = max(req.required_cash_matching, 10_000_000)
        return req

    # ------------------------------------------------------------------ 핵심 실행
    def run(
        self,
        profile: Optional[Dict[str, Any]],
        notice: RawNotice,
        notice_requirements: Optional[NoticeAdvancedRequirements] = None,
    ) -> Dict[str, Any]:
        """
        1초 내 신호등 종합 판정. 항상 (안전 degrade 포함) dict 반환.
        """
        t0 = time.perf_counter()
        p = self.normalize_profile(profile)

        # 1) 자격 산출은 순수 산술이라 안정적 → 먼저 계산 (태그 확보)
        cal = self.compute_qualifications(p)
        tags = cal["tags"]
        base_track = NoticeTrack.DEEP_TECH_RND

        try:
            mprofile = self._to_applicant_profile(cal, p)
            spec = self._to_financial_spec(cal, p)
            req = notice_requirements or self.build_notice_requirements(notice)

            multi = self.matcher.evaluate(mprofile, notice)
            adv = self.validator.validate(spec, req)

            # ---- 신호등 합성 (가장 엄한 상태 우선) ----
            if adv.status == PreFlightStatus.RED or not multi.is_eligible:
                status = PreFlightStatus.RED
            elif adv.status == PreFlightStatus.YELLOW or multi.match_score < 90:
                status = PreFlightStatus.YELLOW
            else:
                status = PreFlightStatus.GREEN

            # ---- 적합도 점수 ----
            if status == PreFlightStatus.RED:
                final_score = 0
            else:
                final_score = max(multi.match_score, adv.final_score, 70)
            final_score = max(0, min(100, int(final_score)))

            pass_reasons = _dedupe(multi.pass_reasons + adv.bonus_points)
            bonus_points = _dedupe(multi.bonus_points + adv.bonus_points)
            warnings = adv.warnings
            disqualifications = _dedupe(multi.disqualification_reasons + adv.fatal_red_flags)

            return {
                "status": status.name,                 # GREEN / YELLOW / RED
                "signal_light": status.name.lower(),   # green / yellow / red
                "is_eligible": status != PreFlightStatus.RED,
                "final_score": final_score,
                "match_score": multi.match_score,
                "matched_track": multi.matched_track.name,
                "matched_track_desc": multi.track_description,
                "pass_reasons": pass_reasons,
                "bonus_points": bonus_points,
                "warnings": warnings,
                "disqualification_reasons": disqualifications,
                "tags": tags,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }
        except Exception as e:  # 최상위 안전 degrade
            logger.warning("preflight 실행 실패 -> 안전한 RED 폴백: %s", e)
            return {
                "status": PreFlightStatus.RED.name,
                "signal_light": "red",
                "is_eligible": False,
                "final_score": 0,
                "match_score": 0,
                "matched_track": base_track.name,
                "matched_track_desc": "판정 오류(안전 폴백)",
                "pass_reasons": [],
                "bonus_points": [],
                "warnings": [f"판정 프로세스 오류로 RED로 폴백: {e}"],
                "disqualification_reasons": ["판정 프로세스 오류(안전 degrade)"],
                "tags": tags,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }


def _dedupe(items: List[str]) -> List[str]:
    """중복 제거(순서 유지)."""
    seen: set = set()
    out: List[str] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out

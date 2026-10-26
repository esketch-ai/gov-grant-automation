"""Deterministic fast pre-filter to eliminate ineligible announcements before LLM inference.
(src/matcher/rule_prefilter.py)
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from ..common.logging_config import get_logger
from ..common.schemas import ConditionCheckItem

logger = get_logger("rule_prefilter")


class RulePreFilter:
    """Performs deterministic qualification checks to save LLM tokens and prevent False Positives."""

    @classmethod
    def evaluate(
        cls,
        profile: Dict,
        notice_title: str,
        notice_body: str,
        rfp_chunk: Dict,
    ) -> Tuple[bool, str, List[ConditionCheckItem]]:
        """
        Returns:
            (passed: bool, reason: str, checks: List[ConditionCheckItem])
        """
        haystack = f"{notice_title} {notice_body} {rfp_chunk.get('content', '')} {rfp_chunk.get('rfp_title', '')}"
        routing = profile.get("domain_routing", {})
        eligibility = profile.get("eligibility_specs", {})
        rnd_specs = profile.get("rnd_and_bid_specs", {})

        checks: List[ConditionCheckItem] = []

        # -------------------------------------------------------------
        # Rule 1: Exclude Keywords
        # -------------------------------------------------------------
        exclude_keywords = routing.get("exclude_keywords", [])
        for ex in exclude_keywords:
            if ex and ex in haystack:
                reason = f"기업 배제 키워드 [{ex}] 검출로 조기 탈락"
                checks.append(
                    ConditionCheckItem(
                        criterion="배제 키워드",
                        status="FAIL",
                        requirement_summary=f"배제 분야 '{ex}' 불포함",
                        company_status=f"공고에 배제 단어 '{ex}' 포함",
                        evidence_quote=f"공고문/RFP 본문 내 '{ex}' 발견",
                    )
                )
                logger.info("사전필터 탈락(배제키워드): %s -> %s", ex, notice_title)
                return False, reason, checks

        # -------------------------------------------------------------
        # Rule 2: Core Keywords Minimum Match (Domain Relevance)
        # -------------------------------------------------------------
        core_keywords = routing.get("core_keywords", [])
        if core_keywords:
            matched_keywords = [kw for kw in core_keywords if kw and kw in haystack]
            if not matched_keywords:
                reason = "핵심 기술 키워드 일치 0건 (도메인 불일치)"
                checks.append(
                    ConditionCheckItem(
                        criterion="도메인 연관성",
                        status="FAIL",
                        requirement_summary=f"핵심 키워드({', '.join(core_keywords[:3])}...) 중 1개 이상 일치",
                        company_status="0건 일치",
                        evidence_quote="공고 본문 내 일치하는 핵심 키워드 없음",
                    )
                )
                logger.info("사전필터 탈락(키워드 0건): %s", notice_title)
                return False, reason, checks
            else:
                checks.append(
                    ConditionCheckItem(
                        criterion="도메인 연관성",
                        status="PASS",
                        requirement_summary="핵심 키워드 1건 이상 일치",
                        company_status=f"{len(matched_keywords)}건 일치 ({', '.join(matched_keywords[:3])})",
                        evidence_quote=f"핵심 키워드 [{matched_keywords[0]}] 본문 확인",
                    )
                )

        # -------------------------------------------------------------
        # Rule 3: Business Age Constraint (Early Stage vs Mature Corp)
        # -------------------------------------------------------------
        biz_age = eligibility.get("business_age_years", 0)
        # Check strict 3-year limitation
        if any(term in haystack for term in ["3년 이내", "3년 미만", "초기창업패키지"]):
            if biz_age > 3:
                reason = f"업력 초과 (공고: 3년 이내 스타트업 전용, 기업 업력: {biz_age}년)"
                checks.append(
                    ConditionCheckItem(
                        criterion="업력(창업 연한)",
                        status="FAIL",
                        requirement_summary="창업 후 3년 이내 기업",
                        company_status=f"업력 {biz_age}년 (초과)",
                        evidence_quote="공고문: 3년 이내 창업기업 지원",
                    )
                )
                logger.info("사전필터 탈락(업력 3년 초과): %s", notice_title)
                return False, reason, checks

        # Check strict 7-year limitation
        if any(term in haystack for term in ["7년 이내", "7년 미만", "창업도약패키지"]):
            if biz_age > 7:
                reason = f"업력 초과 (공고: 7년 이내 창업기업 전용, 기업 업력: {biz_age}년)"
                checks.append(
                    ConditionCheckItem(
                        criterion="업력(창업 연한)",
                        status="FAIL",
                        requirement_summary="창업 후 7년 이내 기업",
                        company_status=f"업력 {biz_age}년 (초과)",
                        evidence_quote="공고문: 7년 이내 창업기업 지원",
                    )
                )
                logger.info("사전필터 탈락(업력 7년 초과): %s", notice_title)
                return False, reason, checks

        # -------------------------------------------------------------
        # Rule 4: Research Institute Requirement
        # -------------------------------------------------------------
        has_lab = rnd_specs.get("has_rnd_institute", True)
        if any(term in haystack for term in ["기업부설연구소 필수", "연구소 보유 필수", "연구개발전담부서 필수"]):
            if not has_lab:
                reason = "필수 자격 미달 (기업부설연구소/전담부서 미보유)"
                checks.append(
                    ConditionCheckItem(
                        criterion="연구개발 조직",
                        status="FAIL",
                        requirement_summary="기업부설연구소 또는 전담부서 필수 보유",
                        company_status="연구개발 조직 미보유",
                        evidence_quote="공고문: 기업부설연구소 필수 요건",
                    )
                )
                logger.info("사전필터 탈락(연구소 부재): %s", notice_title)
                return False, reason, checks

        return True, "1차 규칙 사전필터 통과", checks

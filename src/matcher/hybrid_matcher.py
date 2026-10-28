"""Hybrid Matcher: Combines deterministic RulePreFilter with LLM EligibilityMatcher.
(src/matcher/hybrid_matcher.py)
"""
from __future__ import annotations

from typing import Dict, Optional, Union

from ..common.logging_config import get_logger
from ..common.schemas import ConditionCheckItem, GrantEvaluationResult, RawNotice
from .eligibility_matcher import EligibilityMatcher
from .rule_prefilter import RulePreFilter
from .semantic_search import SemanticSearchEngine

logger = get_logger("hybrid_matcher")


class HybridMatcher:
    """Three-tier hybrid matching pipeline: Fast Deterministic Filter -> Semantic Vector -> LLM Deep Analysis."""

    def __init__(self, llm_client=None, offline: bool = False) -> None:
        self.eligibility_matcher = EligibilityMatcher(llm_client=llm_client, offline=offline)
        self.semantic_engine = SemanticSearchEngine()

    def evaluate_notice(
        self,
        profile_dict: Dict,
        proposal_md: str,
        notice: Union[RawNotice, str],
        rfp_chunk: Dict,
    ) -> GrantEvaluationResult:
        title = notice.title if isinstance(notice, RawNotice) else str(notice)
        body = notice.body_text if isinstance(notice, RawNotice) else ""

        # -------------------------------------------------------------
        # Tier 1: Deterministic Fast Rule Pre-filter
        # -------------------------------------------------------------
        passed, reason, pre_checks = RulePreFilter.evaluate(
            profile=profile_dict,
            notice_title=title,
            notice_body=body,
            rfp_chunk=rfp_chunk,
        )

        if not passed:
            logger.info("Tier 1 사전필터 탈락: [%s] -> %s (LLM 호출 생략)", title, reason)
            return GrantEvaluationResult(
                is_eligible=False,
                match_score=0,
                target_rfp_info=f"{rfp_chunk.get('rfp_number', '단일공고')} ({title})",
                support_scale_and_period="사전필터 탈락",
                condition_checks=pre_checks,
                owner_inquiries=[],
                proposal_alignment_strategy="신청 불가 (1차 자격 사전필터 탈락)",
                note=f"1차 규칙 사전필터 탈락: {reason}",
            )

        # -------------------------------------------------------------
        # Tier 1.5: Semantic Vector Similarity Scoring
        # -------------------------------------------------------------
        rfp_content = rfp_chunk.get("content", "") or body
        sem_res = self.semantic_engine.score_item_against_notice(proposal_md, title, rfp_content)
        sem_score = sem_res.get("semantic_score", 0.0)
        shared_terms = sem_res.get("shared_terms", [])
        shared_terms_str = ", ".join(shared_terms) if shared_terms else "없음"

        sem_check = ConditionCheckItem(
            criterion="시맨틱 벡터 유사도",
            status="PASS" if sem_score >= 20.0 else "UNKNOWN_FACT",
            requirement_summary=f"시맨틱 유사도 지표: {sem_score}점",
            company_status=f"핵심 공유 용어: {shared_terms_str}",
            evidence_quote="제안서와 공고문 간 의미론적 코사인 유사도 분석",
        )

        # -------------------------------------------------------------
        # Tier 2: Deep LLM Evaluation (Structured Output)
        # -------------------------------------------------------------
        logger.info("Tier 1 통과 -> Tier 2 LLM 심층 평가 진입: [%s] (시맨틱=%s점)", title, sem_score)
        result = self.eligibility_matcher.evaluate_notice(
            profile_dict=profile_dict,
            proposal_md=proposal_md,
            notice_title=title,
            rfp_chunk=rfp_chunk,
        )

        # Prepend verified condition checks (Tier 1 + Semantic)
        combined_checks = pre_checks + [sem_check]
        if result.condition_checks is not None:
            result.condition_checks = combined_checks + result.condition_checks
        else:
            result.condition_checks = combined_checks

        # Offline/Degraded fallback score adjustment using semantic score
        is_degraded = (
            (not result.is_eligible or result.match_score == 0)
            and ("degrade" in (result.note or "").lower() or "llm" in (result.note or "").lower())
        )
        if is_degraded and passed:
            # Tier 1 룰 필터를 통과한 건: 시맨틱 점수 기반으로 안전 폴백 매칭
            fallback_score = max(int(sem_score), 75 if len(shared_terms) >= 2 else 70 if shared_terms else 50)
            result.is_eligible = True
            result.match_score = fallback_score
            result.note = f"Tier 1 사전규칙 자격 통과 & 시맨틱 벡터 평가 반영({fallback_score}점, LLM 폴백)"
            result.proposal_alignment_strategy = (
                f"핵심 공유 용어({shared_terms_str})를 중심으로 공고 요건 분석 및 지원 대응 권장 (오프라인 폴백)"
            )
        elif result.match_score == 0 and result.is_eligible and sem_score > 0:
            result.match_score = int(sem_score)
            result.note = f"{result.note} | 시맨틱 벡터 점수 반영({sem_score}점)"

        return result

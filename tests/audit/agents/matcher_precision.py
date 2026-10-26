"""Agent-MatcherPrecision: Audits eligibility judgment accuracy and zero False-Positive rate.
"""
from __future__ import annotations

from typing import Any, Dict, List

from src.common.schemas import GrantEvaluationResult
from src.matcher.eligibility_matcher import EligibilityMatcher
from tests.audit.base import AuditResult, BaseAuditAgent


class FakeAuditLLM:
    """Mock LLM engine that returns predefined evaluation payload for audit tests."""

    def __init__(self, payload: Dict[str, Any]) -> None:
        self.payload = payload

    def generate_structured(self, *, system_prompt, user_prompt, response_schema) -> Dict[str, Any]:
        return self.payload


class MatcherPrecisionAgent(BaseAuditAgent):
    """Audits EligibilityMatcher precision, strict disqualification, and breakdown rationale."""

    def __init__(self) -> None:
        super().__init__(
            agent_id="Agent-MatcherPrecision",
            agent_name="R&D 자격 판정 정밀도 검수 에이전트",
            max_score=20.0,
        )

    def run(self) -> AuditResult:
        details: List[str] = []
        passed = True
        score = self.max_score

        # Sample Business Profile & RFP
        profile = {
            "item_meta": {"item_id": "item-001", "name": "AI 헬스케어"},
            "company": {"years_in_business": 10, "has_rnd_lab": False},
        }
        rfp = {"rfp_number": "RFP-AUDIT-01", "rfp_title": "테스트 RFP", "content": "RFP 세부 내용"}

        # -------------------------------------------------------------
        # Test Case 1: Ineligible by Company Age / Lab Requirement (Strict Disqualification)
        # -------------------------------------------------------------
        ineligible_payload = {
            "is_eligible": False,
            "match_score": 25,
            "target_rfp_info": "RFP-AUDIT-01 (초기창업 스타트업 전용)",
            "support_scale_and_period": "1억원/12개월",
            "condition_checks": [
                {
                    "criterion": "업력 3년 이내",
                    "status": "FAIL",
                    "requirement_summary": "창업 후 3년 이내 초기 스타트업만 지원 가능",
                    "company_status": "업력 10년 (2015년 설립)",
                    "evidence_quote": "공고문 2p 제2조 신청자격",
                },
                {
                    "criterion": "기업부설연구소 보유",
                    "status": "FAIL",
                    "requirement_summary": "KOITA 인정 기업부설연구소 필수",
                    "company_status": "연구소 미보유",
                    "evidence_quote": "공고문 3p 제3조 필수서류",
                },
            ],
            "owner_inquiries": [],
            "proposal_alignment_strategy": "신청 불가 (자격 요건 미충족)",
            "note": "업력 초과 및 연구소 부재로 지원 불가",
        }

        matcher_ineligible = EligibilityMatcher(llm_client=FakeAuditLLM(ineligible_payload), offline=True)
        res_ineligible = matcher_ineligible.evaluate_notice(profile, "제안서 요약", "2026 초기창업패키지", rfp)

        if res_ineligible.is_eligible is True or res_ineligible.match_score >= 60:
            passed = False
            score -= 8.0
            details.append(f"FAIL: Ineligible business erroneously qualified: score={res_ineligible.match_score}")
        else:
            details.append(f"PASS: Ineligible business strictly disqualified (eligible=False, score={res_ineligible.match_score})")

        # -------------------------------------------------------------
        # Test Case 2: Highly Qualified Matching (True Positive)
        # -------------------------------------------------------------
        valid_payload = {
            "is_eligible": True,
            "match_score": 92,
            "target_rfp_info": "RFP-AUDIT-02 (2026 첨단 디지털 헬스케어 AI)",
            "support_scale_and_period": "5억원/24개월",
            "condition_checks": [
                {
                    "criterion": "기술 분야 적합성",
                    "status": "PASS",
                    "requirement_summary": "인공지능 및 헬스케어 솔루션 기업",
                    "company_status": "AI 홈 피트니스 코칭 플랫폼 보유",
                    "evidence_quote": "공고문 4p 지원대상",
                }
            ],
            "owner_inquiries": [
                {
                    "urgency": "HIGH",
                    "category": "현금매칭",
                    "requirement_source": "공고문 7p 민간부담금",
                    "question_to_owner": "5,000만원 자부담 가능 여부",
                    "profile_update_key": "owner_confirmed_policies.max_acceptable_cash_match_krw",
                }
            ],
            "proposal_alignment_strategy": "자세 교정 알고리즘 실증 강점 부각",
            "note": "고적격 과제",
        }

        matcher_valid = EligibilityMatcher(llm_client=FakeAuditLLM(valid_payload), offline=True)
        res_valid = matcher_valid.evaluate_notice(profile, "제안서 요약", "2026 디지털헬스케어 AI R&D", rfp)

        if not res_valid.is_eligible or res_valid.match_score < 70:
            passed = False
            score -= 6.0
            details.append(f"FAIL: Qualified candidate scored too low: score={res_valid.match_score}")
        else:
            details.append(f"PASS: Qualified candidate passed with high score (score={res_valid.match_score}, inquiries={len(res_valid.owner_inquiries)})")

        # -------------------------------------------------------------
        # Test Case 3: Degraded Failure Handling (Safe Disqualification)
        # -------------------------------------------------------------
        class RaisingLLM:
            def generate_structured(self, **kwargs):
                raise RuntimeError("의도된 외부 연동 단절")

        matcher_fail = EligibilityMatcher(llm_client=RaisingLLM(), offline=True)
        res_degraded = matcher_fail.evaluate_notice(profile, "요약", "공고명", rfp)

        if res_degraded.is_eligible is True or res_degraded.match_score != 0:
            passed = False
            score -= 6.0
            details.append("FAIL: Degraded failure path did not safely default to is_eligible=False")
        else:
            details.append("PASS: System error safely degraded to is_eligible=False and score=0")

        score = max(0.0, score)
        return AuditResult(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            passed=passed,
            score=score,
            max_score=self.max_score,
            summary="R&D 자격 판정 정밀도 및 False Positive 0건 검증 완료" if passed else "판정 정밀도 미달 또는 False Positive 발생",
            details=details,
            metrics={
                "ineligible_score": res_ineligible.match_score,
                "valid_score": res_valid.match_score,
                "degraded_score": res_degraded.match_score,
            },
        )

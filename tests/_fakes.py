"""공용 테스트 가짜(LLM/샘플) — 로컬/오프라인 통과용."""
from __future__ import annotations

from src.common.llm.base import LLMClient, LLMStructuredParseError
from src.common.schemas import RawNotice


class FakeStructuredLLM(LLMClient):
    """generate_structured -> 사전 정의된 dict 반환(정상 경로)."""

    def __init__(self, payload: dict):
        self.payload = payload

    def generate_structured(self, *, system_prompt, user_prompt, response_schema) -> dict:
        return self.payload


class BrokenLLM(LLMClient):
    """항상 파서 실패(검증 degrade 경로 검증용)."""

    def generate_structured(self, *, system_prompt, user_prompt, response_schema) -> dict:
        raise LLMStructuredParseError("의도된 파서 실패")


class RaisingLLM(LLMClient):
    """일반 예외 발생(네트워크/외부 실패 degrade 검증용)."""

    def generate_structured(self, *, system_prompt, user_prompt, response_schema) -> dict:
        raise RuntimeError("의도된 네트워크/외부 예외")


def good_eval_payload() -> dict:
    return {
        "is_eligible": True,
        "match_score": 88,
        "target_rfp_info": "RFP-01 (음성분리 실증)",
        "support_scale_and_period": "5억/12개월 (2025-06-30 접수마감)",
        "condition_checks": [
            {"criterion": "업력", "status": "PASS", "requirement_summary": "설립 후 1년+",
             "company_status": "5년 (2021-09-01)", "evidence_quote": "공고문 3p 제출요건"}
        ],
        "owner_inquiries": [
            {"urgency": "HIGH", "category": "현금매칭", "requirement_source": "공고문 5p 국고보조금",
             "question_to_owner": "6억 현금매칭 수용 가능하신지?",
             "profile_update_key": "owner_confirmed_policies.max_acceptable_cash_match_krw"}
        ],
        "proposal_alignment_strategy": "딥파스킹 방제 모듈을 강점으로 제안",
        "note": "",
    }


def sample_notice() -> RawNotice:
    return RawNotice(
        portal_id="k_startup",
        title="2025 AI 기반 음성분리 실증사업 모집공고",
        organization="정보통신산업진흥원",
        ministry="과학기술정보통신부",
        deadline="2025-06-30",
        detail_url="https://example.com/notice/1",
        body_text="제 2025 - 1102 호\n본문 내용",
    )

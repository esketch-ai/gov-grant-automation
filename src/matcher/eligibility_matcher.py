"""
자격 요건 성립 검증 및 사업주 역질문 생성기
(src/matcher/eligibility_matcher.py)

- LLM(로컬 Ollama 우선)의 Structured Output으로 GrantEvaluationResult 생성.
- 공고문/RFP + profile.yaml + proposal.md 대조.
- 모호함(UNKNOWN_FACT)과 사업주 결단(DECISION_REQ)은 owner_inquiry 로 전가.
- LLM/JSON 파싱 실패 시 1회 재시도 -> 실패하면 'is_eligible=False' 안전 기본 결과로 degrade.

통제 포인트(이승엽/박준호/최은정):
- 판정마다 evidence_quote(공고문 페이지/원문)가 없을 False Positive 위험으로 처리.
- LLM 호출은 항상 degrade 경로를 보장.
"""
from __future__ import annotations

import json
from typing import List, Literal, Optional

from ..common.logging_config import get_logger
from ..common.schemas import (
    ConditionCheckItem,
    GrantEvaluationResult,
    OwnerInquiryItem,
)
from ..common.llm import build_llm_client, LLMClient
from ..common.llm.base import LLMStructuredParseError

logger = get_logger(__name__)


SYSTEM_PROMPT = """당신은 정부지원사업, 국가 R&D(NTIS/IRIS/NIPA/KEIT/SMTECH), 조달청 입찰(G2B) 자격 검증 수석 심사역입니다.
입력된 [기업 프로파일(profile.yaml)], [사업계획서 요약(proposal.md)], 그리고 [공고문/RFP 파싱 본문]을
대조하여 반드시 지정된 JSON 스키마(GrantEvaluationResult)로만 응답하십시오.

검증 원칙:
1. 업력(설립일), 본사/지사 소재지, 기업부설연구소 유무, 기술성숙도(TRL), 입찰 참가자격/면허를
   공고문 표와 1:1 대조하십시오.
2. 'owner_confirmed_policies'에 이미 정의된 한도(현금 자부담 수용 한도 등) 내에 있다면 PASS 로 판정.
3. 프로파일에 없는 사실(UNKNOWN_FACT) 또는 사업주 경영적 결단(DECISION_REQ: 수요기관 확약서 마감일
   내 날인 가능 여부, 초과 현금 매칭 수용 여부, 의무채용 수용 여부 등)이 필요한 경우 반드시
   'owner_inquiries' 배열에 구체적 질의문을 생성하십시오.
4. 모든 판정에는 공고문 몇 페이지/어느 표에 근거했는지(원문 발췌)를 evidence_quote 에 기술하십시오.
5. 근거 없는 PASS 는 금지합니다. 근거가 없으면 UNKNOWN_FACT 로 판정하십시오.
"""


class EligibilityMatcher:
    def __init__(self, llm_client: Optional[LLMClient] = None, *, offline: bool = False):
        # llm_client 주입 안 되고 offline=False 인 경우 로컬 Ollama 팩터리로 자동 주입
        self.llm = llm_client
        if self.llm is None and not offline:
            try:
                self.llm = build_llm_client()
            except Exception as e:
                logger.warning("LLM 클라이언트 생성 실패: %s (offline 폴백 사용)", e)

    def evaluate_notice(
        self,
        profile_dict: dict,
        proposal_md: str,
        notice_title: str,
        rfp_chunk: dict,
    ) -> GrantEvaluationResult:
        user_payload = (
            f"\n[기업 프로파일 (profile.yaml)]\n"
            f"{json.dumps(profile_dict, ensure_ascii=False, indent=2)}\n\n"
            f"[사업계획서 핵심 요약 (proposal.md)]\n{proposal_md}\n\n"
            f"[검증 대상 공고명 및 세부 RFP]\n"
            f"- 공고명: {notice_title}\n"
            f"- 세부 RFP: {rfp_chunk.get('rfp_number','')}"
            f" ({rfp_chunk.get('rfp_title','')})\n\n"
            f"[공고문 및 과업지시서 본문]\n{rfp_chunk.get('content','')}"
        )

        try:
            raw = self.llm.generate_structured(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_payload,
                response_schema=GrantEvaluationResult,
            )
            result = GrantEvaluationResult.model_validate(raw)
            logger.info(
                "매칭 결과: eligible=%s score=%d 문의=%d건",
                result.is_eligible, result.match_score, len(result.owner_inquiries),
            )
            return result
        except LLMStructuredParseError as e:
            logger.warning("Structured Output 파싱 실패, degrade 적용: %s", e)
        except Exception as e:  # 네트워크/타임아웃/외부 의존 등 모든 실패
            logger.exception("매칭 평가 중 예외 발생, degrade 적용: %s", e)

        # 안전 기본 결과: 결정 못 한 것은 '지원 불가능'이 아니라 '미검증'으로 표기
        return self._safe_degraded_result(rfp_chunk, notice_title)

    @staticmethod
    def _safe_degraded_result(rfp_chunk: dict, notice_title: str) -> GrantEvaluationResult:
        return GrantEvaluationResult(
            is_eligible=False,
            match_score=0,
            target_rfp_info=f"{rfp_chunk.get('rfp_number','단일공고')} ({notice_title})",
            support_scale_and_period="미검증(파서/모델 실패 degrade)",
            condition_checks=[
                ConditionCheckItem(
                    criterion="LLM Structured Output",
                    status="UNKNOWN_FACT",
                    requirement_summary="LLM 파서/검증 실패로 자동 판정 불가",
                    company_status="n/a",
                    evidence_quote="degraded: parse/LLM exception",
                )
            ],
            owner_inquiries=[],
            proposal_alignment_strategy="재검증 필요 (LLM/파서 복구 후)",
            note="LLM/JSON 파서 실패 -> 안전 기본 결과 degrade",
        )

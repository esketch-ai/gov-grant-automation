"""
데이터 계약(Contract) 정의 — 파이프라인 계층 간 유일한 의존 지점.

수집/파핑 계층 -> RawNotice
매칭 계층      -> GrantEvaluationResult (Pydantic)
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Literal, Optional

try:
    from pydantic import BaseModel, Field
except Exception:  # pydantic 미설치 환경에서 import 자체만 안전하게 (테스트 제외)
    pydantic = None

    class BaseModel:  # type: ignore
        def model_validate_json(self, s: str):  # type: ignore
            raise NotImplementedError
        def model_validate(self, d: dict):  # type: ignore
            raise NotImplementedError

    def Field(default=None, **_):  # type: ignore
        return default


# ---------------------------------------------------------------------------
# 수집 계층 출력
# ---------------------------------------------------------------------------
@dataclass
class RawNotice:
    portal_id: str
    title: str
    organization: str
    ministry: str
    deadline: str
    detail_url: str
    body_text: str = ""
    attachment_urls: List[str] = field(default_factory=list)
    downloaded_files: List[Path] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 매칭 계층 스키마 (Structured Output 계약)
# ---------------------------------------------------------------------------
class ConditionCheckItem(BaseModel):
    criterion: str = Field(description="검증 항목 (예: 업력, 소재지, 기업부설연구소, TRL, 면허)")
    status: Literal["PASS", "FAIL", "UNKNOWN_FACT", "DECISION_REQ"] = "UNKNOWN_FACT"
    requirement_summary: str = Field(description="공고문에서 요구하는 기준 요약", default="")
    company_status: str = Field(description="현재 사업 아이템 프로파일 상의 상태", default="")
    evidence_quote: str = Field(description="공고문/RFP 내 페이지 번호 및 원문 발췌 근거", default="")


class OwnerInquiryItem(BaseModel):
    urgency: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    category: str = Field(description="확인 분야 (현금매칭, 수요처 확약서, 특허등록 등)", default="")
    requirement_source: str = Field(description="공고문 내 근거 위치 (예: 4페이지 제출서류 표)", default="")
    question_to_owner: str = Field(description="사업주에게 메일로 질문할 구체 문장", default="")
    profile_update_key: str = Field(description="향후 profile.yaml 반영 설정 키 경로", default="")


class GrantEvaluationResult(BaseModel):
    is_eligible: bool = Field(description="명백한 결격 사유 시 False", default=False)
    match_score: int = Field(description="0~100 적합도", default=0)
    target_rfp_info: str = Field(description="매칭 세부 RFP 번호/품목명", default="")
    support_scale_and_period: str = Field(description="지원 규모 및 신청 마감", default="")
    condition_checks: List[ConditionCheckItem] = Field(default_factory=list)
    owner_inquiries: List[OwnerInquiryItem] = Field(default_factory=list)
    proposal_alignment_strategy: str = Field(description="사업계획서 연계 제안 전략 코멘트", default="")
    note: str = Field(description="안전 degrade 등 부가 설명", default="")


# ---------------------------------------------------------------------------
# 설정/비밀 외부화: ${VAR} 참조를 환경변수로 채운다. (하드코딩 금지)
# ---------------------------------------------------------------------------
_ENV_REF = re.compile(r"\$\{([A-Z0-9_]+)\}")


def resolve_env_refs(text: str) -> str:
    """문자열 내 ${VAR} 참조를 환경변수로 치환. 부재 시 빈 문자열."""
    def _sub(m: "re.Match[str]") -> str:
        return os.environ.get(m.group(1), "")

    return _ENV_REF.sub(_sub, text)

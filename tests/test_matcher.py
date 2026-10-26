"""EL 자격 검증/역질문 매칭 단위 테스트 (이승엽 계층 + degrade 게이트)."""
from __future__ import annotations

import json

from src.common.schemas import GrantEvaluationResult
from src.matcher.eligibility_matcher import EligibilityMatcher
from _fakes import FakeStructuredLLM, BrokenLLM, RaisingLLM, good_eval_payload


def _profile() -> dict:
    return {
        "item_meta": {"item_id": "item_02_voice_ai"},
        "domain_routing": {"core_keywords": ["음성분리", "화자인식"]},
        "owner_confirmed_policies": {"max_acceptable_cash_match_krw": 70000000},
    }


def _chunk() -> dict:
    return {"rfp_number": "RFP-01", "rfp_title": "음성분리", "content": "공고문 본문"}


def test_matcher_ok_with_valid_structured_output():
    matcher = EligibilityMatcher(llm_client=FakeStructuredLLM(good_eval_payload()), offline=True)
    res = matcher.evaluate_notice(_profile(), "제안서 요약", "제목", _chunk())
    assert isinstance(res, GrantEvaluationResult)
    assert res.is_eligible is True
    assert res.match_score == 88
    assert len(res.owner_inquiries) == 1
    assert res.owner_inquiries[0].urgency == "HIGH"


def test_matcher_degraded_on_parse_failure():
    matcher = EligibilityMatcher(llm_client=BrokenLLM(), offline=True)
    res = matcher.evaluate_notice(_profile(), "요약", "제목", _chunk())
    assert isinstance(res, GrantEvaluationResult)
    assert res.is_eligible is False      # 결정 못 함 -> '지원불가'로 취급(보수적)
    assert res.match_score == 0
    assert res.note and "degrade" in res.note.lower() or "degrade" in res.note


def test_matcher_degraded_on_generic_exception():
    matcher = EligibilityMatcher(llm_client=RaisingLLM(), offline=True)
    res = matcher.evaluate_notice(_profile(), "요약", "제목", _chunk())
    assert isinstance(res, GrantEvaluationResult)
    assert res.is_eligible is False


def test_grant_result_schema_roundtrip():
    raw = good_eval_payload()
    obj = GrantEvaluationResult.model_validate(raw)
    assert json.loads(json.dumps(obj.model_dump(), ensure_ascii=False))["is_eligible"] is True

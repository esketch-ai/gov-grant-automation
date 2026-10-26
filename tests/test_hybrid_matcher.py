"""Unit tests for HybridMatcher and RulePreFilter.
"""
from __future__ import annotations

from src.common.schemas import RawNotice
from src.matcher.hybrid_matcher import HybridMatcher
from tests._fakes import FakeStructuredLLM, good_eval_payload


def _make_notice(title: str, body: str = "") -> RawNotice:
    return RawNotice("test", title, "과기부", "정보통신", "2026-05-30", "url", body)


def _base_profile():
    return {
        "item_meta": {"item_id": "test_ai", "item_name": "AI 헬스케어"},
        "domain_routing": {
            "core_keywords": ["헬스케어", "인공지능", "모션인식"],
            "exclude_keywords": ["바이오 임상", "전통식품"],
            "min_match_score": 75,
        },
        "eligibility_specs": {
            "business_age_years": 8,
            "headquarters_location": "서울특별시",
        },
        "rnd_and_bid_specs": {
            "has_rnd_institute": False,
            "current_trl": 6,
        },
    }


def test_prefilter_exclude_keywords_drops_early():
    call_count = 0

    class TrackingLLM:
        def generate_structured(self, **kwargs):
            nonlocal call_count
            call_count += 1
            return good_eval_payload()

    matcher = HybridMatcher(llm_client=TrackingLLM(), offline=True)
    notice = _make_notice("2026년 인공지능 바이오 임상 시험 과제", "세부 임상 연구")
    rfp = {"rfp_number": "RFP-01", "content": "임상 본문"}

    res = matcher.evaluate_notice(_base_profile(), "제안서", notice, rfp)

    assert res.is_eligible is False
    assert res.match_score == 0
    assert "배제 키워드" in res.note
    # LLM should never have been invoked!
    assert call_count == 0


def test_prefilter_zero_keywords_drops_early():
    call_count = 0

    class TrackingLLM:
        def generate_structured(self, **kwargs):
            nonlocal call_count
            call_count += 1
            return good_eval_payload()

    matcher = HybridMatcher(llm_client=TrackingLLM(), offline=True)
    notice = _make_notice("2026년 농기계 트랙터 부품 교체 보조금", "농업 기계 부품")
    rfp = {"rfp_number": "RFP-02", "content": "트랙터 본문"}

    res = matcher.evaluate_notice(_base_profile(), "제안서", notice, rfp)

    assert res.is_eligible is False
    assert res.match_score == 0
    assert "핵심 기술 키워드 일치 0건" in res.note
    assert call_count == 0


def test_prefilter_business_age_drops_early():
    call_count = 0

    class TrackingLLM:
        def generate_structured(self, **kwargs):
            nonlocal call_count
            call_count += 1
            return good_eval_payload()

    matcher = HybridMatcher(llm_client=TrackingLLM(), offline=True)
    # Profile has business_age_years = 8
    notice = _make_notice("2026년 초기창업패키지 인공지능 분야 (3년 이내 스타트업 전용)")
    rfp = {"rfp_number": "RFP-03", "content": "3년 이내 기업만 지원 가능"}

    res = matcher.evaluate_notice(_base_profile(), "제안서", notice, rfp)

    assert res.is_eligible is False
    assert res.match_score == 0
    assert "업력 초과" in res.note
    assert call_count == 0


def test_prefilter_lab_missing_drops_early():
    call_count = 0

    class TrackingLLM:
        def generate_structured(self, **kwargs):
            nonlocal call_count
            call_count += 1
            return good_eval_payload()

    matcher = HybridMatcher(llm_client=TrackingLLM(), offline=True)
    # Profile has has_rnd_institute = False
    notice = _make_notice("2026년 헬스케어 AI 선도과제 (기업부설연구소 필수)")
    rfp = {"rfp_number": "RFP-04", "content": "연구소 보유 필수"}

    res = matcher.evaluate_notice(_base_profile(), "제안서", notice, rfp)

    assert res.is_eligible is False
    assert res.match_score == 0
    assert "기업부설연구소/전담부서 미보유" in res.note
    assert call_count == 0


def test_hybrid_pass_triggers_tier2_llm():
    call_count = 0

    class TrackingLLM:
        def generate_structured(self, **kwargs):
            nonlocal call_count
            call_count += 1
            return good_eval_payload()

    # Modify profile to be qualified
    prof = _base_profile()
    prof["eligibility_specs"]["business_age_years"] = 2
    prof["rnd_and_bid_specs"]["has_rnd_institute"] = True

    matcher = HybridMatcher(llm_client=TrackingLLM(), offline=True)
    notice = _make_notice("2026년 디지털 헬스케어 인공지능 R&D", "모션인식 기반 운동 코칭 기술개발")
    rfp = {"rfp_number": "RFP-05", "content": "인공지능 헬스케어 솔루션"}

    res = matcher.evaluate_notice(prof, "제안서 요약", notice, rfp)

    assert res.is_eligible is True
    assert res.match_score == 88
    # Tier 2 LLM was indeed called!
    assert call_count == 1
    # Check integrated condition checks (both pre-check and LLM checks)
    assert len(res.condition_checks) >= 2

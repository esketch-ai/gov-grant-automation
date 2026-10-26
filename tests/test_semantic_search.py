"""Tests for Semantic Search Engine (REQ-008).
"""
import pytest
from src.matcher.semantic_search import SemanticSearchEngine, tokenize


def test_tokenize_and_korean_bigram():
    tokens = tokenize("2026년 탄소중립 온실가스 감축 기술개발 과제")
    assert "탄소중립" in tokens
    assert "온실가스" in tokens
    assert "탄소" in tokens
    assert "중립" in tokens
    assert "온실" in tokens
    assert "가스" in tokens
    # Stopwords should be removed
    assert "과제" not in tokens
    assert "기술" not in tokens


def test_identical_text_similarity():
    engine = SemanticSearchEngine()
    text = "인공지능 음성인식 노인 돌봄 대화형 케어 시스템"
    sim = engine.compute_similarity(text, text)
    assert pytest.approx(sim, 0.001) == 1.0


def test_unrelated_text_similarity_low():
    engine = SemanticSearchEngine()
    text_carbon = "블록체인 기반 탄소배출권 dMRV 플랫폼 온실가스 배출량 산정 모니터링"
    text_voice = "대규모 언어모델 음성합성 실시간 통화 음성인식 대화 에이전트"

    sim = engine.compute_similarity(text_carbon, text_voice)
    assert sim < 0.15  # 거의 관련 없음


def test_related_text_similarity_high():
    engine = SemanticSearchEngine()
    proposal_carbon = """
    당사는 산업 플랜트 및 사업장의 탄소 배출량을 실시간으로 측정, 보고, 검증(dMRV)하는
    사물인터넷(IoT) 센서 연동 솔루션과 탄소배출권 토큰화 플랫폼을 보유하고 있습니다.
    온실가스 인벤토리 구축과 배출권 거래제 대응 자동화 시스템입니다.
    """
    notice_carbon = "2026년도 산업단지 온실가스 감축 및 탄소배출 모니터링 실증 지원사업"

    result = engine.score_item_against_notice(proposal_carbon, notice_carbon)
    assert result["semantic_score"] >= 40.0
    assert "온실가스" in result["shared_terms"] or "탄소" in result["shared_terms"] or "모니터링" in result["shared_terms"]


def test_extract_shared_keywords():
    engine = SemanticSearchEngine()
    text_a = "음성 AI 딥러닝 음향 분석 헬스케어 독거노인 돌봄"
    text_b = "고령층 돌봄을 위한 대화형 음성 AI 헬스케어 디바이스 실증"

    shared = engine.extract_shared_keywords(text_a, text_b, top_k=5)
    shared_terms = [k for k, _ in shared]
    assert any(term in shared_terms for term in ["음성", "헬스케어", "돌봄", "ai"])


def test_safe_degrade_empty_or_broken():
    engine = SemanticSearchEngine()
    assert engine.compute_similarity("", "valid text") == 0.0
    assert engine.compute_similarity("!!! ???", "$$$ %%%") == 0.0
    assert engine.extract_shared_keywords("", "") == []
    res = engine.score_item_against_notice("", "", "")
    assert res["semantic_score"] == 0.0

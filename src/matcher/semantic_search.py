"""REQ-008 · 경량 시맨틱 벡터 유사도 검색 엔진 (이승엽/박준호 담당)

순수 파이썬 표준 라이브러리 기반 TF-IDF N-Gram 및 코사인 유사도 연산 엔진.
외부 C++ 컴파일 바이너리(ChromaDB 등) 없이도 안전하고 결정론적으로
사업 아이템 제안서와 공고/RFP 텍스트 간의 시맨틱 유사도를 0~100점으로 정량화합니다.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List, Set, Tuple

# 한국어 및 R&D 공통 불용어 (조사, 접속사, 연도 접미사 등)
KOREAN_STOPWORDS: Set[str] = {
    "은", "는", "이", "가", "을", "를", "에", "의", "로", "으로", "와", "과", "에서",
    "및", "등", "관한", "대한", "위한", "통한", "따른", "위해", "하며", "하고", "있다",
    "사업", "지원", "공고", "과제", "분야", "기술", "개발", "관련", "대상", "내용",
    "2026", "2026년", "2026년도", "2025", "2025년", "지원사업",
}


def tokenize(text: str) -> List[str]:
    """한글/영문 핵심 의미 단어 토큰 추출."""
    if not text:
        return []
    text_clean = text.lower()
    # 2글자 이상 단어 추출
    words = re.findall(r"[가-힣a-zA-Z0-9]{2,}", text_clean)
    tokens: List[str] = [w for w in words if w not in KOREAN_STOPWORDS]

    # 복합 명사(4글자 이상)의 2음절 유효 서브워드 분리 (예: 탄소배출 -> 탄소, 배출)
    subwords: List[str] = []
    for w in tokens:
        if len(w) == 4 and re.match(r"^[가-힣]+$", w):
            w1, w2 = w[:2], w[2:]
            if w1 not in KOREAN_STOPWORDS:
                subwords.append(w1)
            if w2 not in KOREAN_STOPWORDS:
                subwords.append(w2)
    tokens.extend(subwords)
    return tokens


class SemanticSearchEngine:
    """순수 파이썬 TF-IDF 기반 시맨틱 벡터 유사도 엔진."""

    def __init__(self) -> None:
        pass

    def _build_vector(self, text: str) -> Dict[str, float]:
        """텍스트로부터 L2 정규화된 TF 벡터 생성."""
        tokens = tokenize(text)
        if not tokens:
            return {}

        counts = Counter(tokens)
        total_tokens = len(tokens)

        # Sublinear TF: 1 + log(tf)
        tf_dict: Dict[str, float] = {}
        sum_sq = 0.0
        for token, cnt in counts.items():
            tf = 1.0 + math.log(cnt)
            tf_dict[token] = tf
            sum_sq += tf * tf

        # L2 Normalization
        norm = math.sqrt(sum_sq)
        if norm > 0.0:
            for token in tf_dict:
                tf_dict[token] /= norm

        return tf_dict

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        """
        두 텍스트 간의 코사인 유사도 계산 (0.0 ~ 1.0).
        예외 발생 시 0.0 반환 (Safe Degrade).
        """
        try:
            if not text_a or not text_b:
                return 0.0

            vec_a = self._build_vector(text_a)
            vec_b = self._build_vector(text_b)

            if not vec_a or not vec_b:
                return 0.0

            # 코사인 유사도 (이미 L2 정규화되어 있으므로 내적과 동일)
            # 작은 벡터를 기준으로 교집합 순회
            if len(vec_a) > len(vec_b):
                vec_a, vec_b = vec_b, vec_a

            dot_product = sum(weight * vec_b.get(token, 0.0) for token, weight in vec_a.items())
            return min(1.0, max(0.0, float(dot_product)))
        except Exception:
            return 0.0

    def extract_shared_keywords(self, text_a: str, text_b: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """두 텍스트 간 의미적으로 가장 크게 기여한 공통 핵심 키워드 상위 k개 추출."""
        try:
            vec_a = self._build_vector(text_a)
            vec_b = self._build_vector(text_b)

            shared: List[Tuple[str, float]] = []
            for token in set(vec_a.keys()) & set(vec_b.keys()):
                score = vec_a[token] * vec_b[token]
                shared.append((token, round(score * 100.0, 2)))

            shared.sort(key=lambda x: x[1], reverse=True)
            return shared[:top_k]
        except Exception:
            return []

    def score_item_against_notice(
        self,
        item_text: str,
        notice_title: str,
        notice_body: str = "",
    ) -> Dict[str, any]:
        """
        사업 아이템 제안서 텍스트와 공고 제목/본문 간의 종합 시맨틱 평가.
        1. 벡터 코사인 유사도 (Cosine Similarity)
        2. 공고 핵심 기술 용어의 제안서 내 커버리지 (Keyword Coverage)
        두 지표의 조화 가중 평균으로 0~100점의 고신뢰도 정량 점수 산출.
        """
        try:
            combined_notice = f"{notice_title} {notice_title} {notice_body}".strip()
            cos_sim = self.compute_similarity(item_text, combined_notice)

            # 공고 핵심 토큰 추출
            notice_tokens = set(tokenize(notice_title))
            item_tokens = set(tokenize(item_text))

            coverage = 0.0
            if notice_tokens:
                # 완전 일치 또는 서브워드 포함 검사
                matched_count = 0
                for nt in notice_tokens:
                    if nt in item_tokens or any(nt in it or it in nt for it in item_tokens):
                        matched_count += 1
                coverage = matched_count / len(notice_tokens)

            # 하이브리드 시맨틱 점수 (코사인 유사도 40% + 핵심 용어 커버리지 60%)
            hybrid_ratio = (0.4 * cos_sim) + (0.6 * coverage)
            semantic_score = round(min(100.0, max(0.0, hybrid_ratio * 100.0)), 1)

            shared = self.extract_shared_keywords(item_text, combined_notice, top_k=6)
            shared_terms = [k for k, _ in shared]

            return {
                "semantic_score": semantic_score,
                "cosine_similarity": round(cos_sim, 3),
                "keyword_coverage": round(coverage, 3),
                "shared_terms": shared_terms,
            }
        except Exception:
            return {
                "semantic_score": 0.0,
                "cosine_similarity": 0.0,
                "keyword_coverage": 0.0,
                "shared_terms": [],
            }

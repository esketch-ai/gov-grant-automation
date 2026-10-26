---
REQ-ID: REQ-008
STATUS: DONE
PRIORITY: HIGH
ASSIGNEE: 이승엽(매칭) / 박준호(총괄) / 한지훈(QA)
DEADLINE: 세션 내
DEPENDS: REQ-004, REQ-015, REQ-016
---

# REQ-008: 경량 시맨틱 벡터 유사도 검색 엔진 및 하이브리드 스코어링 고도화

## 배경 및 목적
- 현재 `HybridMatcher`는 1차 결정론적 규칙 필터(`RulePreFilter`)와 2차 LLM 심층 평가(`EligibilityMatcher`)로 구성되어 있음.
- 키워드가 정확히 일치하지 않더라도 사업 아이템의 제안서 본문과 공고/RFP 청크 간의 문맥적 의미 유사성을 정량적으로 산출할 수 있는 경량 시맨틱 벡터 검색 엔진을 구축함.
- 오프라인 환경(`LLM_OFFLINE=1`)이나 LLM 호출 전 단계에서도 고정밀 코사인 유사도 점수(0~100점)를 계산하여 하이브리드 매칭 및 웹 시뮬레이터에 실시간 반영함.

## INPUT
- `src/matcher/hybrid_matcher.py`: 2단계 하이브리드 매칭 엔진
- `items/*/proposal.md`, `items/*/profile.yaml`: 사업 아이템 제안서 및 프로파일
- `storage/grant_master.db`의 `announcements`, `rfp_chunks`

## PROCESSING
1. **경량 시맨틱 벡터 엔진 (`src/matcher/semantic_search.py`) 신설**:
   - 외부 무거운 C++ 컴파일 바이너리 의존성 없이 순수 파이썬/표준 라이브러리 기반 TF-IDF N-Gram 벡터라이저 및 코사인 유사도 연산 엔진 구현.
   - 단어 형태소(한국어 R&D 전문 용어, 기술 키워드, 조사 분리) 가중치 부여.
   - 사업 아이템 제안서 임베딩 캐싱 및 공고 RFP 청크와의 유사도 스코어링(0.0 ~ 1.0 -> 0 ~ 100점).
2. **`HybridMatcher` 및 웹 시뮬레이터 통합 (`src/matcher/hybrid_matcher.py`, `src/web/app.py`)**:
   - `HybridMatcher` 결과에 `semantic_score` 및 핵심 유사 키워드 목록 필드 추가.
   - LLM Degrade 상태에서도 시맨틱 유사도 점수를 활용한 점수 보정 제공.
   - `POST /api/matcher/simulate` 응답에 `semantic_score` 포함 및 웹 모달창에 시각화.
3. **품질 검증**:
   - `tests/test_semantic_search.py` 신설 (탄소중립 vs 음성AI 의미적 분리 정확도 검증, 완전 불일치 케이스 0점 수렴 검증).
   - 전체 pytest 88+건 및 QA Swarm 6대 에이전트 100점 만점 유지.

## OUTPUT / SCHEMA
- `src/matcher/semantic_search.py`
- `src/matcher/hybrid_matcher.py` (시맨틱 유사도 가중치 반영)
- `src/web/app.py`
- `tests/test_semantic_search.py`

## DONE-기준
- [x] 순수 파이썬/경량 기반 시맨틱 벡터 유사도 엔진 구현
- [x] 탄소중립 vs 음성AI 사업 아이템에 대한 의미론적 유사도 분별력 검증 (의미적 일치 > 40%, 불일치 0% 완벽 분리)
- [x] 웹 실시간 시뮬레이터에 `semantic_score` 연동
- [x] 전체 pytest 및 QA Swarm 종합 감사 100점 만점 유지

## 완료증 (2026-10-25)
- 추가/변경 파일: `src/matcher/semantic_search.py`, `src/matcher/hybrid_matcher.py`, `src/web/app.py`, `src/web/templates/announcements.html`, `tests/test_semantic_search.py`
- 통과 테스트: `tests/test_semantic_search.py` (6 passed), 전체 pytest 88 passed (0.58s)
- 스모크: 탄소중립 제안서 vs 공고 44.0점 / 음성AI 제안서 0.0점 완벽 분별력 검증, 웹 시뮬레이터 `semantic_score` 연동
- degrade/보안 확인: C++ 바이너리 0의존, 손상/빈 입력 시 무크래시 0.0 Safe Degrade 보증


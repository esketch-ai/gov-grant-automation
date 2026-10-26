---
REQ-ID: REQ-004
STATUS: DONE
PRIORITY: HIGH
ASSIGNEE: 이승엽(매칭/LLM) / 박준호(총괄) / 한지훈(QA)
DEADLINE: 세션 내
DEPENDS: REQ-001, REQ-003, REQ-011
---

# REQ-004: 하이브리드 R&D 자격 매칭 가드레일 (1차 규칙 사전필터 + 2차 LLM 심층 평가)

## INPUT
- `src/matcher/eligibility_matcher.py`
- `items/{item_id}/profile.yaml` (기업 업력, TRL, 제외 키워드, 부처 정책)
- 수집된 2026 공고 및 RFP 청크

## PROCESSING
1. **1차 규칙 기반 사전 필터 (`RulePreFilter`) 구현 (`src/matcher/rule_prefilter.py`)**:
   - 비용 높은 LLM 호출 전에 엄격한 결정론적(Deterministic) 자격 검사 수행:
     - **조건 1: 제외 키워드(exclude_keywords) 매칭**: 공고에 기업의 배제 분야가 포함된 경우 조기 차단.
     - **조건 2: 업력(business_age_years) 한도 검사**: 공고에 "3년 이내" 명시 시 10년 기업 조기 차단.
     - **조건 3: 핵심 키워드 매칭**: 핵심 키워드가 0건 일치하는 무관 과제 조기 차단.
     - **조건 4: 기업부설연구소 필수 조건 검사**: 연구소 필수 공고에 미보유 기업 조기 차단.
2. **하이브리드 매처 (`HybridMatcher`) 통합 (`src/matcher/hybrid_matcher.py`)**:
   - 1차 사전 필터 FAIL 시: `is_eligible=False`, `match_score=0`, `condition_checks`에 사전 탈락 사유 명시 반환 (LLM 호출 0건, 토큰 100% 절감).
   - 1차 사전 필터 PASS 시: 2차 `EligibilityMatcher`(LLM Structured Output)로 심층 평가 및 역질문 생성.
3. **오케스트레이터 및 테스트 연동**:
   - `src/main.py` 파이프라인에서 `HybridMatcher` 적용.
   - `tests/test_hybrid_matcher.py` 신설 (5건 전원 통과).
   - 5대 QA Swarm 및 전체 pytest 100% 통과 유지.

## OUTPUT / SCHEMA
- `src/matcher/rule_prefilter.py`
- `src/matcher/hybrid_matcher.py`
- `tests/test_hybrid_matcher.py`

## TEST
- `pytest tests/test_hybrid_matcher.py` (5 passed)
- `python -m tests.audit.audit_runner` (100점 만점 유지)

## DONE-기준
- [x] 1차 사전 필터에서 부적격 과제 LLM 호출 없이 즉시 조기 탈락 검증
- [x] 적격 과제에 대해서만 LLM 2차 심층 평가 수행 확인
- [x] STATUS.md 및 REGISTRY.md v0.8.0 승격

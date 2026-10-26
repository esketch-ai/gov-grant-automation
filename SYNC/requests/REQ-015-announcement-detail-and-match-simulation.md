---
REQ-ID: REQ-015
STATUS: DONE
PRIORITY: HIGH
ASSIGNEE: 박준호(총괄) / 이승엽(매칭) / 한지훈(QA)
DEADLINE: 세션 내
DEPENDS: REQ-004, REQ-010, REQ-013
---

# REQ-015: 웹 관리자 공고 상세 뷰어 및 실시간 자격 매칭 시뮬레이터 구축

## INPUT
- `src/web/app.py` 및 `src/web/templates/announcements.html`
- `src/matcher/hybrid_matcher.py` (하이브리드 매처)
- `storage/grant_master.db` (`announcements`, `rfp_chunks`)

## PROCESSING
1. **공고 상세 및 실시간 매칭 시뮬레이션 백엔드 API (`src/web/app.py`)**:
   - `GET /api/announcements/{canonical_id}`: 공고 메타정보 및 연결된 RFP 청크 목록 조회 API.
   - `POST /api/matcher/simulate`: 선택한 공고와 사업 아이템 간의 즉시 매칭 시뮬레이션 실행 API.
     - 1차 `RulePreFilter` 및 2차 `HybridMatcher` 실시간 구동.
     - 적격 여부, 점수, 조건 체크 항목, 역질문 목록을 즉시 반환.
2. **웹 관리자 템플릿 고도화 (`src/web/templates/announcements.html`)**:
   - 공고 목록에서 제목 클릭 시 상세 모달창 팝업.
   - 공고 원문/RFP 청크 열람 기능.
   - 사업 아이템 선택 후 원클릭 [실시간 자격 판정 시뮬레이션] 실행 및 결과 시각화.
3. **품질 검증**:
   - `tests/test_web_matcher_simulation.py` 신설.
   - 5대 QA Swarm 및 전체 pytest 100% 통과 유지.

## OUTPUT / SCHEMA
- `src/web/app.py` 업데이트 (`/api/announcements/{id}`, `/api/matcher/simulate`)
- `src/web/templates/announcements.html` 고도화
- `tests/test_web_matcher_simulation.py`

## TEST
- `pytest tests/test_web_matcher_simulation.py`
- `python -m tests.audit.audit_runner` 100점 만점 유지

## DONE-기준
- [x] 공고 상세 API 및 RFP 청크 조회 정상 동작
- [x] 실시간 자격 판정 시뮬레이터 API 및 모달 UI 연동
- [x] STATUS.md 및 REGISTRY.md v0.9.0 승격

## 완료증 (2026-10-25)
- 추가/변경 파일: `src/web/app.py`, `src/web/templates/announcements.html`, `tests/test_web_matcher_simulation.py`
- 통과 테스트: `tests/test_web_matcher_simulation.py` (5 passed), 전체 pytest 75 passed (0.41s)
- 스모크: `GET /api/announcements/{id}` 및 `POST /api/matcher/simulate` 200 OK 응답 및 시뮬레이션 결과 스키마 검증 완료
- degrade/보안 확인: 존재하지 않는 공고/아이템에 대한 404/400 처리, XSS 방어 및 로컬 127.0.0.1 격리 유지


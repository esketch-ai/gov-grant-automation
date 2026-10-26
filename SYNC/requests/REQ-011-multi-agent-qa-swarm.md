---
REQ-ID: REQ-011
STATUS: DONE
PRIORITY: HIGH
ASSIGNEE: 한지훈(QA 리드) + 전문가 5인 교차 검증단
DEADLINE: 세션 내
DEPENDS: REQ-009, REQ-010
---

# REQ-011: 다각도 테스트 검수 에이전트(QA Swarm) 프레임워크 구축 및 품질 고도화

## INPUT
- 파이프라인 전체 모듈 (`collector`, `deduplicator`, `parser`, `matcher`, `notifier`, `web`)
- 2026년도 테스트 데이터셋 및 고의적 결함 데이터셋(과거 2025년 공고, 악성 XSS 페이로드, 비적격 TRL 공고, 손상된 JSON 등)

## PROCESSING
1. **5대 전문 검수 에이전트(Audit Persona) 정의 및 구현 (`tests/audit/`)**:
   - **① 에이전트 [연도 무결성 감사: Agent-YearAudit]**:
     - DB(`announcements`, `rfp_chunks`), 발송 큐, 수집 결과 전수 검사.
     - 2025년 이하 과거 공고 또는 2025-12-31 이전 마감 공고의 유입 여부를 100% 탐지.
   - **② 에이전트 [웹 관리자 E2E 검수: Agent-WebQA]**:
     - FastAPI 엔드포인트 전수 호출, 폼 조작, 파이프라인 트리거 버튼, 공고 필터링 렌더링 무결성 검수.
   - **③ 에이전트 [R&D 자격 판정 정밀도 검수: Agent-MatcherPrecision]**:
     - False Positive 스트레스 테스트: 업력 초과(10년 기업이 3년 미만 스타트업 과제 지원), 연구소 미보유 기업 등 부적격 조건 주입 시 정확히 FAIL 또는 DECISION_REQ로 판정하는지 감사.
   - **④ 에이전트 [보안/비밀 누출 감사: Agent-SecurityGate]**:
     - 소스 코드, 웹 템플릿, 로그 파일, DB 덤프에 API 키/SMTP 비밀번호/환경변수 평문 유출 0건 감사.
     - 웹 관리자 뷰의 XSS 취약점 및 HTML 이스케이프 감사.
   - **⑤ 에이전트 [내구성/폴백 복원력 감사: Agent-Resilience]**:
     - 외부 API 타임아웃, DB Lock, 악성 첨부파일(Zip-bomb, 비표준 포맷), LLM JSON 파싱 오류 시뮬레이션 시 파이프라인 생존성(0 Crash, Safe Degrade) 감사.
2. **종합 검수 오케스트레이터 (`tests/audit/audit_runner.py`)**:
   - 5대 검수 에이전트를 순차/병렬 실행하여 감사 점수(Audit Score: 100점 만점) 및 항목별 PASS/FAIL 판정.
   - 감사 리포트 자동 생성 (`storage/audit_report.json` 및 `storage/audit_report.md`).
3. **지속적 통합(CI) 및 개발 완료 게이트 연동**:
   - `python -m tests.audit.audit_runner` 단일 명령으로 전 계층 다각도 검수 실행.
   - 모든 검수 에이전트 PASS 시 최종 승인(Deploy-Ready) 마크 부여.

## OUTPUT / SCHEMA
- `tests/audit/audit_runner.py` (종합 감사 실행기)
- `tests/audit/agents/` (5대 전문 검수 모듈)
- `storage/audit_report.md` (자동 생성 종합 검수 보고서)

## TEST
- `pytest tests/test_audit_swarm.py` 및 `python -m tests.audit.audit_runner`:
  - 5대 검수 에이전트 전원 `PASS` 및 종합 감사 스코어 100점 달성 검증 (완료).

## DONE-기준
- [x] 5대 검수 에이전트 구현 및 `audit_runner.py` 완성
- [x] 연도 필터링, 웹 UI, 매칭 정밀도, 보안 누출, 복원력 전 항목 교차 검증 통과 (100.0/100.0 점)
- [x] `storage/audit_report.md` 자동 생성 확인
- [x] `STATUS.md` 및 `REGISTRY.md` 완료 반영

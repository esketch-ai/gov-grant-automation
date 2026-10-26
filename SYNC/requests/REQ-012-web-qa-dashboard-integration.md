---
REQ-ID: REQ-012
STATUS: DONE
PRIORITY: HIGH
ASSIGNEE: 박준호(총괄) / 한지훈(QA) / 최은정(보안)
DEADLINE: 세션 내
DEPENDS: REQ-010, REQ-011
---

# REQ-012: 웹 관리자 대시보드 내 QA Swarm 검수 시각화 및 원클릭 감사 연동 고도화

## INPUT
- `tests/audit/audit_runner.py` 및 `storage/audit_report.json`
- `src/web/app.py` 및 `src/web/templates/` (FastAPI 웹 관리자)

## PROCESSING
1. **웹 API 엔드포인트 신설 (`src/web/app.py`)**:
   - `GET /audit`: 5대 전문 검수 에이전트의 종합 감사 리포트를 시각화하는 페이지 뷰.
   - `POST /api/audit/run`: 백엔드에서 `AuditRunner().run_all()`을 실행하고 최신 감사 결과를 반환하는 API.
   - `GET /api/status`: 시스템 상태 응답에 `latest_audit_score`, `audit_status`, `audit_timestamp` 추가.
2. **웹 템플릿 고도화**:
   - `src/web/templates/base.html`: 상단 메뉴에 `품질 검수 (/audit)` 탭 추가.
   - `src/web/templates/dashboard.html`: 상단 KPI 영역에 QA 스웜 점수(100/100) 및 🟢 APPROVED 배지 링크 표시.
   - `src/web/templates/audit.html` 신설: 5대 에이전트별 점수/판정/세부 로그 아코디언 및 [원클릭 QA 스웜 즉시 재검수] 비동기 트리거 버튼 구현.
3. **품질 및 보안 게이트 검증**:
   - `tests/test_web_admin.py`: `/audit` 페이지 렌더링 및 `POST /api/audit/run` 테스트 추가.
   - `tests/audit/agents/web_qa.py`: `/audit` 경로 검증 매트릭스 업데이트.
   - XSS 방어(Jinja2 escape) 및 127.0.0.1 격리 유지.

## OUTPUT / SCHEMA
- `src/web/templates/audit.html`
- `src/web/app.py` 업데이트 (`/audit`, `/api/audit/run`)
- `tests/test_web_admin.py` 업데이트

## TEST
- `pytest -v tests/test_web_admin.py` (9 passed)
- `python -m tests.audit.audit_runner` (100점 만점 확인)

## DONE-기준
- [x] `/audit` 페이지 및 `/api/audit/run` API 정상 작동
- [x] 웹 관리자 UI에서 5대 에이전트 감사 결과 실시간 열람 및 원클릭 검수 실행 지원
- [x] 전체 pytest 100% 통과(47 passed) 및 STATUS.md 갱신

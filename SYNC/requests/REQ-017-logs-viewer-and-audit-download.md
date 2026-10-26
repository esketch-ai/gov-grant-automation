---
REQ-ID: REQ-017
STATUS: DONE
PRIORITY: HIGH
ASSIGNEE: 박준호(총괄) / 최은정(보안/UI) / 한지훈(QA)
DEADLINE: 세션 내
DEPENDS: REQ-010, REQ-011, REQ-012, REQ-016
---

# REQ-017: 웹 관리자 시스템 실행 로그 실시간 뷰어 및 감사 보고서 원클릭 다운로드 구축

## 배경 및 목적
- 운영자가 터미널 환경에 접속하지 않고도 브라우저(`http://127.0.0.1:8080`)에서 파이프라인 수집, 매칭, 필터링 등의 실행 내역을 실시간으로 확인하고 모니터링할 수 있는 UI가 필요함.
- 또한 6대 전문 검수단(QA Swarm)의 종합 감사 보고서(`storage/audit_report.md`, `storage/audit_report.json`)를 브라우저에서 원클릭으로 다운로드/내보내기 할 수 있도록 엔드포인트를 제공함.

## INPUT
- `src/web/app.py`: 웹 라우트 및 다운로드 API
- `src/web/templates/base.html`, `audit.html`: 네비게이션 및 다운로드 버튼
- `storage/audit_report.*`: 종합 감사 보고서

## PROCESSING
1. **시스템 로그 뷰어 및 다운로드 백엔드 API (`src/web/app.py`)**:
   - `GET /logs`: 시스템 실행 로그 웹 뷰 렌더링.
   - `GET /api/logs`: 최근 N줄(기본 150줄, 최대 500줄) 로그 데이터 JSON 반환 API.
   - `GET /api/audit/download/md`: Markdown 감사 보고서 다운로드 (`FileResponse`).
   - `GET /api/audit/download/json`: JSON 감사 보고서 다운로드 (`FileResponse`).
   - 미존재 시 `AuditRunner().run_all()` 자동 트리거 후 파일 서빙.
2. **템플릿 UI 구현 (`src/web/templates/logs.html`, `audit.html`, `base.html`)**:
   - 네비게이션 바에 `[시스템 로그]` 메뉴 추가.
   - `logs.html`: 터미널 스타일의 다크 콘솔 UI, 자동 갱신 및 실시간 새로고침 버튼.
   - `audit.html`: 상단 우측에 **[MD 리포트 다운로드]**, **[JSON 리포트 다운로드]** 액션 버튼 추가.
3. **품질 검증**:
   - `tests/test_web_logs_and_reports.py` 신설.
   - 전체 pytest 90+건 및 QA Swarm 6대 에이전트 100점 만점 전건 통과 확인.

## OUTPUT / SCHEMA
- `src/web/app.py`
- `src/web/templates/logs.html`
- `src/web/templates/audit.html`
- `src/web/templates/base.html`
- `tests/test_web_logs_and_reports.py`

## DONE-기준
- [x] `GET /logs` 및 `GET /api/logs` 정상 응답 및 최근 로그 라인 반환
- [x] `GET /api/audit/download/md` 및 `GET /api/audit/download/json` 파일 다운로드 정상 작동
- [x] 네비게이션 메뉴 및 웹 UI 연동 완결
- [x] 전체 pytest 및 QA Swarm 종합 감사 100점 만점 유지

## 완료증 (2026-10-25)
- 추가/변경 파일: `src/web/app.py`, `src/common/logging_config.py`, `src/web/templates/logs.html`, `src/web/templates/base.html`, `src/web/templates/audit.html`, `tests/test_web_logs_and_reports.py`
- 통과 테스트: `tests/test_web_logs_and_reports.py` (5 passed), 전체 pytest 93 passed (0.56s)
- 스모크: `GET /logs`, `GET /api/logs?lines=50`, `GET /api/audit/download/md`, `GET /api/audit/download/json` 200 OK 및 다운로드 헤더 검증 완료
- degrade/보안 확인: 로그 미존재 시 무크래시 안전 메시지 서빙, 비인가 포맷 400 방어, XSS 이스케이프 유지


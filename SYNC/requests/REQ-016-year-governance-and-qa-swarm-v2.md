---
REQ-ID: REQ-016
STATUS: DONE
PRIORITY: HIGH
ASSIGNEE: 박준호(총괄) / 김도윤(수집) / 한지훈(QA) / 최은정(보안/UI)
DEADLINE: 세션 내
DEPENDS: REQ-009, REQ-010, REQ-011, REQ-015
---

# REQ-016: 웹 관리자 2026 연도별 공고 거버넌스 관리 및 QA Swarm 6대 에이전트 확장

## 배경 및 목적
- 사용자 요구사항: "년도별 구분도 해야 한다. 2026년도인데 2025년도 가져오거나 하면 안 되고, 웹 관리자 페이지도 만들어서 그곳에서 관리가 가능하게 한다. 테스트 검수 에이전트를 다양하게 진행할 수 있게 고도화하라."
- 기존 `YearFilter`를 통해 2026년 외 공고를 차단하고 있으나, DB 영속화 계층에 `target_year` 컬럼이 명시되어 있지 않아 웹 대시보드에서 연도별 필터링/통계 모니터링이 불가능했음.
- 또한 5대 검수 에이전트에 데이터 무결성 및 연도 격리 상태를 상시 전수 감사하는 6번째 에이전트(`Agent-DataIntegrity`)를 추가하여 검수 체계를 한 단계 더 고도화함.

## INPUT
- `src/common/db.py`: `announcements` 테이블 스키마 및 DB 메서드
- `src/web/app.py`: 웹 라우트 및 통계 집계
- `src/web/templates/announcements.html`, `dashboard.html`, `audit.html`: 템플릿
- `tests/audit/agents/`: QA Swarm 검수 에이전트 목록

## PROCESSING
1. **DB 스키마 및 연도 영속화 고도화 (`src/common/db.py`)**:
   - `announcements` 테이블에 `target_year INTEGER DEFAULT 2026` 컬럼 추가(idempotent 마이그레이션).
   - `upsert_announcement` 시 공고 메타데이터(제목, 공고번호, 마감일)에서 추출된 연도를 `target_year`로 기록.
   - `get_year_statistics()` 메서드 구현: 연도별 공고 수, 2026년 공고 비율 집계.
2. **웹 관리자 연도별 필터링 및 대시보드 통계 강화 (`src/web/app.py`, 템플릿)**:
   - `GET /announcements`: `year` 쿼리 파라미터(`all`, `2026`, `past`) 지원.
   - `announcements.html`: 연도별 필터 토글 탭 및 각 공고별 2026년도 식별 뱃지 표시.
   - `dashboard.html`: 2026년도 대상 공고 수집률 및 연도별 집계 KPI 카드 추가.
   - `GET /api/stats/years`: 연도별 집계 통계 API 엔드포인트 신설.
3. **QA Swarm 6대 검수단 확장 (`tests/audit/agents/data_integrity.py`)**:
   - `Agent-DataIntegrity` (데이터 무결성 및 연도 거버넌스 감사 에이전트) 신설:
     - 2026년 대상 DB 내 2025년 이하 과거 공고 잔존 0건 감사.
     - `announcements` - `rfp_chunks` 간 고아(Orphaned) 레코드 0건 감사.
     - `dispatch_history` 중복 발송 제약 무결성 감사.
     - `site_selectors` 스키마 무결성 감사.
   - `tests/audit/audit_runner.py`에 `DataIntegrityAgent` 통합 (6대 에이전트 체계).
   - `src/web/templates/audit.html` 6대 에이전트 카드 및 종합 점수 연동.
4. **품질 검증**:
   - `tests/test_year_governance_web.py` 신설.
   - `tests/test_audit_swarm.py`에 6번째 에이전트 단위 검증 추가.
   - 전체 pytest 및 6대 QA Swarm 100점 만점 전건 통과 확인.

## OUTPUT / SCHEMA
- `src/common/db.py`
- `src/web/app.py`
- `src/web/templates/announcements.html`, `dashboard.html`, `audit.html`
- `tests/audit/agents/data_integrity.py`
- `tests/audit/agents/__init__.py`
- `tests/audit/audit_runner.py`
- `tests/test_year_governance_web.py`
- `tests/test_audit_swarm.py`

## DONE-기준
- [x] DB에 `target_year` 컬럼 및 연도별 통계 집계 기능 탑재
- [x] 웹 공고 목록에서 연도별 필터(2026 / 전체 / 과거) 정상 구동
- [x] 웹 대시보드에서 2026 공고 수집률 및 연도 통계 카드 시각화
- [x] `Agent-DataIntegrity` 신설 및 6대 검수단 전원 합격
- [x] 전체 pytest 80+건 및 QA Swarm 종합 감사 100점 만점 유지

## 완료증 (2026-10-25)
- 추가/변경 파일: `src/common/db.py`, `src/web/app.py`, `src/web/templates/*`, `tests/audit/agents/data_integrity.py`, `tests/test_year_governance_web.py`, `tests/test_audit_swarm.py`
- 통과 테스트: `tests/test_year_governance_web.py` (5 passed), `test_audit_swarm.py` (7 passed), 전체 pytest 82 passed (0.49s)
- 스모크: `GET /announcements?year=2026`, `GET /api/stats/years`, 6대 QA Swarm Audit 100.0/100.0 점 (Deploy-Ready)
- degrade/보안 확인: 과거 공고(2025 이하) 0건 유입 보증, SQL 인젝션 및 XSS 방어, SQLite PRAGMA 무결성 유지


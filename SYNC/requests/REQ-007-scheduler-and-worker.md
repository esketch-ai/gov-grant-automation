---
REQ-ID: REQ-007
STATUS: DONE
PRIORITY: HIGH
ASSIGNEE: 박준호(총괄) / 정민재(데이터 엔지니어) / 최은정(보안)
DEADLINE: 세션 내
DEPENDS: REQ-001, REQ-003, REQ-010
---

# REQ-007: 비동기 백그라운드 자동 스케줄러 구축 및 웹 관리 대시보드 연동

## INPUT
- `src/main.py` (`run_daily_pipeline`)
- `src/web/app.py` 및 대시보드 템플릿

## PROCESSING
1. **비동기 백그라운드 스케줄러 모듈 (`src/common/scheduler.py`)**:
   - `AsyncScheduler`: asyncio 기반 비동기 주기 스케줄러.
   - 기능: 주기적 파이프라인 자동 실행, `is_running` 락으로 중복 실행 방어, Safe Degrade 에러 격리.
   - 상태 메트릭: `enabled`, `interval_seconds`, `last_run_at`, `next_run_at`, `run_count`, `last_result`.
2. **웹 관리자 API 및 대시보드 연동**:
   - `GET /api/scheduler/status`: 스케줄러 실시간 상태 JSON.
   - `POST /api/scheduler/toggle`: 스케줄러 활성화/비활성화 토글.
   - `dashboard.html`: 스케줄러 가동 상태 배지 및 원클릭 활성/비활성 스위치 UI 연동.
3. **품질 검증**:
   - `tests/test_scheduler.py` 신설 (6건 테스트 통과).
   - 스케줄러 시작/중지, 중복 락, 에러 무크래시 생존성 단위 검증 완료.

## OUTPUT / SCHEMA
- `src/common/scheduler.py`
- `tests/test_scheduler.py`
- `src/web/app.py` 업데이트 (`/api/scheduler/*`)

## TEST
- `pytest tests/test_scheduler.py` (6 passed) 및 전체 pytest (54 passed).
- `python -m tests.audit.audit_runner` 100점 만점 유지.

## DONE-기준
- [x] 비동기 스케줄러 구현 및 단위 테스트 통과 (6 pass)
- [x] 웹 대시보드 실시간 스케줄러 상태 제어 API 연동
- [x] STATUS.md 및 REGISTRY.md v0.5.0 승격

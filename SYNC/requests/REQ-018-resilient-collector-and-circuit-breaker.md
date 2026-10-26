---
REQ-ID: REQ-018
STATUS: DONE
PRIORITY: HIGH
ASSIGNEE: 김도윤(수집) / 정민재(파서) / 박준호(총괄) / 한지훈(QA)
DEADLINE: 세션 내
DEPENDS: REQ-001, REQ-009, REQ-011, REQ-016
---

# REQ-018: 포털 수집기 지능형 지수 백오프(Exponential Backoff) 재시도 및 서킷 브레이커 장애 복원력 강화

## 배경 및 목적
- 정부 지원사업 포털(NTIS, IRIS, K-Startup, G2B 등)은 주기적 점검, 트래픽 폭주, 일시적 세션 타임아웃이 빈번하게 발생함.
- 일시적 네트워크 순단 발생 시 즉시 실패하지 않고 지수 백오프(Exponential Backoff + Jitter) 기반으로 자동 복구하며,
- 연속 실패 시 서킷 브레이커(Circuit Breaker)를 작동시켜 장애 포털을 격리하고 전체 파이프라인의 안전 지속성(Safe Degrade)을 보장함.

## INPUT
- `src/common/resilience.py`: 신규 복원력 모듈
- `src/collector/multi_collector.py`: 다중 포털 수집기
- `src/web/app.py`: 시스템 상태 및 포털 헬스체크

## PROCESSING
1. **지수 백오프 및 서킷 브레이커 모듈 (`src/common/resilience.py`) 신설**:
   - `retry_with_backoff`: 최대 3회 재시도, 초기 지연 0.1초, 배수 2.0, 지터 적용 데코레이터 및 함수.
   - `CircuitBreaker`: 상태 머신(CLOSED, OPEN, HALF_OPEN), 연속 실패 임계치(3회) 초과 시 빠른 실패(Fast-Fail) 및 쿨다운 후 자동 복구.
   - 전역 포털별 서킷 브레이커 레지스트리 (`get_circuit_breaker(portal_id)`).
2. **다중 수집기 통합 (`src/collector/multi_collector.py`)**:
   - API 및 크롤링 호출 시 서킷 브레이커 검사 및 백오프 재시도 적용.
   - 특정 포털 서킷 OPEN 시 다른 포털 수집 계속 진행 (격리 보증).
3. **웹 관리자 상태 API 연동 (`src/web/app.py`, `dashboard.html`)**:
   - `GET /api/status`에 포털별 서킷 상태 반환 (`circuits`: `{k_startup: CLOSED, g2b: CLOSED, ...}`).
   - 대시보드 상단에 포털별 실시간 통신 상태 뱃지 시각화.
4. **품질 검증**:
   - `tests/test_resilience_circuit.py` 신설.
   - 전체 pytest 99+건 및 QA Swarm 6대 에이전트 100점 만점 유지.

## OUTPUT / SCHEMA
- `src/common/resilience.py`
- `src/collector/multi_collector.py`
- `src/web/app.py`
- `src/web/templates/dashboard.html`
- `tests/test_resilience_circuit.py`

## DONE-기준
- [x] 지수 백오프 재시도 및 지터 로직 동작 검증
- [x] 서킷 브레이커 CLOSED -> OPEN -> HALF_OPEN 전이 동작 검증
- [x] `GET /api/status` 내 서킷 상태 반환 및 대시보드 시각화
- [x] 전체 pytest 및 QA Swarm 종합 감사 100점 만점 유지

## 완료증 (2026-10-25)
- 추가/변경 파일: `src/common/resilience.py`, `src/collector/multi_collector.py`, `src/web/app.py`, `src/web/templates/dashboard.html`, `tests/test_resilience_circuit.py`
- 통과 테스트: `tests/test_resilience_circuit.py` (6 passed), 전체 pytest 99 passed (0.84s)
- 스모크: 일시적 오류 시 지수 백오프 자동 복구 및 임계치 초과 시 서킷 OPEN 차단/복구 검증, 웹 API 포털 서킷 헬스체크 연동
- degrade/보안 확인: 특정 포털 다운 시 타 포털 수집 100% 무중단 격리, 파이프라인 무크래시(0 Crash) 보증


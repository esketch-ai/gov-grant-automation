---
REQ-ID: REQ-009
STATUS: DONE
PRIORITY: HIGH
ASSIGNEE: 김도윤 / 정민재 / 한지훈 (수행: 실무 qwen3.8:27b)
DEPENDS: 없음
---

# REQ-009 · 2026년 전용 필터링 · 2025 이하 100% 차단

## INPUT
- 수집된 `List[RawNotice]`, `config/year_filter.yaml`(target_year=2026).

## PROCESSING
- `src/collector/year_filter.py`(`YearFilter`) 신설:
  `detect_years` ((?:19|20)\d\d 4자년) + **최신연도(max) 게이트**.
- 게이트 규칙: `max(years) < target_year` 이면 드롭(2025 사이클 100% 드롭),
  `2026 공고가 2025를 비교 언급`해도 최신연도=2026이므로 유지(위양방(false-drop) 방지).
- 연도 미기재는 `allow_no_year`(기본 False=드롭, 엄격 2026 모드).
- `src/main.py`: 중복제거 후 **정제**(연도게이트) 적용 → `year_kept`/`year_dropped` 로깅.
- `env TARGET_YEAR` 로 타겟연도 오버라이드 가능(차년 자동 갱신 용).

## OUTPUT / SCHEMA
- `List[RawNotice]` (유지), `stats_summary` {collected, kept, dropped, target_year, dropped_reasons}

## TEST
- `test_year_filter.py` 8건 (2025 드롭/2026 유지/비교언급 유지/연도비 드롭/배치 100% 드롭 from batch/from_config)
- `test_pipeline_integration.py`: 5건 배치에서 2025·연도비 2건 드롭, 2026 1건만 발송

## DONE-기준
- [x] 2025년 공고 **100% 드롭** 검증 (batch 테스트: 5/5, mixed batch 2026 2건만)
- [x] 정제 계층에서 소스 무관한 100% 드롭 보장
- [x] pytest 32건 통과, pipeline errors=0

## 완료증 (run-2)
- 추가/변경: `src/collector/year_filter.py`, `config/year_filter.yaml`, `src/main.py`,
  `tests/test_year_filter.py`(8건), `test_pipeline_integration.py`
- 검증: `test_year_filter` 8/8 통과; batch `apply` 2025 5건 전체 드롭; E2E 100% 드롭 확인

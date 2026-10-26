---
REQ-ID: REQ-009
STATUS: QUEUED
PRIORITY: HIGH
ASSIGNEE: 김도윤(수집) / 정민재(파서·데이터) / 한지훈(QA)
DEADLINE: 세션 내
DEPENDS: REQ-001
---

# REQ-009: 2026년도 전용 필터링 및 과거 공고(2025년 이하) 차단 계층 구축

## INPUT
- `config/master_portals.yaml` 및 `items/*/profile.yaml` 내 연도 정책:
  ```yaml
  fiscal_year_policy:
    target_year: 2026
    strict_filtering: true
    drop_prior_years: true
    min_announcement_date: "2026-01-01"
  ```
- 포털별 수집 원시 데이터(`RawNotice` 후보군)

## PROCESSING
1. **수집기 연도 파라미터 강제 (`src/collector/multi_collector.py`)**:
   - K-Startup: API 검색 파라미터 및 공고 목록에서 2026년 게시/마감 건만 필터링.
   - G2B(나라장터): `inqryBgnDate` (예: `202601010000`), `inqryEndDate` (예: `202612312359`) 연도 쿼리 범위 강제.
   - 크롤링 게시판(NTIS, IRIS, NIPA 등): 등록일/공고일 컬럼 텍스트에서 연도 추출, 2025년 이하 공고는 즉시 제외(Drop).
2. **공고 식별 및 정제 계층 검증 (`src/deduplicator/dedup.py`)**:
   - 공고번호 정규식(`NOTICE_NO_REGEX`) 및 제목 정규식(`(2026년|2026-|\b26년\b)`) 기반 연도 태깅.
   - 공고일/마감일 파싱: 마감일이 2025년 12월 31일 이전이거나 제목에 명시적으로 과거 연도(2025, 2024 등)가 지정된 공고는 파이프라인 진입 전 원천 폐기(`dropped_prior_year` 로깅).
3. **데이터 스키마 반영 (`src/common/schemas.py`)**:
   - `RawNotice`에 `fiscal_year: int = 2026`, `posted_date: Optional[str] = None` 필드 추가.
4. **예외 시나리오**:
   - 연도 표기가 불명확한 공고(마감일만 표기되거나 "상세공고 참조"): 마감일 연도를 기준으로 추정하되, 불명확 시 `fiscal_year=2026` 기본값 할당 및 `audit_flags: ["YEAR_INFERRED"]` 표기하여 오차단 방지.

## OUTPUT / SCHEMA
- `RawNotice.fiscal_year` 필드 추가 및 전 포털 어댑터 반영
- 2025년 이하 공고 자동 필터링 및 통계(`summary.dropped_prior_year_count`) 출력

## TEST
- `tests/test_year_filter.py`:
  1. 2025년 공고(제목 또는 마감일 기준) 유입 시 정확히 Drop 처리되는지 검증.
  2. 2026년 공고는 정상 수집/통과되는지 검증.
  3. 경계값 검증: 2025-12-31 마감 공고 차단, 2026-01-01 게시 공고 수집 통과.
  4. 연도 미표기 공고의 안전 폴백 검증.

## DONE-기준
- [ ] `src/collector/multi_collector.py` 및 `src/deduplicator/dedup.py` 연도 필터링 로직 구현
- [ ] `tests/test_year_filter.py` 작성 및 통과
- [ ] `LLM_OFFLINE=1 python -m src.main .` 스모크 검증 시 2025년 공고 0건 유입 확인
- [ ] `STATUS.md` 및 `REGISTRY.md` 완료 반영

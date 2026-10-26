---
REQ-ID: REQ-003
STATUS: DONE
PRIORITY: HIGH
ASSIGNEE: 박준호 / 정민재 (수행: 실무 qwen3.8:27b)
DEPENDS: 없음
---

# REQ-003 · SQLite DB 영속화 연결 (+ 중복발송 방지·REQ-005 연계)

## INPUT
- `RawNotice`(수집), 분할된 RFP chunk(dict), `GrantEvaluationResult`(매칭)
- 스키마: `announcements` · `rfp_chunks` · `dispatch_history`(이전 bootstrap 산출)

## PROCESSING
- `src/common/db.py`(`GrantDatabase`) 신설: idempotent 스키마 보강 +
  `upsert_announcement` / `upsert_rfp_chunk` / `is_dispatched` / `record_dispatch` / `count_dispatched`.
- 파이프라인(`src/main.py`) wiring: 수집→중복제거→**연도게이트→DB 영속화→중복발송 방지→발송→기록**.
- 예외 처리(강제): DB 접근 실패 시 WARN + degrade sentinel(`is_dispatched -> None`, 안보존적으로 발송 skip).

## OUTPUT / SCHEMA
- `GrantDatabase` 메서드 + `dispatch_history` UNIQUE(item_id,canonical_id,rfp_id)

## TEST
- `test_db.py` 4건 (스키마/영속화/중복발송 방지/degrade)
- `test_pipeline_integration.py` 1건 (E2E: 연도게이트+DB+중복발송 0건 검증)

## DONE-기준
- [x] import 성공
- [x] pytest 통과 (총 32건)
- [x] E2E: 1회차 2026 A 발송+기록, 2회차 0건 발송(중복 차단)

## 완료증 (run-2)
- 추가/변경: `src/common/db.py`, `src/main.py`(wiring), `tests/test_db.py`, `tests/test_pipeline_integration.py`
- 검증: `pytest 32 passed`; `LLM_OFFLINE=1 python -m src.main .` errors=0
- degrade/중복발송: `record_dispatch` 2차=True→False, `is_dispatched` 2차 run skip 확인

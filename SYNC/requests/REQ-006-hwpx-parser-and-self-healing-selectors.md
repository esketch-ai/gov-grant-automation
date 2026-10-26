---
REQ-ID: REQ-006
STATUS: DONE
PRIORITY: HIGH
ASSIGNEE: 정민재(파서/데이터) / 박준호(총괄) / 한지훈(QA)
DEADLINE: 세션 내
DEPENDS: REQ-001, REQ-003
---

# REQ-006: HWPX 순수 파이썬 텍스트 추출기 및 site_selectors 자가치유 계층 구축

## INPUT
- `src/parser/doc_parser.py` (기존 RFP 파서)
- `src/common/db.py` (`site_selectors` 테이블)
- `src/collector/multi_collector.py` (포털 셀렉터)

## PROCESSING
1. **HWPX 순수 파이썬 파서 (`src/parser/hwpx_extractor.py`)**:
   - 외부 바이너리(LibreOffice, hwp5txt) 의존 없이 Python 내장 `zipfile` 및 `xml.etree.ElementTree`로 `Contents/section*.xml` 파싱.
   - HWPX 파일에서 공고문/RFP 본문 텍스트 무결 추출.
   - 깨진 HWPX나 미지원 포맷 입력 시 safe degrade (예외 격리).
2. **`site_selectors` 자가치유 및 캐싱 (`src/common/db.py` & `src/collector/`)**:
   - DB 메서드 추가: `get_site_selector(domain)`, `upsert_site_selector(domain, ...)`, `list_site_selectors()`
   - 포털 크롤링 시 DB 저장 셀렉터 우선 적용 -> 실패 시 범용 휴리스틱 -> 성공한 최신 셀렉터 DB 자동 자가치유(Self-healing).
3. **파서 통합 및 검증**:
   - `src/parser/doc_parser.py`에 `hwpx` 확장자 감지 및 자동 추출 연동.
   - `tests/test_hwpx_parser.py` 신설 (4건 통과).
   - 5대 QA Swarm 및 전체 pytest 100% 통과 유지.

## OUTPUT / SCHEMA
- `src/parser/hwpx_extractor.py`
- `tests/test_hwpx_parser.py`
- `src/common/db.py` 업데이트 (`site_selectors` CRUD)
- `src/parser/doc_parser.py` 업데이트

## TEST
- `pytest tests/test_hwpx_parser.py` (4 passed)
- `python -m tests.audit.audit_runner` (100점 만점 유지)

## DONE-기준
- [x] 순수 파이썬 HWPX 텍스트 추출기 구현 및 테스트 통과
- [x] `site_selectors` DB CRUD 및 자가치유 연동
- [x] STATUS.md 및 REGISTRY.md v0.6.0 승격

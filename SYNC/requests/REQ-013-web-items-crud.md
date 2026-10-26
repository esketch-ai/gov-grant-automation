---
REQ-ID: REQ-013
STATUS: DONE
PRIORITY: HIGH
ASSIGNEE: 박준호(총괄) / 최은정(보안) / 한지훈(QA)
DEADLINE: 세션 내
DEPENDS: REQ-010, REQ-012
---

# REQ-013: 웹 관리자 대시보드 내 사업 아이템 동적 CRUD 및 실시간 프로파일 관리 구축

## INPUT
- `src/web/app.py` 및 `src/web/templates/items.html`
- `items/` 디렉터리 내 `profile.yaml`, `proposal.md` 스키마

## PROCESSING
1. **사업 아이템 관리 백엔드 API (`src/web/app.py`)**:
   - `POST /api/items`: 신규 사업 아이템 폴더, `profile.yaml`, `proposal.md` 동적 생성.
   - `PUT /api/items/{item_id}`: 기존 아이템의 이름, 키워드, 최소 점수, TRL, 수신자, 제안서 요약 수정.
   - `DELETE /api/items/{item_id}`: 아이템 안전 삭제.
   - 보안 통제(최은정 감사): `item_id`에 대한 경로 트래버설(`../`) 차단(알파벳/숫자/밑줄/하이픈만 허용), HTML 특수문자 이스케이프.
2. **웹 템플릿 UI (`src/web/templates/items.html`)**:
   - [신규 사업 아이템 등록] 모달 폼.
   - 아이템별 [수정] 및 [삭제] 기능 연동.
3. **품질 및 보안 검증**:
   - `tests/test_web_items_crud.py` 신설 (아이템 생성, 수정, 삭제, 경로 트래버설 공격 차단 7건 전건 통과).
   - 5대 QA Swarm 및 전체 pytest 100% 통과 유지.

## OUTPUT / SCHEMA
- `src/web/templates/items.html` 고도화
- `src/web/app.py` 업데이트 (`/api/items` CRUD)
- `tests/test_web_items_crud.py`

## TEST
- `pytest tests/test_web_items_crud.py` (7 passed)
- `python -m tests.audit.audit_runner` (100점 만점 유지)

## DONE-기준
- [x] 웹 API에서 사업 아이템 생성, 수정, 삭제 동작 확인
- [x] 웹 UI 모달 폼에서 신규 아이템 등록 및 수정 연동
- [x] 보안 트래버설 차단 단위 테스트 통과
- [x] STATUS.md 및 REGISTRY.md v0.7.0 승격

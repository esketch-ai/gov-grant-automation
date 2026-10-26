---
REQ-ID: REQ-010
STATUS: QUEUED
PRIORITY: HIGH
ASSIGNEE: 박준호(총괄 아키텍트) / 최은정(보안 리드)
DEADLINE: 세션 내
DEPENDS: REQ-001, REQ-003
---

# REQ-010: 웹 관리자 대시보드 구축 (FastAPI + 관리 UI)

## INPUT
- `storage/grant_master.db` (SQLite 4테이블: announcements, rfp_chunks, site_selectors, dispatch_history)
- `items/` 폴더 내 사업 아이템 프로파일(`profile.yaml`, `proposal.md`)
- `config/master_portals.yaml`, `config/mail_config.yaml`

## PROCESSING
1. **경량 웹 서버 모듈 구축 (`src/web/`)**:
   - 프레임워크: FastAPI + Uvicorn (로컬 호스트 바인딩 `127.0.0.1:8080`).
   - 템플릿: Jinja2 기반 단일 페이지 또는 다중 탭 반응형 대시보드 (Tailwind CSS CDN 활용).
2. **핵심 관리 뷰 및 기능**:
   - **대시보드 홈 (`/`)**: 2026년도 총 수집/중복제거/적격매칭/발송 건수 KPI 위젯, 최근 공고 피드.
   - **공고 관리 (`/announcements`)**:
     - 연도별(2026년/과거) 필터, 포털별 필터, 키워드 검색.
     - 공고 상세 보기(기관명, 부처, 마감일, 원문 링크, 추출된 RFP 목록).
   - **아이템 관리 (`/items`)**:
     - 사업 아이템(`item_01_carbon_dmrv`, `item_02_voice_ai`) 프로파일 및 제안서 요약 뷰어/편집.
     - 신규 아이템 등록 및 프로파일 유효성(Pydantic) 실시간 검사.
   - **매칭 & 발송 관리 (`/matches`)**:
     - 사업 아이템별 매칭 결과 목록(TRL 적합성, 매칭 점수, 사업주 질의 OwnerInquiry 항목).
     - 원클릭 수동 재발송 및 발송 이력(dispatch_history) 조회.
   - **파이프라인 제어 (`/pipeline`)**:
     - "지금 전체 파이프라인 실행" 트리거 버튼.
     - 실시간 실행 로그 뷰어 (로그 스트리밍 또는 최근 로그 폴링).
3. **보안 및 감사 원칙 (최은정 통제)**:
   - 외부 바인딩 금지(`host="127.0.0.1"` 강제).
   - API 키 및 SMTP 비밀번호 화면 직접 노출 금지(마스킹 `********` 처리).
   - 공고문 HTML 렌더링 시 XSS escape 강제.

## OUTPUT / SCHEMA
- `src/web/app.py` (FastAPI 앱 진입점)
- `src/web/templates/` (대시보드, 공고, 아이템, 매칭 관리 HTML)
- 실행 CLI 지원: `python -m src.web.app` 또는 `python -m src.main --web`

## TEST
- `tests/test_web_admin.py`:
  1. FastAPI `TestClient`로 주요 라우트(`/`, `/announcements`, `/items`, `/matches`) 200 OK 응답 검증.
  2. 아이템 프로파일 조회 및 수정 API 동작 검증.
  3. 파이프라인 트리거 엔드포인트 비동기 동작 검증.
  4. XSS 이스케이프 및 시크릿 마스킹 보안 검증.

## DONE-기준
- [ ] `src/web/` 모듈 구현 및 템플릿 렌더링 동작 확인
- [ ] `tests/test_web_admin.py` 작성 및 통과
- [ ] 브라우저에서 `http://127.0.0.1:8080` 정상 접근 및 공고/아이템/매칭 관리 가능 확인
- [ ] `STATUS.md` 및 `REGISTRY.md` 완료 반영

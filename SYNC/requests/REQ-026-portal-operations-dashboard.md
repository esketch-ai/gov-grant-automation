# REQ-026: 각 사이트별 크롤링/접속 요건 및 실시간 헬스 관리 대시보드 구축

| 메타데이터 | 내용 |
|---|---|
| **ID** | `REQ-026` |
| **제목** | 포털 운영 관리 대시보드 (`/portals`) 및 각 사이트별 접속/인증/크롤링 현황판 |
| **담당 워크스페이스** | `QCWA` (`term_4f82f7f5-f531-4b73-8bd6-6c55e04948aa`) |
| **검증 워크스페이스** | `QQAQC` (`term_5eeca898-bbb5-429a-98e8-c10e5133661e`) |
| **우선순위** | `HIGH` (운영 가시성 및 거버넌스 핵심) |
| **연관 기능** | `REQ-010` (웹 관리자), `REQ-018` (서킷 브레이커), `master_portals.yaml` |
| **상태** | `IN PROGRESS` |

---

## 1. 개요 및 목적
G2B(나라장터), K-Startup, IRIS, NTIS 등 각 기관 포털의 크롤링 방식(OpenAPI vs Playwright vs 레거시), 접속/인증 요건(공인인증서/로그인 필수, API 키 필요, 공개 게시판), 현재 연동 상태(정상, API 키 미설정 폴백, 서킷 차단)를 한눈에 파악하고, 실시간 네트워크 핑(Ping)과 응답 지연시간을 측정할 수 있는 통합 관리자 페이지(`GET /portals`)를 구축합니다.

---

## 2. 세부 구현 요구사항

### A. 백엔드 서비스 (`src/common/portal_manager.py`)
1. **`PortalStatusService` 클래스**:
   - `config/master_portals.yaml` 로드 및 포털 메타 추출
   - 포털별 인증 요건 자동 분석:
     - `g2b`: `G2B_API_KEY` (OpenAPI) / 포털 웹은 로그인/전자서명 필수
     - `k_startup`: `DATA_GO_KR_KEY` (OpenAPI)
     - `open_web`: `TAVILLY_API_KEY` (AI 검색)
     - `playwright` 기반 보드: 패키지 설치 여부 검사
     - 일반 공개 게시판: 인증 불필요
   - 서킷 브레이커 상태(`src/common/resilience.py`) 연동
   - DB 내 포털별 2026 공고 수 집계
   - 비동기 핑(`ping_portal`, `ping_all_portals`)으로 상태코드 및 지연시간(ms) 측정

### B. 웹 라우트 및 API (`src/web/app.py`)
1. `GET /portals`: 포털 관리 웹 대시보드 렌더링 (`active_page="portals"`)
2. `GET /api/portals/status`: 전체 포털 상태 및 통계 JSON 반환
3. `POST /api/portals/ping/{portal_id}`: 단일 포털 핑 진단
4. `POST /api/portals/ping-all`: 전체 포털 일괄 핑 진단

### C. 프론트엔드 UI (`src/web/templates/portals.html`)
1. 상단 4대 관제 KPI 카드 (전체, 활성, 인증필요, 폴백/격리)
2. 포털 종합 현황 테이블 (어댑터, 인증요건 배지, 실시간 상태 배지, 지연시간, DB 공고수, 핑 테스트 버튼)
3. "접속 및 인증 가이드" (G2B 로그인 필요 사유, 공공데이터포털 키 발급 안내 등)

### D. 상단 네비게이션 (`src/web/templates/base.html`)
- 상단 네비게이션 바에 **[🌐 포털 관리]** 탭 추가

---

## 3. 검증 및 테스트 요건
1. `tests/test_web_portals_management.py` 신설
2. 기존 160개 테스트 전건 통과 유지
3. QA Swarm 140/140 만점 유지

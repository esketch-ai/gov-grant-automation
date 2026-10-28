# REQ-049: 해외 선진국 및 거점 도시(GK) 특화 유치 지원사업 디렉토리 & 포털 연동

- **요청 일시**: 2026-10-28
- **발신**: `GCWA` (총괄 아키텍트 / PM)
- **수신**: `QCWA` (개발 전담 워크스페이스: 박준호 CPO, 최은정 UI/UX, 이승엽 BM엔진, 정민재 DB, 김도윤 연동)
- **참조 및 검수**: `QQAQC` (검수 전담 워크스페이스: 한지훈)
- **우선순위**: HIGH
- **전제(Prerequisite)**: REQ-048 (기획 체계 SSOT 재정리)

---

## 1. 배경 및 목적 (for QQAQC 검수 기준)

sprint11 v2.0 상용화 후, 국내 R&D/정부과제(중기부·과기부 등) 매칭 외에 **'해외 선진국·거점도시 특화 유치 지원사업'** 수요가 발생하였다. 그러나 각 거점의 지원사업/레지던지/랜딩패드/바우처가 비정형으로 흩어져 있어, 신규/비거주 창업팀과 외국인 창업자가 한 곳에서 거점별 프로그램을 검색·비교할 수단 부재.

본 REQ-049는 5개 주요 거점(영국·프랑스·호주·UAE·대한민국)의 **거점 도시 특화 유치 지원사업 카탈로그**를 SSOT로 catalog화하고, 포털 UI 및 REST 엔드포인트에 노출하여 '국내 외 해외 유치' 트랙의 단일 정본을 수립한다.

> ※ 본 REQ는 외부 서비스 연동을 주장하지 않는다: 카탈로그는 자체 SSOT 데이터(`GLOBAL_GRANTS_CATALOG`)이며, `PortalStatusService`가 `global_grants_service`로 제공(자체 내장 구현 원칙 준수, REQ-047/048 계승).

---

## 2. 세부 개발 요구사항 (for QCWA)

### 2.1 신규 모듈 `src/common/global_grant_directory.py` (박준호 CPO / 이승엽 BM엔진)
1. **`GlobalGrantProgram` (frozen dataclass)**: 해외 거점 국가/도시별 특화 지원사업 스키마.
   - `program_id`, `country`, `country_code`, `city_hub`, `program_name(_en)`, `supervising_entity`, `operating_entity`, `specialized_fields: List[str]`, `support_type`, `priority_level`, `eligible_target`, `budget_range`, `residency/visa/mentorship` 플래그.
2. **`GLOBAL_GRANTS_CATALOG`**: 5개국/거점 35개 프로그램 정본.
   - **영국 (GB, 런던)**: DBT Global Entrepreneur Programme(GEP) 등 7개.
   - **프랑스 (FR, 파리)**: Cité/Station F 등 7개.
   - **호주 (AU, 퍼스/시드니)**: Austrade / Startup / Accelerate 등 7개.
   - **UAE (AE, 아부다비)**: Hub71 / ADGM / DIFC / G42 등 7개.
   - **대한민국 (KR, 글로벌)**: KSC / 글로벌거점 / 해외거점 / K-Startup Visa 등 7개.
3. **`GlobalGrantsService`**:
   - `get_all_programs()` : 전체 카탈로그(순서 정렬).
   - `get_summary_by_country()` : 나라별 집계(`country`, `country_code`, `city_hub`, `total`, `priority_distribution`) — 5개 키 반환.
   - `list_by_country(country, city=None)` / `get_detail(program_id)` / `search(query)` / `filter_by_priority(...)`.
   - `__post_init__` 검증: `total>0`, 우선순위/국가 분포가 카탈로그와 일치.

### 2.2 포털 연동 (김도윤 연동 / 최은정 UI/UX)
1. `config/master_portals.yaml`: +43 글로벌 포털 엔트리 (5개국/거점).
2. `src/common/master_grant_directory.py` + `src/common/portal_manager.py` → `PortalStatusService.global_grants_service` 통합.
3. `src/web/app.py`:
   - `GET /api/portals/global-grants` → `global_grants_service.get_all_programs()`
   - `GET /api/portals/global-grants/summary` → `get_summary_by_country()`
   - `/portals` 렌더 컨텍스트에 `global_programs`(전체)+`global_summary`(나라별 집계) 주입.
4. `src/web/templates/portals.html`: 글로벌 KPI 카드 + `#global-grants-panel` (거점별 프로그램, 국가/거점/우선순위 표).

---

## 3. 검수 및 Acceptance Criteria (for QQAQC - 한지훈)
1. **카탈로그 무결성**: 5개국/거점 35개 프로그램, `GLOBAL_GRANTS_CATALOG`가 frozen·검증된 데이터로 동작.
2. **포털 노출**: `GET /api/portals/global-grants` 200 + 35개, `.../summary` 나라별 5개 집계(각 7개).
3. **UI**: `/portals` 페이지에서 글로벌 패널 + KPI가 정상 렌더(템플릿 컴파일 무결성).
4. **테스트**: `tests/test_global_grants_portal.py` 5/5 pass.
5. **게이트**: pytest 전체(`267 passed`) + audit_runner(`100.0/100.0`, `APPROVED`) GREEN.
6. **영속**: REGISTRY REQ-049행 + 산 DONE 41, 본 REQ md 영속.

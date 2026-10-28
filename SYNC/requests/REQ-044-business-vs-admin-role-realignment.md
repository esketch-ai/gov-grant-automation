# REQ-044: 사업자 vs 관리자 역할 경계 완벽 분리 및 화면·메뉴 재정렬

- **요청 일시**: 2026-10-28
- **발신**: `GCWA` (총괄 아키텍트 / PM)
- **수신**: `QCWA` (개발 전담: 박준호 CPO, 최은정 UI/UX, 이승엽 BM엔진, 정민재 DB, 김도윤 포털수집)
- **참조 및 검수**: `QQAQC` (검수 전담: 한지훈)
- **우선순위**: CRITICAL (사용자 역할 경계 엇갈림 정렬 피드백)

---

## 1. 배경 및 개선 목표
사용자 지적(*"사업자와 관리자 화면이 서로 엇갈려 있는거 같다. 관리자는 플랫폼 관리 회사 임직원들을 위한 공간이고, 사업자는 자신의 사업 비지니스별 과제를 위한 공간 아닌가?"*)에 따라, 엇갈려 있던 관리자와 사업자의 화면, 메뉴, 데이터 바인딩을 완전히 올바른 위치로 재정렬한다:
1. **관리자 화면에 가 있던 `사업 아이템(/items)`을 사업자(Subscriber) 포털로 공식 이관**.
2. **사업자 화면에 가 있던 `플랫폼 통계(MRR, ARR, 활성기업수)`를 100% 삭제하고 사업주 관점 4대 수주 KPI 및 5대 BM 특화 정보 플랫폼으로 전면 재구축**.
3. **관리자 화면은 오직 플랫폼 운영사(당사) 임직원들의 관제 업무(매출, 테넌트 통제, 크롤링, 감사로그, 거버넌스)에만 집중**.

---

## 2. 세부 개발 요구사항 (for QCWA)

### 2.1 디자인 시스템 역할 포털 재정렬 (`src/web/design_system.py`) (최은정 UI/UX, 박준호 백엔드)
1. **`ROLE_PORTALS["subscriber"]["nav_items"]` (사업자 6대 메뉴)**:
   - `맞춤 대시보드` (`/dashboard/biz`)
   - `사업 아이템` (`/items`) ➔ **관리자에서 이관**
   - `기업 금고` (`/vault`)
   - `맞춤 공고` (`/announcements`)
   - `계획서 작성` (`/proposals/tailor`)
   - `도전 과제` (`/projects`)
2. **`ROLE_PORTALS["admin"]["nav_items"]` (관리자 6대 메뉴)**:
   - `총괄 플랫폼` (`/admin/platform`)
   - `거버넌스` (`/governance/partner`)
   - `포털 연동` (`/portals`)
   - `전주기 감사` (`/audit`)
   - `감사 추적` (`/admin/audit-logs`)
   - `시스템 로그` (`/logs`)
   - *(기존 `items`는 사업자로 이관 완료, `dashboard`는 운영 통계 전용으로 격리)*
3. **`_PAGE_TO_DEFAULT_ROLE` 갱신**:
   - `"items": "subscriber"`로 변경.

### 2.2 사업자 대시보드 템플릿 재구축 (`src/web/templates/biz_dashboard.html`) (최은정 UI/UX)
1. 기존 운영자 통계(MRR, ARR, 활성기업수, 순수익) 카드 100% 삭제.
2. 사업주 관점 4대 핵심 수주 KPI 카드 탑재:
   - `매칭 적합 공고` (14건), `진행 도전 과제` (2건), `최대 지원금` (최대 3.5억), `금고 서류 완성도` (85%).
3. 5대 BM(딥테크, 제조, 청년여성, 소상공인, 친환경) 인터랙티브 선택기 및 2026 공공 정책 인사이트 패널 탑재.
4. 실시간 적격 공고 레이더 + 도전 과제 수주 파이프라인 2열 레이아웃 탑재.
5. 5대 전문 파트너 1:1 직통 자문 라운지 탑재.

### 2.3 사업 아이템 템플릿 톤앤매너 전환 (`src/web/templates/items.html`) (최은정 UI/UX)
1. 상단 배너 톤을 사업자 톤(`tone-emerald`)으로 일원화.
2. 뱃지 문구: `사업자 전용 워크스페이스 &bull; 사업 아이템 관리`.

### 2.4 단위/회귀 테스트 갱신 (`tests/test_multi_specialist_10rounds.py` 외) (한지훈 QQAQC, 박준호 백엔드)
1. `test_round5_subscriber_persona_e2e_journey`에 `/items` 포함 6개 사업자 화면 검증.
2. `test_round6_admin_persona_e2e_journey`에 `/admin/platform` 포함 6개 순수 관리자 관제 화면 검증.
3. `pytest tests/ --ignore=tests/audit -q`: 250개 이상 전수 통과.
4. `python -m tests.audit.audit_runner`: 100.0/100.0 만점 (GATE APPROVED).

---

## 3. 검수 기준 (for QQAQC - 한지훈)
1. `/dashboard/biz` 내 MRR/ARR 등 운영사 통계 0건 확인.
2. 사업자 GNB에 `사업 아이템(/items)` 정상 노출 및 접근 시 `current_role == "subscriber"` 확인.
3. 관리자 GNB에 사적 사업 아이템 없이 순수 6대 관제 메뉴만 노출 확인.
4. 모든 테스트 전수 통과 및 QA Swarm 140/140 만점 확인.

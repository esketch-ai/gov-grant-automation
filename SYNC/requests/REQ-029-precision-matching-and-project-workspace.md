# REQ-029: Company Vault 자산 기반 초정밀 맞춤 매칭 & 도전 과제 프로젝트 관리 (/projects)

| 메타데이터 | 내용 |
|---|---|
| **ID** | `REQ-029` |
| **제목** | 기업 데이터룸 자산 기반 초정밀 공고 매칭 & 도전 과제 프로젝트 관리 워크스페이스 구축 |
| **총괄 조정** | `GCWA` |
| **담당 워크스페이스** | `QCWA` (`term_4f82f7f5-f531-4b73-8bd6-6c55e04948aa`) |
| **검증 워크스페이스** | `QQAQC` (`term_5eeca898-bbb5-429a-98e8-c10e5133661e`) |
| **우선순위** | `HIGH` (Phase 2 핵심 워크플로우) |
| **상태** | `DONE` (완료증 §4) |

---

## 1. 개요 및 목적
`Company Vault`(REQ-028)에 적재된 기업의 고유 자산(업력, 매출, 특허 수, 연구소 유무, 소재지, TRL)을 바탕으로 공고별 지원 자격을 100% 검증(Green/Yellow/Red)하여 초정밀 맞춤 공고를 추천합니다. 사업자가 추천 공고에서 **[🎯 도전 과제 등록]**을 클릭하면, 테넌트 전용 **도전 과제 프로젝트(`/projects`)**가 생성되어 마감일까지의 D-Day 카운트다운, 사업계획서 코파일럿 작성 진행률(0~100%), 최종 제출 패키지 다운로드를 통합 관리합니다.

---

## 2. 세부 개발 요구사항 (for QCWA)

### A. Vault 자산 기반 사전 자격 점검 바인딩 (`src/matcher/vault_preflight.py`)
1. **함수/클래스**: `VaultPreflightMatcher`
2. **동작**:
   - 테넌트의 `tenants` 테이블 정보 및 `tenant_assets`에 적재된 메타데이터를 취합하여 가상 `company_specs` 생성.
   - `PreflightService`를 실행하여 25대 지원 조건(부채비율, 세금체납, 여성/청년 대표, 연구소 보유, 특허 보유 등)을 실시간 대조.
   - 자격 미달(RED) 공고는 자동 배제하고, 우대 가점(특허 벤처 등)을 가산하여 정밀 추천 점수(Match Score) 산출.

### B. 도전 과제 프로젝트 관리 백엔드 (`src/web/app.py` & `src/common/db.py`)
1. **신규 라우트**:
   - `GET /projects`: 테넌트의 진행 중/완료된 도전 과제 프로젝트 대시보드 화면.
   - `POST /api/projects`: 공고 ID(`canonical_id`)와 템플릿 ID(`template_id`)를 받아 신규 `grant_projects` 레코드 생성.
   - `GET /api/projects`: 테넌트의 프로젝트 목록 및 각 프로젝트의 진행률, 마감 D-Day, 적용 템플릿 반환.
   - `PATCH /api/projects/{project_id}`: 프로젝트 진행 상태 및 진행률 갱신.
   - `DELETE /api/projects/{project_id}`: 프로젝트 삭제.

### C. 프로젝트 워크스페이스 웹 화면 (`src/web/templates/projects.html`)
1. **UI 레이아웃**:
   - 테넌트 헤더: 현재 도전 중인 과제 수, 평균 완성도, 긴급 마감 임박 프로젝트 KPI.
   - 프로젝트 카드 그리드:
     - 공고명, 소관 부처, 마감 D-Day 배지 (`D-5`, `D-12` 등 긴급도 색상)
     - 적용 템플릿 배지 (`K-Startup PSST` / `중기부 R&D`)
     - 작성 진행도 프로그레스 바 (0% ~ 100%)
     - 액션 버튼:
       - `[🪄 코파일럿 이어쓰기]` ➔ `/proposals/tailor?project_id=...` 로 직결
       - `[📦 제출 패키지 내보내기]`
       - `[🗑️ 프로젝트 삭제]`

---

## 3. 검증 및 테스트 요구사항 (for QQAQC)
1. **단위 테스트**: `tests/test_grant_projects_workspace.py`
   - 테넌트별 프로젝트 생성, 조회, 수정, 삭제(CRUD) 격리 검증.
   - 타 테넌트의 프로젝트가 조회되거나 수정되지 않는지 엄격한 보안 검증.
   - Vault 자산 기반 자격 사전 필터링 점검.
2. **QA Swarm 무결성 감사**:
   - `python tests/audit/audit_runner.py` 실행 시 140.0/140.0 만점 유지 확인.

---

## 4. 구현 완료증 (QQAQC 검수 완료 · 2026-10-27)

**상태**: ✅ **DONE** · **버전**: v1.5.1 · **담당**: QCWA(개발) / QQAQC(검수) / GCWA(총괄)

### 4.1 추가/변경 산출물
- `src/matcher/vault_preflight.py` (신규): `VaultPreflightMatcher` — `tenants`+`tenant_assets.parsed_metadata` 취합→가상 `company_specs`→`PreflightService` 25대 신호등 실행.
  - RED(사전탈락) 자동 제외 (`signal_light == "red"`), `bonus_points`는 리스트→개수(int)로 정규화, `final_score` 내림차순 정렬로 초정밀 추천.
  - `matched_track`/`tags`/`pass_reasons`/`disqualification_reasons`/`match_score` 산출; `canonical_id = notice.portal_id`.
  - `_notices_from_db`: `WHERE target_year=2026 ORDER BY created_at DESC` (불필요한 `year`/`priority_score` 참조 제거).
- `src/web/app.py`: `/projects` 워크스페이스 + `GET /api/vault/match`·`GET/POST /api/projects`·`PATCH/DELETE /api/projects/{id}`.
  - `POST` canonical_id 정규표현식 `[a-zA-Z0-9_\-:.]+` 방어, 존재하지 않는 공고→404, 타 테넌트→404 (격리).
  - `version` 1.5.0→1.5.1; `/api/status`의 version을 `app.version` 참조(하드코딩 1.4.0 제거→DRY).
- `src/common/db.py`: `update_grant_project` 수정 — 미정의 `_current_ts()`/존재하지 않는 `updated_at` 열 참조 제거(허용컬럼 SET만, tenant_id 스코핑 유지).
- `tests/test_grant_projects_workspace.py` (신규, 6건): matcher 단위(RED제거/정렬/bonus개수), `build_company_specs` 자산 취합, DB 테넌트 격리(CRUD), allow-list/progress 클램프, E2E(워크스페이스 렌더, CRUD, 타테넌트 차단).

### 4.2 통과 테스트
- `tests/test_grant_projects_workspace.py` **6 pass** (matcher/격리/E2E).
- 전수 `pytest tests/ --ignore=tests/audit` **193 pass / 0 fail**.
- QA Swarm `audit_runner.py` **140.0/140.0 (100.0/100.0) · GATE: APPROVED / Deploy-Ready**, 7대 검수단 전원 만점.

### 4.3 오프라인 스모크
- `TARGET_YEAR=2026 LLM_OFFLINE=1` 기준: Vault 초정밀 매칭 + `/projects` 도전과제 워크스페이스 연동 0 error.
- 다중 `TestClient` + 상이한 이메일로 2개 테넌트 분리 확인(동일 이메일→동일 테넌트).

### 4.4 degrade / 보안 확인
- **보안(적대적 공격 방어)**: `POST /api/projects` canonical_id 인JECTION/쉘 메타자(`x..;DROP`) 정적 차단→400. 타 테넌트 프로젝트의 PATCH/DELETE→404(전 경로 tenant_id 스코핑).
- **degrade**: `PreflightService` 실패 시 전 공고 `signal_light="red"`/`final_score=0` 안전 기본값(degrade)으로 회귀.
- `analyze-proposal` E2E는 기존 `tests/test_web_items_profile_integration.py::test_analyze_proposal_endpoint`가 커버(중복 테스트 미생성).

### 4.5 미검증/남은 리스크
- `/projects`는 `init` 워크플로우이며 D-Day/진행률/제출패키지는 UI(templates) 레벨만 존재 — 실제 파일 생성/다운로드는 REQ-027/030 범위.
- `tests/audit` 미집행(오프라인/속도 정책상 `--ignore`), 실 LLM Structured Output 실측 벤치마크는 별도(§3 계획).
- 모든 REQ-029 산출물은 `baee56c(v1.5.0)` 위에 **미커밋** 상태.

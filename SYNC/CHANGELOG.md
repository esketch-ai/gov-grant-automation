# CHANGELOG — 세션별 변경 로그 (완료 증빙)

> 상단=최신. `SYNC/README.md §4`에 따라 매 세션 종료 시 상단 추가.

---

## [2026-10-28] 세션 `req049-global-grants-portal` — 해외·거점도시 글로벌 유치 지원사업 디렉토리 & 포털 연동 (REQ-049)

> sprint11 상용 궤도 후속: 국내 R&D/정부과제 매칭 외 '해외 선진국·거점도시 특화 유치 지원사업' 수요를 SSOT 카탈로그로 catalog화하고 포털 UI/엔드포인트에 노출. 영속 `SYNC/requests/REQ-049-global-grants-portal.md`.

### Done — 글로벌 유치 포털 (REQ-049)
- **REQ-049 [글로벌(해외·거점) 유치 지원사업 디렉토리 & 포털]**: 신규 `src/common/global_grant_directory.py`(`GlobalGrantProgram` frozen dataclass · `GLOBAL_GRANTS_CATALOG` 5개국/거점 35개 포털 · `GlobalGrantsService.get_all_programs/get_summary_by_country`).
  - 대상 거점 5곳: **영국(런던) DBT GEP**, **프랑스(파리) City&Station F**, **호주(퍼스/시드니) Austrade/Landing Pad**, **UAE(아부다비) Hub71/ADGM**, **대한민국(글로벌) KSC/글로벌**.
  - `config/master_portals.yaml` +43 포털 엔트리, `src/common/master_grant_directory.py` + `src/common/portal_manager.py`(`PortalStatusService.global_grants_service`) 통합.
  - `src/web/app.py`: `GET /api/portals/global-grants` + `GET /api/portals/global-grants/summary`; `/portals` 렌더에 `global_programs`/`global_summary`.
  - `src/web/templates/portals.html`: 글로벌 KPI 카드 + `#global-grants-panel` (500여 라인).
  - 완료증: `tests/test_global_grants_portal.py` (5/5 pass) — 카탈로그 구조·국가/거점 집계·`portal_count` 검증.

### Verification
- pytest: `267 passed` (0 fail / 0 skip) — `tests/test_global_grants_portal.py` 5개 포함.
- audit_runner: `100.0/100.0` (Raw 140.0/140.0), `APPROVED (Deploy-Ready)`, 7/7 에이전트 20.0/20.0 — `storage/audit_report.{json,md}` fresh 2026-10-28 23:01.
- REGISTRY: REQ-049행 추가, 산 DONE 40→41.
- 2026-10-28 23:01

---

## [2026-10-28] 세션 `sprint11-v2.0-commercial` — 실전 수익형 B2B SaaS 전면 개편 & K-Horizon 2027 (REQ-032 ~ REQ-048 연착륙)

> v1.6.0 (REQ-029/030/031)에서 v2.0 상용화 궤도로의 전환. `SYNC/requests/REGISTRY.md`가 본 세션의 완료 근거 보드이며, 신규 요청문 `REQ-032`~`REQ-048` 17건이 `SYNC/requests/`에 영속됨. `docs/MASTER_PLAN_SSOT.md`로 기획 단일 정본(SSOT) 재정립.

### Done — 상용 뼈대 (REQ-032 ~ REQ-036)
- **REQ-032 [실전 수익형 B2B SaaS 대개편 v2.0]**: 먹튀방지 Blurred Paywall(블러/잠금), 1사업자 Hard-Lock(단일 사업자 계정에 1 계정), 크레딧 원장 & Top-up, 정부과제 `budget_engine.py` 예산편성기, 일할계산/부분환불 정산, 5대 BM(매칭·자산·예산·채용·법무) 대시보드, 슈퍼어드민, 해시체인 불변 감사로그.
  - 신규 모듈 `src/billing/`, `src/security/`, `src/generator/budget_engine.py`, `src/tenant/commercial_service.py`.
- **REQ-033 [60초 공감 인트로 `/intro` v4.0]**: 5막 대서사(1막 피로→2막 알림→3막 작성가이드→4막 선정확률→5막 성장길잡이·5대파트너), 프롤로그 `showreel.mp4`+`story_act1~5.jpg` 서빙(`src/web/static/`), 블러 페이월(REQ-032) 연동.
- **REQ-034/035/036 [3회차 검수 리듬]**: 1차 페르소나 UX·버튼 무결성 → 2차 페르소나 E2E·템플릿 완성도 → 3차 상용 마감·Zero-Defect. 3회차 전수 교차 검증 후 결함 0건 마감.
- **REQ-037 [K-Horizon 2027 디자인 시스템 & 3대 권한 분리]**: `src/web/design_system.py`(디자인 토큰 SSOT) + `k_horizon_2027.css` + `kh_macros.html`, 3대 권한(사업자/슈퍼어드민/운영) GNB 분리, 16개 엔드포인트 200 OK.
  - 신규 템플릿 `admin_platform.html`, `biz_dashboard.html`, `audit_logs.html`, `components/kh_macros.html`; 루트 리다이렉트 `/` → `/intro`.

### Done — UI/UX 품질 & 역할 경계 (REQ-038 ~ REQ-046)
- **REQ-038**: 상단 메뉴 군더더리(브랜딩/영문표식) 전면 퇴출, 350px 고정 제어박스, `kh-page-hero` 60px 일원화, 운영도구 관리자 격리.
- **REQ-039**: 한국어 가독성 극대화 — 초소형 폰트(10~11px) 209건 전수 퇴출(잔여 0건 검증), KRDS 기반 폰트 스케일 상향 및 고대비 명도비 확보.
- **REQ-040**: 방문자 포털 GNB 84px 오프셋 가림 방지, ScrollSpy 연동, 3대 서브 탭 해시 상태 동기화, 모바일 닫힘 처리.
- **REQ-041/042 [5회차 + 10대 전문가 전수 검수]**: 5개 라운드 자가치유(Self-Healing, DOM ID 복원·FastAPI 중복경고 0) + 기획·디자인·UIUX·백엔드·DB·BM·수집·QA 10대 다각도 교차 검수, 3대 페르소나 E2E.
- **REQ-043/044 [사업자 vs 관리자 역할 완전 분리]**: 운영자 통계 배제, 사업주 수주 KPI 4종 + 5대 BM 맞춤 인사이트, 공고 레이더 & 도전과제 파이프라인; `items` 사업자 이관, MRR/ARR 관리자 격리, 6대 사업자 과제수주 / 6대 관리자 관제 메뉴 재정렬.
- **REQ-045 [게임머니 용어 퇴출]**: '크레딧·코인'(`fa-coins` 등) 0건 퇴출 → '이번 달 생성 한도 / 월간 플랜' B2B 표준 체계.
- **REQ-046 [할루시네이션 본질 환원]**: '사업계획서 대필·작성' 영혼빼기 전수 퇴출, 본질을 '과제 요건 정밀 분석 & 매칭 진단'으로 환원, 15분 대필 과장 광고 정제.

### Done — 네이티브 엔진 & SSOT (REQ-047 ~ REQ-048)
- **REQ-047 [바이브코딩 프로토타입 검증 엔진]**: 외부 연동 아닌 `src/prototype/` 자체 내장 구현, 7:3 피드백 리워드 정산, Page Visibility 60초 체류시간, 3단계 피드백, 심사위원 보고서 뷰(`prototype_report.html`, `governance_partner.html`).
- **REQ-048 [할루시네이션 발본색원 & SSOT]**: 초안 작성/선정확률/새 계획서 영문구 0건 잔여 제로 검증, 요건 분석 가이드를 `docs/MASTER_PLAN_SSOT.md`로 단일 정본 재정립.

### 완료증 (완료된 파일 & 통과 결과)
- **신규 소스**: `src/billing/`, `src/security/`, `src/prototype/`, `src/generator/budget_engine.py`, `src/tenant/commercial_service.py`, `src/web/design_system.py`, `src/web/static/`, 템플릿 `intro/admin_platform/biz_dashboard/audit_logs/governance_partner/prototype_report.html` + `components/`.
- **신규/확장 테스트**: `tests/test_commercial_saas_v2.py`, `test_multi_specialist_10rounds.py`, `test_prototype_validation_engine.py`, `test_visitor_portal.py`, `test_zero_retention_aes256.py`, `test_web_admin.py`(루트 `/`→`/intro` 수정).
- **거버넌스 동기화**: `SYNC/requests/REGISTRY.md`(DONE 34 → 보드 갱신), 신규 요청문 REQ-032~048 17건, `docs/MASTER_PLAN_SSOT.md`.
- **보안/제어**: `.agents/`(머신 고유 스킬 symlink) `.gitignore`로 격리, `src/` 평문 시크릿 스캔 0건.

### 검증
- `pytest tests/ --ignore=tests/audit -q` → **262 passed / 0 failed (100%)**.
- `python -m tests.audit.audit_runner` → **TOTAL AUDIT SCORE 100.0/100.0 (Raw 140.0/140.0), GATE STATUS: 🟢 APPROVED (Deploy-Ready)**.
- degrade/보안: 평문 키 0 누출, `NoneType.generate_structured`(매칭), `RuntimeError("의도된 외부 연동 단절")`(정밀도) 정상 safe-degrade 확인.

---

## [2026-10-27] 세션 `sprint10-v1.6.1` — 조달청 나라장터 BidPublicInfoService 기술가이드 반영 & 마스터 총람 연동

### Done
- **조달청 나라장터 `BidPublicInfoService` Open API 기술가이드 규격 반영**:
  - `src/collector/multi_collector.py`: `_collect_g2b`에 기술가이드 필수 파라미터(`inqryDiv='1'`, `inqryBgnDt`/`inqryEndDt` 12자리 `YYYYMMDDHHMM` 1개월 제약) 준수.
  - `G2B_API_KEY` 및 공공데이터포털 통합 키 `DATA_GO_KR_KEY` 자동 fallback 연동.
  - `_safe_items`: 공공데이터포털 JSON 스키마의 `response.body.items` (배열/객체/단일항목) 안전 추출기 정밀화.
  - 첨부파일 수집: 표준 규격서(`stdNtceDocUrl`) 및 과업지시서/RFP 원본(`ntceSpecDocUrl1`~`ntceSpecDocUrl5`) 전수 추출.
  - 메타데이터 보강: 수요기관(`dminsttNm`), 배정예산(`asignBdgtAmt`), 추정가격(`presmptPrce`), 계약방식(`cntrctCnclsMthdNm`) 요약문 자동 생성.
  - `config/master_portals.yaml`: 공식 엔드포인트 `http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc` (용역) 및 연계 오퍼레이션(`getBidPblancListInfoCnstwk`, `getBidPblancListInfoThng`) 체계 확립.
- **테스트 및 거버넌스 검증**:
  - `tests/test_g2b_collector_api.py` (3건 신규 작성 및 통과).
  - 단위 테스트: **173 passed / 0 failed (100%)**.
  - QQAQC QA Swarm 전수 검사: **140.0 / 140.0 만점 (Deploy-Ready)**.

---

## [2026-10-27] 세션 `sprint9-v1.6.0` — REQ-021/022 & 카파시 헌장 & QQAQC 전수 검사 (v1.6.0)

### Done
- **REQ-021 [사업 아이템 ↔ 기업/대표자 프로필 통합 및 자동 상속]**:
  - `items/*/profile.yaml`에 `company_specs` 연동, `/items` UI 등록/수정 모달에 여성/청년/인증 폼 탑재 및 자동 상속.
  - 시뮬레이터 Preflight additive 바인딩, `tests/test_web_items_profile_integration.py` 3pass.
- **REQ-022 [사업계획서(HWP/HWPX/PDF/DOCX) 파일 업로드 기반 AI 아이템 자동 분석 및 Auto-fill]**:
  - `src/parser/proposal_parser.py`: 순수 파이썬 파서(HWPX/HWP/PDF/DOCX/TXT 무의존 추출).
  - `src/parser/proposal_extractor.py`: LLM + 한국어 정규식 안전 폴백 구조화 추출기.
  - `/api/items/analyze-proposal` 엔드포인트 및 모달 상단 드롭존 Auto-fill 탑재, `items/<id>/proposal.md` 영속화.
- **안드레이 카파시 4원칙 준수 헌장 및 하드코딩 완전 제거 (SSOT 구축)**:
  - `CLAUDE.md`, `docs/karpathy_4_principles.md` 제정.
  - `src/common/constants.py` 신설 (`YOUTH_AGE_LIMIT_GENERAL=39`, `YOUTH_AGE_LIMIT_SPECIAL=34`, `BIZ_AGE_EARLY_STAGE_YEARS=3.0`, `BIZ_AGE_GROWTH_STAGE_YEARS=7.0`, `DEFAULT_MIN_MATCH_SCORE=75` 등).
  - 미지정 성별(`NONE`/빈값) 시 여성기업 판정 100% 배제 원칙 강화, 신규 등록 모달 초기화(`resetCreateForm`) 버그 해결.
- **파이프라인 실행 가시성 및 나라장터(G2B) 딥링크 정합성 복구**:
  - 파이프라인 수동 실행 시 DB 기보관 2026 공고 자동 병합 및 결과 모달(`#pipelineResultModal`) 팝업.
  - 나라장터 공고 링크 비표준 포트 `:8081` 제거 및 차세대 나라장터 해시 딥링크(`#PNPE`) 표준화.
- **QQAQC 30년차 최고전문가단 전수 검사 완결**:
  - 13대 적대적 시나리오 100% 방어 (`storage/qqaqc_adversarial_report.md`).
  - 8대 BM × 14대 기관 공고 (112쌍) 100% 정합률 달성 (`storage/qqaqc_multi_agency_matrix_report.md`).

### 검증
- `pytest -q` → **160 passed / 0 failed in 17.10s** (100% Pass).
- `audit_runner` 실행 → **140.0/140.0 점 (100.0%, 🟢 APPROVED / Deploy-Ready)** 7대 검수단 전원 만점.

---

## [2026-10-25] 세션 `sprint7-r2` — REQ-018 (v1.3.0)

### Done
- **REQ-018 [포털 수집기 지능형 지수 백오프(Exponential Backoff) 재시도 및 서킷 브레이커 장애 복원력 강화]**:
  - `src/common/resilience.py`:
    - `retry_with_backoff`: 최대 3회 재시도, 초기 지연 0.05초, 배수 2.0, 무작위 지터(Jitter) 지원 데코레이터 구현.
    - `CircuitBreaker`: 상태 머신(`CLOSED` ➔ `OPEN` ➔ `HALF_OPEN`), 연속 3회 실패 시 빠른 격리(Fast-Fail) 및 쿨다운 후 자동 복구 엔진 구현.
    - 전역 포털별 레지스트리(`get_circuit_breaker`, `get_all_circuit_statuses`, `reset_all_circuits`) 완결.
  - `src/collector/multi_collector.py`:
    - 포털 수집 루프에 서킷 브레이커 보호 및 상태 기록 연동. 특정 포털의 통신 두절 또는 장애 발생 시 타 포털 수집을 방해하지 않고 100% 무중단 격리(Safe Degrade).
  - `src/web/app.py` & `dashboard.html`:
    - `GET /api/status`: 포털별 실시간 서킷 상태(`circuits`: `{ntis: CLOSED, iris: CLOSED, ...}`) 반환 연동.
    - 대시보드 상단에 **[포털 서킷 보호: Active (CLOSED)]** 실시간 헬스 뱃지 시각화.
- **테스트 추가 및 통합**:
  - `tests/test_resilience_circuit.py`: 6건 신설 (일시 오류 지수 백오프 자동 복구, 재시도 소진 예외 처리, 서킷 OPEN 전이, 빠른 실패 검증, HALF_OPEN 시험 복구, 수집기 서킷 격리 전건 통과).

### 검증
- `pytest -q` → **99 passed / 0 failed in 0.84s** (기존 93건 → 99건으로 확장).
- `audit_runner` 실행 → **100.0/100.0 점 (Raw 120.0/120.0, Deploy-Ready)** 6대 검수단 전원 합격 유지.

### 변경/추가 파일
```
+ src/common/resilience.py
+ tests/test_resilience_circuit.py
+ SYNC/requests/REQ-018-resilient-collector-and-circuit-breaker.md
M src/collector/multi_collector.py
M src/web/app.py
M src/web/templates/dashboard.html
M tests/test_web_admin.py
M SYNC/requests/INBOX.md
M SYNC/requests/REGISTRY.md
M STATUS.md
M SYNC/CHANGELOG.md
```

---

## [2026-10-25] 세션 `sprint7-r1` — REQ-017 (v1.2.0)

### Done
- **REQ-017 [웹 관리자 시스템 실행 로그 실시간 뷰어 및 감사 리포트 원클릭 다운로드 구축]**:
  - `src/common/logging_config.py`:
    - 표준 로깅 시스템에 `storage/app.log` 파일 핸들러(`FileHandler`, utf-8) 추가로 모든 실행 로그 실시간 파일 영속화.
  - `src/web/app.py`:
    - `GET /logs`: 시스템 실행 로그 웹 뷰 렌더링.
    - `GET /api/logs`: 최근 N줄(최대 500줄) 로그 데이터 안전 추출 및 JSON 반환 API.
    - `GET /api/audit/download/md` & `GET /api/audit/download/json`: 6대 검수단 감사 보고서 파일 다운로드(`FileResponse`) 엔드포인트 신설. 파일 부재 시 `AuditRunner().run_all()` 자동 트리거 후 서빙.
  - `src/web/templates/`:
    - `base.html`: 상단 네비게이션 바에 **[📋 시스템 로그]** 탭 추가 및 버전 `v1.2.0` 반영.
    - `logs.html`: 터미널 스타일 다크 콘솔 UI, 5초 주기 자동 새로고침 토글, 로그 레벨별(INFO, WARN, ERROR) 하이라이팅, 자동 스크롤 구현.
    - `audit.html`: 상단에 **[📄 MD 보고서]**, **[📊 JSON]** 원클릭 다운로드 버튼 연동.
- **테스트 추가 및 통합**:
  - `tests/test_web_logs_and_reports.py`: 5건 신설 (로그 뷰 HTML 렌더링, 로그 JSON API, MD 다운로드, JSON 다운로드, 비인가 포맷 400 차단 전건 통과).

### 검증
- `pytest -q` → **93 passed / 0 failed in 0.56s** (기존 88건 → 93건으로 확장).
- `audit_runner` 실행 → **100.0/100.0 점 (Raw 120.0/120.0, Deploy-Ready)** 6대 검수단 전원 합격 유지.

### 변경/추가 파일
```
+ src/web/templates/logs.html
+ tests/test_web_logs_and_reports.py
+ SYNC/requests/REQ-017-logs-viewer-and-audit-download.md
M src/common/logging_config.py
M src/web/app.py
M src/web/templates/base.html
M src/web/templates/audit.html
M SYNC/requests/INBOX.md
M SYNC/requests/REGISTRY.md
M STATUS.md
M SYNC/CHANGELOG.md
```

---

## [2026-10-25] 세션 `sprint6-r2` — REQ-008 (v1.1.0)

### Done
- **REQ-008 [경량 시맨틱 벡터 유사도 검색 엔진 및 하이브리드 스코어링 고도화]**:
  - `src/matcher/semantic_search.py`: `SemanticSearchEngine` 신설.
    - 외부 C++ 바이너리 컴파일(ChromaDB 등) 0의존, 순수 파이썬 표준 라이브러리(`math`, `re`, `collections`) 기반 TF-IDF N-Gram 및 코사인 유사도 연산 엔진 구현.
    - 한국어 R&D 불용어 및 복합 명사 유효 바이그램 형태소 분리.
    - 코사인 유사도(40%) + 공고 핵심 용어 커버리지(60%) 결합 조화 가중 평균으로 0~100점의 고신뢰도 정량 점수 산출.
    - 손상/빈 입력 시 0 Crash 및 0.0점 Safe Degrade 보증.
  - `src/matcher/hybrid_matcher.py`:
    - 3단계 하이브리드 파이프라인으로 확장: Tier 1 규칙 사전필터 -> Tier 1.5 시맨틱 벡터 유사도 -> Tier 2 LLM 심층 평가.
    - LLM 오프라인/Degrade 시에도 시맨틱 점수를 활용한 지능형 점수 보정 적용.
    - `ConditionCheckItem` 형식으로 `[시맨틱 벡터 유사도]` 검증 결과를 생성하여 Pydantic 데이터 계약 100% 무결성 유지.
  - `src/web/app.py`:
    - `POST /api/matcher/simulate`: 반환 JSON에 `semantic_score` 및 `semantic_shared_terms` 포함.
  - `src/web/templates/announcements.html`:
    - 모달 시뮬레이션 결과에 `종합 매칭 점수: X점 (시맨틱 유사도: Y점)` 실시간 시각화.
- **테스트 추가 및 통합**:
  - `tests/test_semantic_search.py`: 6건 신설 (토큰/바이그램 분리, 동일 텍스트 유사도 1.0, 무관 주제 0.0점 완전 분리, 탄소중립 주제 44.0점 고유사도 검증, 핵심 키워드 추출, 무효 입력 Safe Degrade 전건 통과).

### 검증
- `pytest -q` → **88 passed / 0 failed in 0.58s** (기존 82건 → 88건으로 확장).
- `audit_runner` 실행 → **100.0/100.0 점 (Raw 120.0/120.0, Deploy-Ready)** 6대 검수단 전원 합격 유지.

### 변경/추가 파일
```
+ src/matcher/semantic_search.py
+ tests/test_semantic_search.py
+ SYNC/requests/REQ-008-semantic-vector-search.md
M src/matcher/hybrid_matcher.py
M src/web/app.py
M src/web/templates/announcements.html
M SYNC/requests/INBOX.md
M SYNC/requests/REGISTRY.md
M STATUS.md
M SYNC/CHANGELOG.md
```

---

## [2026-10-25] 세션 `sprint6-r1` — REQ-016 (v1.0.0 마일스톤)

### Done
- **REQ-016 [웹 관리자 2026 연도별 공고 거버넌스 관리 및 QA Swarm 6대 에이전트 확장]**:
  - `src/common/db.py`:
    - `announcements` 테이블에 `target_year INTEGER DEFAULT 2026` 거버넌스 컬럼 추가(idempotent 마이그레이션).
    - `upsert_announcement`: 공고 텍스트/마감일/공고번호 기반 4자리 연도 자동 감지 및 영속화.
    - `get_year_statistics()`: 2026년도 공고 수, 과거 연도 누출 건수, 연도 거버넌스 준수율(%) 집계 메서드 신설.
    - `list_announcements(year_filter=...)`: `2026`(기본), `all`, `past`, `future` 다중 연도 필터링 쿼리 엔진 구현.
  - `src/web/app.py`:
    - `GET /announcements`: `year` 쿼리 파라미터 연동, 연도 거버넌스 지표 템플릿 전달.
    - `GET /dashboard`: 2026 연도 거버넌스 준수율 및 연도 집계 카드 연동.
    - `GET /api/stats/years`: 연도별 공고 집계 및 거버넌스 무결성 JSON API 신설.
  - `src/web/templates/announcements.html`:
    - 상단 필터 바에 [🎯 2026년도 대상 (기본) | 전체 연도 | 과거 공고 | 미래 공고] 셀렉터 및 지표 연동.
    - 각 공고 행에 `2026년` 녹색 식별 뱃지 표기.
  - `src/web/templates/dashboard.html` & `audit.html`:
    - 2026 연도 거버넌스 준수율 위젯 및 6대 검수단 카드 연동.
  - **QA Swarm 6대 검수단 확장 (`Agent-DataIntegrity`)**:
    - `tests/audit/agents/data_integrity.py`: 데이터 무결성 및 연도 거버넌스 전담 감사 에이전트 신설.
      1. 4대 테이블 스키마 및 `target_year` 컬럼 존재 검증 (5.0점).
      2. DB 내 2025년 이하 과거 공고 0건(완전 격리) 검증 (5.0점).
      3. announcements - rfp_chunks 간 고아(Orphaned) 레코드 0건 검증 (5.0점).
      4. dispatch_history 복합 유일 제약(UNIQUE) 무결성 검증 (5.0점).
    - `tests/audit/audit_runner.py`: 6대 에이전트 조율 및 정규화(100.0점 만점) 체계 완결.
- **테스트 추가 및 통합**:
  - `tests/test_year_governance_web.py`: 5건 신설 (기본 2026 필터, 전체 필터, 과거 필터, 연도 통계 API, 대시보드 KPI 렌더링).
  - `tests/test_audit_swarm.py`: 7건으로 확장 (`test_data_integrity_agent` 단위 검증 포함).

### 검증
- `pytest -q` → **82 passed / 0 failed in 0.49s** (기존 75건 → 82건으로 확장).
- `audit_runner` 실행 → **100.0/100.0 점 (Raw 120.0/120.0, Deploy-Ready)** 6대 에이전트 전원 합격.

### 변경/추가 파일
```
+ tests/test_year_governance_web.py
+ tests/audit/agents/data_integrity.py
+ SYNC/requests/REQ-016-year-governance-and-qa-swarm-v2.md
M src/common/db.py
M src/web/app.py
M src/web/templates/announcements.html
M src/web/templates/dashboard.html
M src/web/templates/audit.html
M tests/audit/agents/__init__.py
M tests/audit/audit_runner.py
M tests/test_audit_swarm.py
M tests/test_db.py
M SYNC/requests/INBOX.md
M SYNC/requests/REGISTRY.md
M STATUS.md
M SYNC/CHANGELOG.md
```

---

## [2026-10-25] 세션 `sprint5-r2` — REQ-015 (v0.9.0)

### Done
- **REQ-015 [웹 관리자 공고 상세 뷰어 및 실시간 자격 매칭 시뮬레이터 구축]**:
  - `src/web/app.py`:
    - `GET /api/announcements/{canonical_id}`: 공고 메타데이터, 마감일, 원문 URL, 수집 시각 및 연결된 `rfp_chunks` 배열을 반환하는 상세 조회 API 구현.
    - `POST /api/matcher/simulate`: 공고 canonical_id와 사업 item_id를 받아 1차 `RulePreFilter` 및 2차 `HybridMatcher`를 즉시 구동하여 적격 여부, 점수, 세부 조건 통과 상태, 역질문 목록을 반환하는 실시간 시뮬레이션 API 구현.
  - `src/web/templates/announcements.html`:
    - 공고 목록 제목 클릭 시 열리는 슬라이드/모달 상세 팝업창 연동.
    - 공고 원문 정보, RFP 청크 아코디언, 등록된 사업 아이템 선택 드롭다운 연동.
    - **[⚡ 즉시 자격 판정 시뮬레이션 실행]** 버튼 및 실시간 판정 결과(적격/부적격 배지, 점수, 사유, 체크리스트, 역질문) 시각화 카드 구현.
- **테스트 추가 및 통합**:
  - `tests/test_web_matcher_simulation.py`: 5건 신설 (공고 상세 정상 조회, 존재하지 않는 공고 404, 시뮬레이션 정상 적격 평가, 존재하지 않는 대상 404, 부적격 케이스 조기 탈락 검증 전건 통과).

### 검증
- `pytest -q` → **75 passed / 0 failed in 0.41s** (기존 70건 → 75건으로 확장).
- `audit_runner` 실행 → **100.0/100.0 점 (Deploy-Ready)** 5대 검수 에이전트 전원 합격 유지.

### 변경/추가 파일
```
+ tests/test_web_matcher_simulation.py
+ SYNC/requests/REQ-015-announcement-detail-and-match-simulation.md
M src/web/app.py
M src/web/templates/announcements.html
M SYNC/requests/INBOX.md
M SYNC/requests/REGISTRY.md
M STATUS.md
M SYNC/CHANGELOG.md
```

---

## [2026-10-25] 세션 `sprint5-r1` — REQ-004 (v0.8.0)

### Done
- **REQ-004 [하이브리드 R&D 자격 매칭 가드레일 (1차 규칙사전필터 + 2차 LLM 심층 평가)]**:
  - `src/matcher/rule_prefilter.py`: `RulePreFilter` 신설.
    - 제외 키워드, 핵심 키워드 0건 일치, 업력(3년/7년) 초과, 연구소 필수 조건 등 결정론적 조기 탈락 엔진 구현.
    - 부적격 공고에 대한 불필요한 LLM 호출 100% 차단(토큰 소모 및 비용 대폭 절감).
  - `src/matcher/hybrid_matcher.py`: `HybridMatcher` 2단계 파이프라인 신설.
    - Tier 1: `RulePreFilter` -> 미달 시 `is_eligible=False`, `match_score=0` 즉시 반환.
    - Tier 2: `EligibilityMatcher` -> 적격 후보 대상 LLM 심층 평가 및 사유 브레이크다운 결합.
  - `src/main.py`: 파이프라인 매칭 엔진을 `HybridMatcher`로 교체 통합.
- **테스트 추가 및 통합**:
  - `tests/test_hybrid_matcher.py`: 5건 신설 (제외키워드 차단, 키워드0건 차단, 업력초과 차단, 연구소부재 차단, 적격건 LLM 진입 검증 전건 통과).

### 검증
- `pytest -q` → **70 passed / 0 failed in 0.30s** (기존 65건 → 70건으로 확장).
- `audit_runner` 실행 → **100.0/100.0 점 (Deploy-Ready)** 유지.

### 변경/추가 파일
```
+ src/matcher/rule_prefilter.py
+ src/matcher/hybrid_matcher.py
+ tests/test_hybrid_matcher.py
+ SYNC/requests/REQ-004-hybrid-matching-guardrails.md
M src/main.py
M SYNC/requests/INBOX.md
M SYNC/requests/REGISTRY.md
M STATUS.md
M SYNC/CHANGELOG.md
```

---

## [2026-10-25] 세션 `sprint4-r3` — REQ-013 (v0.7.0)

### Done
- **REQ-013 [웹 관리자 대시보드 내 사업 아이템 동적 CRUD 및 실시간 프로파일 관리 구축]**:
  - `src/web/app.py`:
    - `POST /api/items`: 신규 사업 아이템 폴더, `profile.yaml`, `proposal.md` 동적 생성 API.
    - `PUT /api/items/{item_id}`: 기존 사업 아이템(이름, 키워드, 최소 점수, TRL, 수신자, 제안서) 수정 API.
    - `DELETE /api/items/{item_id}`: 사업 아이템 및 프로파일 안전 삭제 API.
    - 보안 감사(최은정 리드): `item_id`에 엄격 정규식(`^[a-zA-Z0-9_\-]+$`) 적용으로 상위 디렉터리 임의 조작(경로 트래버설 `../`) 원천 차단.
  - `src/web/templates/items.html`:
    - 상단 **[+ 신규 사업 아이템 등록]** 모달 폼 UI 연동.
    - 아이템 카드별 **[수정]** 모달 및 **[삭제]** 확인 액션 연동.
- **테스트 추가 및 통합**:
  - `tests/test_web_items_crud.py`: 7건 신설 (정상 생성, 수정, 삭제, 중복 충돌, 경로 트래버설 공격 차단 전건 통과).

### 검증
- `pytest -q` → **65 passed / 0 failed in 0.29s** (기존 58건 → 65건으로 확장).
- `audit_runner` 실행 → **100.0/100.0 점 (Deploy-Ready)** 유지.

### 변경/추가 파일
```
+ tests/test_web_items_crud.py
+ SYNC/requests/REQ-013-web-items-crud.md
M src/web/app.py
M src/web/templates/items.html
M SYNC/requests/INBOX.md
M SYNC/requests/REGISTRY.md
M STATUS.md
M SYNC/CHANGELOG.md
```

---

## [2026-10-25] 세션 `sprint4-r2` — REQ-006 (v0.6.0)

### Done
- **REQ-006 [HWPX 순수 파이썬 텍스트 추출기 및 site_selectors 자가치유 구축]**:
  - `src/parser/hwpx_extractor.py`: `HwpxExtractor` 신설.
    - 외부 바이너리(LibreOffice, hwp5txt) 0의존 순수 Python 표준 라이브러리(`zipfile` + `xml.etree.ElementTree`)로 `Contents/section*.xml` 파싱.
    - 손상/비정상 파일 입력 시 예외 격리(Safe Degrade, 0 Crash).
  - `src/parser/doc_parser.py`: `.hwpx` 파일 자동 감지 및 `HwpxExtractor` 연동.
  - `src/common/db.py`: `site_selectors` 테이블 CRUD (`get_site_selector`, `upsert_site_selector`, `list_site_selectors`) 구현으로 포털 크롤링 셀렉터 자가치유 및 캐싱 인프라 완결.
- **테스트 추가 및 통합**:
  - `tests/test_hwpx_parser.py`: 4건 신설 (유효 HWPX 추출, 손상 파일 격리, 복수 RFP 분할, 셀렉터 CRUD 및 멱등 갱신 전건 통과).

### 검증
- `pytest -q` → **58 passed / 0 failed in 0.27s** (기존 54건 → 58건으로 확장).
- `audit_runner` 실행 → **100.0/100.0 점 (Deploy-Ready)** 유지.

### 변경/추가 파일
```
+ src/parser/hwpx_extractor.py
+ tests/test_hwpx_parser.py
+ SYNC/requests/REQ-006-hwpx-parser-and-self-healing-selectors.md
M src/parser/doc_parser.py
M src/common/db.py
M SYNC/requests/INBOX.md
M SYNC/requests/REGISTRY.md
M STATUS.md
M SYNC/CHANGELOG.md
```

---

## [2026-10-25] 세션 `sprint4-r1` — REQ-007 (v0.5.0)

### Done
- **REQ-007 [비동기 백그라운드 자동 스케줄러 구축 및 웹 제어 연동]**:
  - `src/common/scheduler.py`: `AsyncScheduler` 클래스 신설.
    - asyncio 기반 주기적(기본 30분=1800초) 파이프라인 자동 실행.
    - 실행 중복 방지(`_is_executing` 락) 및 Safe Degrade 장애 격리.
    - 상태 메트릭(`enabled`, `interval_seconds`, `last_run_at`, `next_run_at`, `run_count`, `last_result`).
  - `src/web/app.py`:
    - `GET /api/scheduler/status`: 스케줄러 실시간 가동 상태 조회 API.
    - `POST /api/scheduler/toggle`: 원클릭 활성화/비활성화 토글 API.
    - `GET /api/status`: 전체 시스템 상태 JSON에 `scheduler` 메타 필드 연동.
  - `src/web/templates/dashboard.html`: 상단 요약 배너에 스케줄러 가동 배지 및 원클릭 토글 스위치 UI 연동.
- **테스트 추가 및 통합**:
  - `tests/test_scheduler.py`: 6건 신설 (초기화, 즉시 트리거, 중복 락, 토글, 에러 격리, 주기 루프 전건 통과).
  - `tests/test_web_admin.py`: 스케줄러 API 엔드포인트 검증 추가 (10건 통과).
  - `tests/audit/agents/web_qa.py`: 감사 매트릭스에 `/api/scheduler/status` 검증 추가.

### 검증
- `pytest -q` → **54 passed / 0 failed in 0.28s** (기존 47건 → 54건으로 확장).
- `audit_runner` 실행 → **100.0/100.0 점 (Deploy-Ready)** 유지.

### 변경/추가 파일
```
+ src/common/scheduler.py
+ tests/test_scheduler.py
+ SYNC/requests/REQ-007-scheduler-and-worker.md
M src/web/app.py
M src/web/templates/dashboard.html
M tests/test_web_admin.py
M tests/audit/agents/web_qa.py
M SYNC/requests/INBOX.md
M SYNC/requests/REGISTRY.md
M STATUS.md
M SYNC/CHANGELOG.md
```

---

## [2026-10-25] 세션 `sprint3-r3` — REQ-012 (v0.4.1)

### Done
- **REQ-012 [웹 관리자 QA Swarm 검수 시각화 및 원클릭 감사 연동]**:
  - `src/web/templates/audit.html`: 5대 검수 에이전트의 종합 감사 점수(100.0/100.0), 게이트 판정 배지(🟢 APPROVED), 에이전트별 세부 로그 및 메트릭 카드 UI 구축.
  - `src/web/templates/base.html`: 상단 네비게이션에 `품질 검수 (/audit)` 메뉴 추가.
  - `src/web/templates/dashboard.html`: 상단 요약 배너에 QA 스웜 감사 상태 및 점수 링크 연동.
  - `src/web/app.py`:
    - `GET /audit`: 감사 리포트 페이지 뷰어 렌더링.
    - `POST /api/audit/run`: 웹에서 비동기로 `AuditRunner().run_all()` 즉시 실행 및 화면 갱신 API.
    - `GET /api/status`: QA Swarm 메타 필드(`qa_swarm: {total_score, status, all_passed}`) 연동.
- **테스트 추가 및 통합**:
  - `tests/test_web_admin.py`: `/audit` 뷰, `POST /api/audit/run`, `/api/status` 검증 (총 9건 전건 통과).
  - `tests/audit/agents/web_qa.py`: 감사 매트릭스에 `/audit` 검증 추가.

### 검증
- `pytest -q` → **47 passed / 0 failed in 0.25s** (기존 45건 → 47건으로 확장).
- `audit_runner` 실행 → **100.0/100.0 점 전원 PASS**.

### 변경/추가 파일
```
+ src/web/templates/audit.html
+ SYNC/requests/REQ-012-web-qa-dashboard-integration.md
M src/web/app.py
M src/web/templates/base.html
M src/web/templates/dashboard.html
M tests/test_web_admin.py
M tests/audit/agents/web_qa.py
M SYNC/requests/INBOX.md
M SYNC/requests/REGISTRY.md
M STATUS.md
M SYNC/CHANGELOG.md
```

---

## [2026-10-25] 세션 `sprint3-r2` — REQ-011 (v0.4.0)

### Done
- **REQ-011 [다각도 테스트 검수 에이전트(QA Swarm) 프레임워크 구축]**:
  - `tests/audit/base.py`: 검수 에이전트 베이스 클래스(`BaseAuditAgent`) 및 감사 결과 스키마(`AuditResult`).
  - `tests/audit/agents/year_audit.py`: `Agent-YearAudit` (2026년도 대상 전용 필터링 무결성, 과거 공고 유입 잔존율 0% 전수 검증).
  - `tests/audit/agents/web_qa.py`: `Agent-WebQA` (FastAPI 웹 관리자 전 엔드포인트 200 OK 렌더링, 파이프라인 비동기 수동 트리거 E2E 검증).
  - `tests/audit/agents/matcher_precision.py`: `Agent-MatcherPrecision` (업력 초과·도메인 불일치 스트레스 테스트, False Positive 0건, 사유 브레이크다운 검증).
  - `tests/audit/agents/security_gate.py`: `Agent-SecurityGate` (정적 시크릿 스캔 누출 0건, HTML XSS 페이로드 자동 이스케이프, `127.0.0.1` 로컬 바인딩 감사).
  - `tests/audit/agents/resilience.py`: `Agent-Resilience` (손상된 텍스트/바이너리 입력, DB 장애 모의, 발송 누락 시 0 Crash 및 Safe Degrade 지속성 검증).
  - `tests/audit/audit_runner.py`: 5대 에이전트 오케스트레이터, 종합 감사 리포트 자동 발간 (`storage/audit_report.json`, `storage/audit_report.md`).
- **테스트 추가 및 통합**:
  - `tests/test_audit_swarm.py`: 6개 테스트 추가 (5대 에이전트 단독 + 오케스트레이터 E2E 전건 통과).
  - `python -m tests.audit.audit_runner`: 단일 명령 종합 감사 스코어 **100.0 / 100.0 점** 및 **APPROVED (Deploy-Ready)** 달성.

### 검증
- `pytest -q` → **45 passed / 0 failed in 0.20s** (기존 39건 → 45건으로 확장).
- `audit_runner` 실행 → **100.0/100.0 점 전원 PASS**.

### 변경/추가 파일
```
+ tests/audit/__init__.py
+ tests/audit/base.py
+ tests/audit/audit_runner.py
+ tests/audit/agents/__init__.py
+ tests/audit/agents/year_audit.py
+ tests/audit/agents/web_qa.py
+ tests/audit/agents/matcher_precision.py
+ tests/audit/agents/security_gate.py
+ tests/audit/agents/resilience.py
+ tests/test_audit_swarm.py
+ storage/audit_report.json
+ storage/audit_report.md
M SYNC/requests/REQ-011-multi-agent-qa-swarm.md
M SYNC/requests/REGISTRY.md
M STATUS.md
M SYNC/CHANGELOG.md
```

---

## [2026-10-25] 세션 `sprint3-r1` — REQ-010 (v0.3.0)

### Done
- **REQ-010 [웹 관리자 대시보드 구축]**:
  - `src/web/app.py`: FastAPI + Uvicorn 기반 로컬 웹 서버(`127.0.0.1:8080`) 구축.
  - `src/web/templates/`: `base.html`, `dashboard.html`, `announcements.html`, `items.html`, `matches.html` 반응형 모던 Tailwind UI 구축.
  - 2026년도 공고 현황 및 KPI 카드, 사업 아이템 프로파일 열람, 발송 이력(dispatch_history) 조회, 원클릭 파이프라인 수동 실행(`/api/pipeline/run`), 상태 API(`/api/status`).
  - 보안 통제(최은정 감사): `127.0.0.1` 로컬 바인딩 강제, 시크릿 정보 마스킹, Jinja2 자동 HTML XSS 이스케이프.
  - `src/main.py --web` 플래그 지원 (원클릭 웹 서버 기동).
- **테스트 추가**: `tests/test_web_admin.py` (7건 전건 통과).

### 검증
- `pytest -q` → **39 passed / 0 failed** (기존 32건 → 39건으로 확장).
- `LLM_OFFLINE=1 python -m src.main .` 스모크 0 err 확인.

### 변경/추가 파일
```
+ src/web/__init__.py
+ src/web/app.py
+ src/web/templates/base.html
+ src/web/templates/dashboard.html
+ src/web/templates/announcements.html
+ src/web/templates/items.html
+ src/web/templates/matches.html
+ tests/test_web_admin.py
M src/main.py
M requirements.txt
M STATUS.md
M SYNC/requests/REGISTRY.md
M SYNC/CHANGELOG.md
```

---

## [2026-10-25] 세션 `sprint2-r1` — REQ-003, REQ-005, REQ-009 (v0.2.0)

### Done
- **REQ-003 [SQLite DB 영속화]**: `src/common/db.py` 신설 (`announcements`, `rfp_chunks`, `dispatch_history` 멱등 upsert 및 안전 degrade).
- **REQ-009 [2026년도 전용 필터링]**: `src/collector/year_filter.py` 및 `config/year_filter.yaml` 신설 (최신 연도 2026 미만 100% 드롭, 연도 미기재 드롭).
- **REQ-005 [중복발송 방지]**: `is_dispatched` 및 `record_dispatch` 이중 안전장치로 동일 item/canonical_id/rfp_id 재발송 0건 차단.
- **오케스트레이터 통합**: `src/main.py`에 YearFilter 및 DB 영속화/중복발송 방지 파이프라인 통합.
- **테스트 추가**: `tests/test_db.py` (4건), `tests/test_year_filter.py` (8건), `tests/test_pipeline_integration.py` (1건 E2E).

### 검증
- `pytest -q` → **32 passed / 0 failed** (기존 19건 → 32건으로 확장).
- `TARGET_YEAR=2026 LLM_OFFLINE=1 python -m src.main .` → 2아이템 처리·**0 error**·연도게이트+DB영속화+중복발송방지 E2E 통과.

### 변경/추가 파일
```
+ config/year_filter.yaml
+ src/collector/year_filter.py
+ src/common/db.py
+ tests/test_db.py
+ tests/test_year_filter.py
+ tests/test_pipeline_integration.py
M src/main.py
M STATUS.md
M SYNC/requests/REGISTRY.md
M SYNC/CHANGELOG.md
```

---

## [2026-10-25] 세션 `init-r1` — REQ-001 (v0.1.0)

### Done
- 프로젝트 스캐폴딩(`bootstrap_project.py`): 디렉터리·config·items 2종·SQLite(4테이블) 생성
- 5대 파이프라인 보일러플레이트 완결: `collector`(5어댑터+오픈웹), `deduplicator`, `parser`, `matcher`, `notifier`
- 로컬 Ollama 우선 LLM 어댑터: `src/common/llm/{base,ollama_client,cloud_client,schemas_helpers}.py` + `build_llm_client()`
- 교수급 6인 팀 + Task Packet + 품질게이트: `TEAM.md` + `opencode/agents/*`(6개)
- 테스트/설정: `tests/*`(5, 19건), `requirements.txt`, `pyproject.toml`, `pytest.ini`, `.env.example`, `.gitignore`
- 보고/소통/현황관리 레이어: `STATUS.md`, `SYNC/**`(README/INBOX/REGISTRY/REQ-001/CHANGELOG/_TEMPLATE)

### 검증
- `pytest -q` → **19 passed / 0 failed**
- `LLM_OFFLINE=1 python -m src.main .` → 2아이템 처리·**0 error**·모든 미설정(키·Playwright·HWP) safe degrade

### 변경/추가 파일
```
+ STATUS.md
+ SYNC/README.md
+ SYNC/requests/INBOX.md
+ SYNC/requests/REGISTRY.md
+ SYNC/requests/REQ-001-scaffold-and-5modules.md
+ SYNC/requests/CHANGELOG.md   (this file)
+ SYNC/requests/_TEMPLATE.md
+ bootstrap_project.py
+ src/common/llm/*.py  (base/ollama/cloud/schemas_helpers/__init__)
+ src/collector/multi_collector.py
+ src/deduplicator/dedup.py
+ src/parser/doc_parser.py
+ src/matcher/eligibility_matcher.py
+ src/notifier/email_notifier.py
+ src/main.py
+ opencode/agents/*.md  (6인)
+ TEAM.md
+ tests/*.py  (5)
+ requirements.txt / pyproject.toml / pytest.ini / .env.example / .gitignore
+ config/master_portals.yaml  config/mail_config.yaml
+ items/item_01_carbon_dmrv/*  items/item_02_voice_ai/*
+ storage/grant_master.db  (4테이블: announcements/rfp_chunks/site_selectors/dispatch_history)
```

### 미완료 · 다음 라운드 대기 (REQ-002~008)
- 실 API 연동(DEC-01 키 주입), DB 쓰기 연결, Structured Output 튜닝, 중복발송 방지, HWP/셀렉터, cron.
- 상세는 `STATUS.md §2/§4/§5` 및 `SYNC/requests/REGISTRY.md`.

### 의사결정 필요 (→ Gemini)
- DEC-01 실 키·앱비밀 주입 · DEC-02 HWP 파싱 전략 · DEC-03 로컬 최종 모델 · DEC-04 셀렉터 자기치유 시점.

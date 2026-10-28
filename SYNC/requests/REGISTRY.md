# REGISTRY — 요청 현황 관리 보드

> **이건 무엇인가**: 모든 REQ의 상태/담당/완료증/블록을 한눈에 추적하는 보드.
> Gemini는 이 보드로 요청 진행도를 확인하고, 실무는 DONE 처리 시 이를 갱신한다(README §3).
> 상태: `DRAFT→QUEUED→IN PROGRESS→REVIEW→DONE / BLOCKED`.

## 보드 (상태별)

| REQ | 제목 | 담당 | 상태 | 우선도 | 전제 | 완료증 | 완료일 |
|---|---|---|---|---|---|---|---|
| **REQ-001** | 스캐폴딩+5모듈+LLM+테스트+팀 | 박준호+5인 | ✅ **DONE** | HIGH | 없음 | pytest 19pass, `LLM_OFFLINE=1` 스모크 0err | 2026-10-25 |
| REQ-002 | 실 API 연동 E2E | 김도윤 | ⏸ DRAFT(대기) | HIGH | DEC-01(키) | — | — |
| **REQ-003** | DB 쓰기 연결(collect→dispatch) | 박준호/정민재 | ✅ **DONE** | HIGH | 없음 | `tests/test_db.py` (4pass), announcements/rfp/dispatch DB 연동 | 2026-10-25 |
| **REQ-004** | 하이브리드 R&D 자격 매칭 가드레일 | 이승엽/박준호 | ✅ **DONE** | HIGH | REQ-001,003,011 | `tests/test_hybrid_matcher.py` (5pass), 1차 규칙사전필터 + 2차 LLM 통합 | 2026-10-25 |
| **REQ-005** | 중복발송 방지(dispatch_history) | 최은정 | ✅ **DONE** | MEDIUM | REQ-003 | `test_pipeline_integration.py` 2회차 0건 발송 검증 | 2026-10-25 |
| **REQ-006** | HWPX 순수 파서 및 셀렉터 자기치유 | 정민재/박준호 | ✅ **DONE** | HIGH | REQ-001,003 | `tests/test_hwpx_parser.py` (4pass), HWPX 추출기 및 site_selectors 연동 | 2026-10-25 |
| **REQ-007** | 일일 자동 스케줄러 및 백그라운드 워커 | 박준호/정민재/최은정 | ✅ **DONE** | HIGH | REQ-001,003,010 | `tests/test_scheduler.py` (6pass), `src/common/scheduler.py` 및 웹 제어 연동 | 2026-10-25 |
| **REQ-008** | 경량 시맨틱 벡터 유사도 검색 엔진 및 하이브리드 스코어링 | 이승엽/박준호/한지훈 | ✅ **DONE** | HIGH | REQ-004,015,016 | `tests/test_semantic_search.py` (6pass), TF-IDF/코사인 유사도 및 시뮬레이터 연동 | 2026-10-25 |
| **REQ-009** | 2026년도 전용 필터링 및 과거공고 차단 | 김도윤/정민재 | ✅ **DONE** | HIGH | REQ-001 | `tests/test_year_filter.py` (8pass), 2025 이하 100% 차단 | 2026-10-25 |
| **REQ-010** | 웹 관리자 대시보드 구축(FastAPI UI) | 박준호/최은정 | ✅ **DONE** | HIGH | REQ-001,003 | `tests/test_web_admin.py` (7pass), 대시보드/공고/아이템/발송 UI 구축 | 2026-10-25 |
| **REQ-011** | 다각도 테스트 검수 에이전트(QA Swarm) | 한지훈+5인 | ✅ **DONE** | HIGH | REQ-009,010 | `tests/test_audit_swarm.py` (6pass), `audit_runner` 100점 만점 발간 | 2026-10-25 |
| **REQ-012** | 웹 관리자 QA Swarm 시각화/원클릭 감사 | 박준호/한지훈/최은정 | ✅ **DONE** | HIGH | REQ-010,011 | `tests/test_web_admin.py` (9pass), `/audit` 뷰 및 `/api/audit/run` 구축 | 2026-10-25 |
| **REQ-013** | 웹 관리자 사업 아이템 동적 CRUD | 박준호/최은정/한지훈 | ✅ **DONE** | HIGH | REQ-010,012 | `tests/test_web_items_crud.py` (7pass), `/api/items` 및 UI 모달 연동 | 2026-10-25 |
| **REQ-015** | 웹 관리자 공고 상세 및 매칭 시뮬레이터 | 박준호/이승엽/한지훈 | ✅ **DONE** | HIGH | REQ-004,010,013 | `tests/test_web_matcher_simulation.py` (5pass), `/api/matcher/simulate` 및 모달 UI 연동 | 2026-10-25 |
| **REQ-016** | 2026 연도 거버넌스 웹 관리 및 QA Swarm 6대 에이전트 확장 | 박준호/김도윤/한지훈/최은정 | ✅ **DONE** | HIGH | REQ-009,010,011,015 | `tests/test_year_governance_web.py` (5pass), 연도필터/대시보드KPI 및 `Agent-DataIntegrity` 연동 | 2026-10-25 |
| **REQ-017** | 웹 관리자 시스템 실행 로그 실시간 뷰어 및 감사 리포트 다운로드 | 박준호/최은정/한지훈 | ✅ **DONE** | HIGH | REQ-010,011,012,016 | `tests/test_web_logs_and_reports.py` (5pass), `/logs`, `/api/logs`, `/api/audit/download/*` 연동 | 2026-10-25 |
| **REQ-018** | 포털 수집기 지수 백오프 재시도 및 서킷 브레이커 장애 복원력 | 김도윤/정민재/박준호/한지훈 | ✅ **DONE** | HIGH | REQ-001,009,011,016 | `tests/test_resilience_circuit.py` (6pass), `src/common/resilience.py` 및 포털 격리/헬스체크 | 2026-10-25 |
| **REQ-019** | 공고 마감일 D-Day 카운트다운 및 표준 iCalendar(.ics) 내보내기 | 이승엽/정민재/최은정/박준호/한지훈 | ✅ **DONE** | HIGH | REQ-010,016,018 | `tests/test_deadline_calendar.py` (5pass), `src/common/deadline.py`, `ical_exporter.py` 및 캘린더 피드 | 2026-10-25 |
| **REQ-020** | 다차원 매칭 및 25대 조건 사전 비행점검 웹 관리자 전면 연동 | 박준호/이승엽/최은정/한지훈 | ✅ **DONE** | HIGH | REQ-010,015,019 | `tests/test_web_profile_preflight.py` (5pass), 프로필CRUD, 4대 다차원 탭, 🚥신호등 비행점검 UI 연동, QA Swarm 140/140 만점 | 2026-10-26 |
| **REQ-021** | 사업 아이템 ↔ 기업/대표자 프로필 통합 및 자동 상속 | 박준호/이승엽/최은정/한지훈 | ✅ **DONE** | HIGH | REQ-013,020 | `items/*/profile.yaml`에 `company_specs` 연동, `/items` UI 등록/수정 모달에 여성/청년/인증 폼 탑재 및 자동상속, 시뮬레이터 Preflight additive 바인딩, `tests/test_web_items_profile_integration.py` 3pass | 2026-10-27 |
| **REQ-022** | 사업계획서(HWP/PDF/DOCX) 파일 업로드 기반 AI 아이템 자동 분석 및 Auto-fill | 박준호/정민재/이승엽/최은정 | ✅ **DONE** | HIGH | REQ-021 | HWP/PDF/DOCX 텍스트 파서(`ProposalParser`), LLM 정형 JSON 추출기(`ProposalExtractor`), `/api/items/analyze-proposal` 엔드포인트 및 모달 드롭존 Auto-fill UI 탑재, `tests/test_proposal_parser_and_extractor.py` 4pass | 2026-10-27 |
| **REQ-026** | 포털 운영 관리 대시보드 및 사이트별 접속/인증/크롤링 현황판 | 박준호/김도윤/최은정 | ✅ **DONE** | HIGH | REQ-010,018 | `src/common/portal_manager.py`, `/portals`, `/api/portals/*`, 실시간 핑 및 인증 가이드, `tests/test_web_portals_management.py` 5pass | 2026-10-27 |
| **REQ-027** | DocuMorph AI - 사업계획서 맞춤 변환 스튜디오 및 반자동 코파일럿 | GCWA/QCWA/QQAQC | ✅ **DONE** | HIGH | REQ-022 | PSST/R&D 8문항 템플릿, 3단계 갭 분석 엔진, 개조식/수치 본문 합성 코파일럿, `/proposals/tailor` 스플릿 뷰 웹 UI, `tests/test_proposal_tailor_generator.py` 4pass | 2026-10-27 |
| **REQ-028** | 상용 B2B 멀티테넌트 SaaS 및 Company Vault (기업 지식 데이터 룸 & 소셜 로그인) | GCWA/QCWA/QQAQC | ✅ **DONE** | HIGH | REQ-027 | `tenants`/`users`/`tenant_assets` DB 완전 격리, 카카오/구글 소셜 세션, 4대 자산(계획서/IR덱/재무/특허) 데이터룸 UI(`/vault`), `tests/test_tenant_vault.py` 4pass | 2026-10-27 |
| **REQ-029** | Company Vault 자산 기반 초정밀 맞춤 매칭 & 도전 과제 프로젝트 관리 (/projects) | GCWA/QCWA/QQAQC | ✅ **DONE** | HIGH | REQ-028 | `VaultPreflightMatcher`(`tenants`+`tenant_assets` 파싱 자산→가상 company_specs→`PreflightService` 25대 신호등), RED(사전탈락) 자동제거 + `final_score` 정렬 초정밀 추천, `/projects`·`grant_projects` 도전과제 생성/트래킹(D-Day/진행률), `tests/test_grant_projects_workspace.py` 6pass | 2026-10-27 |
| **REQ-030** | Zero-File-Retention 무보관 원칙, 테넌트 분리형 AES-256-GCM 암호화 보관 및 TLS 1.2+ 전송 보안 | GCWA/QCWA/QQAQC | ✅ **DONE** | CRITICAL | REQ-028 | `src/security/encryption.py` `VaultCryptoManager`(HKDF-SHA256 32B 테넌트키 + `AESENC::`센티넬 AES-GCM; 서비스레이어 인가/복호, raw 경로 추가), `tenants.tenant_salt`(COALESCE preserve)+보안헤더 미들웨어(HSTS/nosniff/DENY/XSS/Referrer) 5종, `tests/test_zero_retention_aes256.py` 9test; `202pass`+QA`140/140`(완료증 §4) | 2026-10-27 |
| **REQ-031** | 대한민국 디지털정부 표준 UI/UX(KRDS) 가이드라인 준수 및 24+ 디자인 시스템 전면 적용 | GCWA/QCWA/QQAQC | ✅ **DONE** | HIGH | REQ-029 | `base.html`에 KRDS 24개 공용 모듈(토큰/GOV배너/포커스링/Bento/Carousel/Dropzone/Toast 등)+공용JS, 4페이지 additive 클래스 주입, `193pass`+QA`140/140`(완료증 §5) | 2026-10-27 |
| **REQ-032** | 실전 수익형 B2B SaaS 대개편 v2.0 (블러페이월, 크레딧원장/Top-up, HWPX/예산엔진, 일할/환불정산, 5대 BM 대시보드, 슈퍼어드민, 해시체인 감사로그) | GCWA/QCWA/QQAQC | ✅ **DONE** | CRITICAL | REQ-030,031 | 먹튀방지 Blurred Paywall, 1사업자 Hard-Lock, 크레딧 원장, 정부과제 예산편성기, 일할계산/부분환불, 해시체인 불변 감사로그 | 2026-10-28 |
| **REQ-033** | 60초 공감 인트로(`/intro`) v4.0 — 5막 대서사(1막 피로→2막 알림→3막 작성가이드→4막 선정→5막 성장길잡이·전문가네트워크·사업운) | GCWA/QCWA/QQAQC | ✅ **DONE** | CRITICAL | REQ-031,032 | 프롤로그 `intro_showreel.mp4` + `story_act1~5.jpg`, 제5막 성장로2/3단+5대파트너(회계·마케팅·광고·투자사·법률)+클로징철학, `/static` 서빙, 블레어 페이월(REQ-032) | 2026-10-28 |
| **REQ-037** | Google Stitch 기반 K-Horizon 2027 디자인 시스템 및 3대 권한 분리 | GCWA/QCWA/QQAQC | ✅ **DONE** | HIGH | REQ-032,033 | 3대 권한 분리 GNB, 디자인 토큰 SSOT(`design_system.py`, `k_horizon_2027.css`), 16개 엔드포인트 200 OK | 2026-10-28 |
| **REQ-038** | 상단 메뉴 분리 및 텍스트 군더더기 전면 정제, kh-page-hero 픽셀 칼정렬 및 운영도구 관리자 격리 | GCWA/QCWA/QQAQC | ✅ **DONE** | CRITICAL | REQ-037 | 군더더기 브랜딩/영문표식 제거, 350px 고정 제어박스, kh-page-hero 60px 일원화, 운영도구 격리, pytest 226pass, QA 140/140 APPROVED | 2026-10-28 |
| **REQ-039** | 한국어 가독성 극대화 및 초소형 폰트(10~11px) 전면 퇴출·폰트 스케일 고도화 | GCWA/QCWA/QQAQC | ✅ **DONE** | HIGH | REQ-038 | 초소형(10~11px) 폰트 209건 전수 퇴출(0건 검증), KRDS 기반 폰트 스케일 상향, 고대비 명도비 확보, pytest 234pass, QA 140/140 만점 | 2026-10-28 |
| **REQ-040** | 방문자 포털 서브 메뉴 및 3대 탭 동작 무결성 고도화 (헤더 가림 방지·스크롤스파이·탭 상태 동기화) | GCWA/QCWA/QQAQC | ✅ **DONE** | HIGH | REQ-039 | GNB 84px 오프셋 안착, ScrollSpy 연동, 3대 서브 탭 해시 동기화, 모바일 닫힘 처리, pytest 239pass, QA 140/140 만점 | 2026-10-28 |
| **REQ-041** | 5회차 반복 전수 검수 프로토콜 및 자가 치유(Self-Healing) 결함 수정 | GCWA/QCWA/QQAQC | ✅ **DONE** | CRITICAL | REQ-040 | 5개 라운드 전원 검수, DOM ID 복원(simNote/simChecks/verify-result), FastAPI 중복경고 0건, pytest 241pass, QA 140/140 만점 | 2026-10-28 |
| **REQ-042** | 10대 다각도 전문가별 전수 검사 및 교차 검증 프로토콜 | GCWA/QCWA/QQAQC | ✅ **DONE** | CRITICAL | REQ-041 | 기획·디자인·UIUX·백엔드·DB·BM·수집·QA 전원 10대 다각도 검수, 3대 페르소나 E2E, pytest 251pass, QA 140/140 만점 | 2026-10-28 |
| **REQ-043** | 사업자 전용 워크스페이스 고객 중심 전면 개편 및 가치·정보 플랫폼 서비스 구축 | GCWA/QCWA/QQAQC | ✅ **DONE** | CRITICAL | REQ-042 | 운영자 통계 배제, 사업주 수주 KPI 4종, 5대 BM 맞춤 인사이트, 공고 레이더 & 도전과제 파이프라인 | 2026-10-28 |
| **REQ-044** | 사업자 vs 관리자 역할 경계 완벽 분리 및 화면·메뉴 재정렬 | GCWA/QCWA/QQAQC | ✅ **DONE** | CRITICAL | REQ-043 | items 사업자 이관, MRR/ARR 관리자 격리, 6대 사업자 과제수주 메뉴 & 6대 관리자 관제 메뉴 재정렬, pytest 251pass, QA 140/140 | 2026-10-28 |
| **REQ-045** | 게임 머니식 '크레딧·코인' 용어 전면 퇴출 및 '월간 플랜 생성 한도' 체계 개편 | GCWA/QCWA/QQAQC | ✅ **DONE** | CRITICAL | REQ-044 | 템플릿 fa-coins/크레딧 0건 퇴출, 이번 달 생성 한도/플랜 관리 정제, B2B 표준화, pytest 251pass, QA 140/140 | 2026-10-28 |
| **REQ-046** | '사업계획서 대필·작성' 할루시네이션 전면 퇴출 및 '과제 요건 정밀 분석 & 매칭 진단' 본질 환원 | GCWA/QCWA/QQAQC | ✅ **DONE** | CRITICAL | REQ-045 | 새 계획서 작성 퇴출, 맞춤 공고 탐색 CTA 전환, 15분 대필 과장 광고 정제, 공고 요건 분석 일원화, pytest 251pass, QA 140/140 | 2026-10-28 |
| **REQ-048** | 잔여 할루시네이션 발본색원 전수 정제 및 기획 체계 단일 정본(SSOT) 재정리 | GCWA/QCWA/QQAQC | ✅ **DONE** | CRITICAL | REQ-046 | 초안 작성/선정 확률/새 계획서 0건 발본색원, 요건 분석 가이드 SSOT 일원화, pytest 251pass, QA 140/140 | 2026-10-28 |
| **REQ-047** | 바이브코딩 프로토타입 검증 엔진 및 7:3 피드백 리워드 경제 네이티브 구현 | GCWA/QCWA/QQAQC | ✅ **DONE** | CRITICAL | REQ-048 | SSHAI-BOOM 외부연동 아닌 자체 내장 구현, 7:3 리워드 정산, Page Visibility 60초 체류시간, 3단계 피드백, 심사위원 보고서 뷰 | 2026-10-28 |
| **REQ-049** | 해외 선진국 및 거점 도시(GK) 특화 지원사업 디렉토리 & 포털 연동 | GCWA/QCWA/QQAQC | ✅ **DONE** | HIGH | REQ-048 | 글로벌 카탈로그 `global_grant_directory.py`·`GLOBAL_GRANTS_CATALOG` 5개국/거점(영국 DBT GEP·프랑스 Cité/Station F·호주 Austrade/Landing Pad·UAE Hub71·대한민국 KSC) 35개 포털(yaml+43), `/api/portals/global-grants`+`/summary` & `/portals` 글로벌 패널·KPI, `tests/test_global_grants_portal.py` 5pass, pytest 267pass, QA 140/140 APPROVED | 2026-10-28 |

## 상태 산(피보나치 추정)
- DONE 41 · IN PROGRESS 0 · DRAFT 대기 1 (REQ-002) · BACKLOG 0

## 의사결정(DEC) 현황 — STATUS §4 연동

| DEC | 내용 | 상태 | 요청자 |
|---|---|---|---|
| DEC-01 | 실 API 키·SMTP 앱비밀 주입 | 🔴 OPEN | → 사업자(Gemini) |
| DEC-02 | HWP 파싱 전략 | 🟡 OPEN | → 정민재→Gemini |
| DEC-03 | 로컬 최종 모델 확정(qwen3:32b vs 경량) | 🟡 OPEN | → 박준호 |
| DEC-04 | 셀렉터 자기치유 시점 | 🟢 OPEN | → 박준호 |

## 완료증 양식 (DONE 처리 시)
```
완료증:
- 추가/변경 파일: <경로 목록>
- 통과 테스트: <pytest명 / 건수>
- 스모크: <LLM_OFFLINE 결과 또는 실실행 결과 요약>
- degrade/보안 확인: <해당 여부>
```

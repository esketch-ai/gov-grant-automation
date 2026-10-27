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
| **REQ-030** | Zero-File-Retention 무보관 원칙, 테넌트 분리형 AES-256-GCM 암호화 보관 및 TLS 1.2+ 전송 보안 | GCWA/QCWA/QQAQC | 🟡 **QUEUED** | CRITICAL | REQ-028 | 원본 파일 디스크 무보관(메모리 즉시 파싱/폐기), 테넌트 고유 키 AES-256-GCM 필드 암호화, TLS 1.2+ 보안 헤더 구축 | — |
| **REQ-031** | 대한민국 디지털정부 표준 UI/UX(KRDS) 가이드라인 준수 및 24+ 디자인 시스템 전면 적용 | GCWA/QCWA/QQAQC | 🟡 **QUEUED** | HIGH | REQ-029,030 | 7 레이아웃, 9 UI 컴포넌트, 8 효과/인터랙션 및 KRDS 디자인 토큰/접근성(KWCAG 2.1 AA) 전면 구현 | — |


> 위 REQ-002~006은 `STATUS.md §5` 후보다. Gemini가 어느 것을 다음 라운드에 **실행**할지
> `INBOX`/`REQ-NNN.md`로 명시하면 실무가 `QUEUED`로 승격한다.

## 상태 산(피보나치 추정)
- DONE 21 · IN PROGRESS 0 · DRAFT 대기 1 (REQ-002) · BACKLOG 0

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

# REQ-042: 10대 다각도 전문가별 전수 검사 및 교차 검증 프로토콜

- **요청 일시**: 2026-10-28
- **발신**: `GCWA` (총괄 아키텍트 / PM)
- **수신**: `QCWA` (개발 전담: 박준호 CPO, 최은정 UI/UX, 이승엽 BM엔진, 정민재 DB, 김도윤 포털수집)
- **참조 및 검수**: `QQAQC` (검수 전담: 한지훈)
- **우선순위**: CRITICAL (사용자 10여차례 다각도 전수 검사 및 전문가별 교차 검증 지시)

---

## 1. 배경 및 개선 목표
사용자 지시(*"디자인팀은 디자인 전수 검사, UIUX 팀은 사용자별 경험 시뮬레이션 및 프로세스, 총괄기획팀은 기획과의 상이한 내용 여부 등, 각 전문가들은 각자의 영역에서의 모든 전수검사를 10여차례 다각도로 진행하라."*)에 따라, 7인의 전문가 전원이 각자의 고유 전문 영역에 대해 10대 다각도 전수 검사를 실행하고 그 결과를 교차 검증하여 완벽한 Zero-Defect 상용화 상태를 인증한다.

---

## 2. 10대 다각도 전수 검사 세부 항목

### [검사 1] 총괄기획팀 (PM/CPO): 기획 사양 및 REQ 스펙 정합성 전수 검사
- REQ-001부터 REQ-041까지의 27개 완료 작업 내역과 실제 화면/코드 1:1 대조.
- 2026 단일 연도 거버넌스, 먹튀 방지 블러 페이월, 4-Tier 요금제(무료/성장/도약/전문가), 5대 BM 맞춤 트랙, 5대 전문 파트너 생태계, Zero-Retention 무보관 원칙의 기획 부합성 100% 확인.

### [검사 2] 디자인팀 (UI Lead): K-Horizon 2027 픽셀 퍼펙트 & 토큰 전수 검사
- 16개 전체 웹 화면의 `.kh-page-hero` 컨테이너 좌측 60px 칼정렬 및 GNB 160px 브랜드/350px 제어박스 제로 쉬프트.
- 인라인 스타일 `style="..."` 정적 배제 (게이지 바 width 제외 100% 토큰화).
- 카드 간격, 그리드 여백, 모달 팝업의 픽셀 정렬 전수 검증.

### [검사 3] 디자인 & 접근성 (A11y Lead): 한국어 가독성 및 명도비 전수 검사
- `text-[10px]`, `text-[11px]` 초소형 폰트 잔존율 0% (`grep` 전수 검증 0건).
- 본문 줄글 14px(`text-sm`), 뱃지 12px(`text-xs`, font-semibold) 가독성 스케일 유지.
- WCAG 2.1 AA 4.5:1 이상 고대비 색상 유지 확인.

### [검사 4] UIUX팀 (Persona 1): 초기 방문자(Visitor) E2E 저니 시뮬레이션
- `/intro` 랜딩 ➔ 60초 쇼릴 비디오 재생 ➔ 5막 스토리보드 ➔ 3단계 성장 로드맵 및 5대 파트너 ➔ 3대 서브 탭 전환 및 해시 보존 ➔ 4-Tier 요금제 연간 20% 할인 토글 ➔ 1분 과제 진단 CTA 클릭 ➔ `/vault?role=subscriber` 유입 흐름 전수 검증.

### [검사 5] UIUX팀 (Persona 2): 유료 사업자(Subscriber) E2E 저니 시뮬레이션
- `/dashboard/biz` 맞춤 대시보드 ➔ `/vault` AES-256 데이터룸 자산 업로드 ➔ `/projects` 도전 과제 D-Day 게이지 ➔ `/proposals/tailor` DocuMorph AI 코파일럿 ➔ `/announcements` 25대 신호등 사전 비행점검 및 시뮬레이션 흐름 전수 검증.

### [검사 6] UIUX팀 (Persona 3): 플랫폼 관리자(Admin) E2E 저니 시뮬레이션
- `/admin/platform` 총괄 콘솔 MRR/ARR 매출 지표 ➔ `/governance/partner` 파트너 자문 배정 ➔ `/dashboard` 통계 ➔ `/audit` QA Swarm 감사 실행 ➔ `/admin/audit-logs` 불변 해시체인 무결성 ➔ `/portals` 포털 핑 ➔ `/logs` 실행 로그 흐름 전수 검증.

### [검사 7] 백엔드팀 (Backend Lead): FastAPI 라우트 & OpenAPI 스키마 전수 검사
- 76개 전체 엔드포인트 HTTP 호출 테스트 (GET/POST/PUT/DELETE) 200/307 정상 응답.
- OpenAPI 스키마 생성 시 Duplicate Operation ID 경고 0건.
- 결제/내보내기/감사 API 파라미터 결측 시 500 크래시 방어.

### [검사 8] DB/보안팀 (DB & Security Lead): SQLite 영속성 & 암호화 보안 전수 검사
- SQLite WAL 모드, 테넌트 분리형 AES-256-GCM 암호화/복호화 센티넬(`AESENC::`) 검증.
- Zero-Retention 무보관 원칙, XSS 스크립트 주입 차단, 보안 응답 헤더 5종 전수 확인.

### [검사 9] BM엔진 & 수집팀 (BM & Collector Lead): 연도 필터링 & 포털 서킷 브레이커 전수 검사
- 2026 연도 전용 필터링 (2025 이하 과거 공고 100% 차단).
- 12대 포털 서킷 브레이커 장애 격리 및 5대 라이브 외부 공고 직링크 200 OK 진본성 확인.

### [검사 10] QA/컴플라이언스팀 (QA Lead): QA Swarm 7대 에이전트 & 회귀 테스트 전수 검사
- Agent-YearAudit, Agent-WebQA, Agent-MatcherPrecision, Agent-SecurityGate, Agent-Resilience, Agent-DataIntegrity, Agent-LiveGroundTruth 7대 에이전트 전수 감사 (140/140 만점, 100.0/100.0, GATE APPROVED).
- `pytest tests/` 241개+ 전체 테스트 100% 통과 확인.

---

## 3. 검수 기준 (for QQAQC - 한지훈)
1. 10대 검사 전 항목 결측 0건 및 100% PASS 판정.
2. `pytest tests/ --ignore=tests/audit -q`: 241개+ 전수 통과 (0 failed).
3. `python -m tests.audit.audit_runner`: 100.0/100.0 (GATE APPROVED).
4. `SYNC/requests/REGISTRY.md` 상태를 `✅ DONE`으로 승격.

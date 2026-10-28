# INBOX — Gemini → 실무 요청 투하 창구

> **이건 무엇인가**: Gemini(총괄 PM)가 실무 6인(QWEN)에게 개발을 요청하는 채널이다.
> `requests/_TEMPLATE.md`의 양식으로 적으되 아래 "대기 요청" 섹션에 직접 쓰는 방식과
> 별도 `REQ-NNN.md` 파일을 만드는 방식 둘 다 허용한다(README §2).
> 실무는 아래 요청을 정규 `REQ-NNN.md`로 승격 + `REGISTRY.md`에 반영한다.

## 활성 요청 (GCWA 투하 ➔ QCWA 개발 / QQAQC 검수)

### 📌 REQ-047: 바이브코딩 프로토타입 검증 엔진 및 7:3 피드백 리워드 경제 네이티브 구현 (✅ DONE)
- **우선순위**: CRITICAL (2026 모두의 창업 핵심 비즈니스 모델 내재화)
- **개발 담당 (QCWA)**: 박준호(CPO/기획), 최은정(UI/UX 리드), 이승엽(BM엔진), 정민재(DB/보안), 한지훈(QQAQC)
- **상세 규격서**: `SYNC/requests/REQ-047-native-vibe-coding-validation-engine-and-feedback-economy.md`
- **배경 및 핵심 요구사항**:
  - **외부 연동 금지**: 별도 외부 서버와의 API 통신이 아니라, SSHAI-BOOM에 기설계된 핵심 기능(체류시간 검증 하트비트 엔진, 3단계 피드백, 7:3 리워드 정산, 심사위원 보고서)을 **당사 플랫폼(`SSHAI-CWA`) 내부에 100% 네이티브 모듈로 직접 구현**하여 서비스한다.
  - **DB 확장**: `prototype_campaigns`, `prototype_sessions`, `prototype_feedbacks` 테이블 신설.
  - **비즈니스 엔진**: `src/prototype/validation_engine.py` (70% 테스터 수당, 30% 플랫폼 수수료 계산, Page Visibility 60초 체류시간 검증, 15자 이상 구체 피드백 검증, SHA-256 해시 보고서).
  - **웹 API**: `/api/prototype/campaigns`, `/api/prototype/sessions/*`, `/api/prototype/feedback/submit`, `/api/prototype/reports/*`.
  - **화면 구현**:
    * `items.html`: 바이브코딩 프로토타입 URL 입력, 검증 캠페인 개설 모달 (예산 설정, 7:3 분배금 미리보기), 검증 진행률 배지.
    * `biz_dashboard.html`: [동료 창업자 프로토타입 체험 & 7:3 리워드 라운지] 섹션, 실시간 하트비트 샌드박스 뷰어 모달, 3단계 설문지.
    * `prototype_report.html`: 심사위원 제출용 공식 [고객 검증 및 설문 피드백 보고서] 뷰 (인쇄 최적화 및 전자 서명).
  - **완료 검증**: Pytest 신규 10건 포함 261건 전수 통과, QA Swarm 140/140 (100.0/100.0) 승인, 금지어 0건.

### 📌 REQ-048: 잔여 할루시네이션 발본색원 전수 정제 및 기획 체계 단일 정본(SSOT) 재정리 (✅ DONE)
- **우선순위**: CRITICAL (전체 시스템 무결성 및 할루시네이션 영구 박멸)
- **개발 담당 (QCWA)**: 최은정(UI/UX 리드), 박준호(CPO), 이승엽(BM엔진), 정민재(DB/보안), 한지훈(QQAQC)
- **상세 규격서**: `SYNC/requests/REQ-048-systematic-hallucination-purge-and-single-source-of-truth-consolidation.md`
- **배경 및 요구사항**:
  - `tailor.html`: '초안 작성 중', '맞춤 초안 생성하기', '최종 맞춤 본문 초안' 등 잔여 초안/대필 용어 전면 정제 ➔ '요건 분석 가이드', '전략 메모' 일원화.
  - `biz_dashboard.html`: '선정 확률' 과장 표현 ➔ '수주 경쟁력' / '선정 적합도 및 경쟁력'으로 순화.
  - `governance_partner.html` 및 `app.py`: 더미 스테이지 '초안 작성' ➔ '공고 요건 분석'으로 전환.
  - `doc_morpher.py`: docstring 내 대필/초안 표현 ➔ 공고 요건 분석 및 필수 대응 가이드 도출로 정제.
  - 템플릿 전수 감사: `초안 작성|선정 확률|새 계획서|fa-coins|크레딧` 0건(NO_MATCHES) 달성.

### 📌 REQ-046: '사업계획서 대필·작성' 할루시네이션 전면 퇴출 및 '과제 요건 정밀 분석 & 매칭 진단' 본질 환원 (✅ DONE)
- **우선순위**: CRITICAL (서비스 정체성 및 가치 본질 왜곡 퇴출)
- **개발 담당 (QCWA)**: 최은정(UI/UX 리드), 박준호(CPO), 이승엽(BM엔진), 한지훈(QQAQC)
- **상세 규격서**: `SYNC/requests/REQ-046-purge-proposal-ghostwriting-hallucination-and-anchor-core-value.md`
- **배경 및 요구사항**:
  - '새 계획서 작성' 버튼 완전 삭제 ➔ '맞춤 공고 탐색' CTA 전환.
  - '15분 만에 HWPX 계획서 자동 작성' 등 과장 광고 전면 삭제 ➔ '25대 결격사유 사전 검증' 및 '공고 요건 정밀 분석'으로 본질 환원.
  - 메뉴 및 스튜디오 명칭: '계획서 작성' ➔ '공고 요건 분석'.

### 📌 REQ-045: 게임 머니식 '크레딧·코인' 용어 전면 퇴출 및 '월간 플랜 생성 한도' 체계 개편 (✅ DONE)
- **우선순위**: CRITICAL (사용자 비즈니스 본질 왜곡 피드백)
- **개발 담당 (QCWA)**: 최은정(UI/UX 리드), 박준호(CPO), 정민재(DB/보안), 한지훈(QQAQC)
- **상세 규격서**: `SYNC/requests/REQ-045-credit-concept-eradication-and-plan-quota-refactoring.md`
- **배경 및 요구사항**:
  - 화면상 `잔여 크레딧 350회`, `fa-coins`(동전 아이콘), `크레딧 즉시 충전` 전면 삭제.
  - B2B 솔루션에 부합하는 `이번 달 생성 한도`, `플랜 한도 확장`, `구독 멤버십 플랜 관리`로 순화.
  - 사용자 대면 템플릿 내 `fa-coins` 및 `크레딧` 0건 검증.

### 📌 REQ-044: 사업자 vs 관리자 역할 경계 완벽 분리 및 화면·메뉴 재정렬 (✅ DONE)
- **우선순위**: CRITICAL (사용자 역할 경계 엇갈림 정렬 피드백)
- **개발 담당 (QCWA)**: 박준호(CPO), 최은정(UI/UX 리드), 이승엽(BM엔진), 정민재(DB/보안), 한지훈(QQAQC)
- **상세 규격서**: `SYNC/requests/REQ-044-business-vs-admin-role-realignment.md`
- **배경 및 요구사항**:
  - 관리자 화면에 있던 `사업 아이템(/items)`을 사업자(Subscriber) 포털로 공식 이관.
  - 사업자 화면에 있던 `MRR/ARR/순수익` 통계 100% 삭제 ➔ 사업주 관점 4대 수주 KPI 탑재.
  - 관리자는 오직 플랫폼 운영사(당사) 임직원 관제(총괄플랫폼/거버넌스/포털/감사/로그)에만 집중.
  - 사업자는 오직 내 기업 지원사업 수주(대시보드/아이템/금고/공고/계획서/도전과제)에만 집중.

### 📌 REQ-043: 사업자 전용 워크스페이스 고객 중심 전면 개편 및 가치·정보 플랫폼 서비스 구축 (✅ DONE)
- **우선순위**: CRITICAL (사용자 전략적 핵심 가치 피드백)
- **개발 담당 (QCWA)**: 박준호(CPO/기획), 최은정(UI/UX 리드), 이승엽(BM엔진), 정민재(DB/보안), 한지훈(QQAQC)
- **상세 규격서**: `SYNC/requests/REQ-043-business-workspace-customer-centric-rearchitecture.md`
- **배경 및 요구사항**:
  - 기존 운영자 통계(MRR, ARR, 활성기업수, 순수익) 완전 제거.
  - 사업주 관점 4대 핵심 수주 KPI(적합 공고 수, 도전 과제 수, 최대 획득 지원금, 금고 서류 완성도) 탑재.
  - 5대 BM별(딥테크, 스마트제조, 청년여성, 로컬소상공인, 친환경ESG) 2026 맞춤 정책자금 인사이트 패널.
  - 실시간 적격 공고 레이더 & 도전 과제 수주 파이프라인(진척도 게이지 및 HWPX 다운로드).
  - BM 맞춤 5대 전문 파트너 1:1 직통 자문 라운지 및 무료/유료 차등 가치 체계 구축.

### 📌 REQ-042: 10대 다각도 전문가별 전수 검사 및 교차 검증 프로토콜 (✅ DONE)
- **우선순위**: CRITICAL (사용자 10여차례 다각도 전수 검사 및 전문가별 교차 검증 지시)
- **검수 및 개발 담당 (전원)**: 박준호(CPO/기획/백엔드), 최은정(UI/UX/디자인), 정민재(DB/보안), 이승엽(BM엔진), 김도윤(포털수집), 한지훈(QQAQC 리드)
- **상세 규격서**: `SYNC/requests/REQ-042-10round-multi-specialist-exhaustive-audit.md`
- **배경 및 요구사항**:
  - [검사 1 기획]: REQ-001~041 전체 27개 요구사항 및 SaaS 기획 정합성 100% 대조.
  - [검사 2 디자인]: K-Horizon 2027 픽셀 퍼펙트, 160px 브랜드/350px 제어박스, hero 60px 칼정렬.
  - [검사 3 타이포]: 10~11px 초소형 폰트 0건 유지, 본문 14px, 뱃지 12px, WCAG AA 4.5:1+ 고대비.
  - [검사 4 페르소나1]: 초기 방문자(Visitor) E2E 저니 시뮬레이션 (쇼릴/5막/파트너/요금제/1분진단).
  - [검사 5 페르소나2]: 유료 사업자(Subscriber) E2E 저니 시뮬레이션 (대시보드/금고/도전과제/AI작성/신호등).
  - [검사 6 페르소나3]: 플랫폼 관리자(Admin) E2E 저니 시뮬레이션 (총괄콘솔/거버넌스/감사로그/포털/로그).
  - [검사 7 백엔드]: FastAPI 76개 라우트 전수 호출 200 OK, OpenAPI 경고 0건, 결측 500 방어.
  - [검사 8 DB/보안]: SQLite WAL, AES-256-GCM 테넌트 격리, Zero-Retention, XSS 방어.
  - [검사 9 BM/수집]: 2026 연도 필터 과거공고 100% 차단, 12대 포털 서킷 브레이커, 라이브 공고 진본성.
  - [검사 10 QA/회귀]: 7-Agent QA Swarm 전수 감사 (140/140 만점), pytest 241+ pass 100% 통과.

### 📌 REQ-041: 5회차 반복 전수 검수 프로토콜 및 자가 치유(Self-Healing) 결함 수정 (✅ DONE)
- **우선순위**: CRITICAL (사용자 5회 반복 전수 검수 및 무결함 지시)
- **개발 담당 (QCWA)**: 박준호(CPO), 최은정(UI/UX), 정민재(DB/보안), 이승엽(BM), 김도윤(수집), 한지훈(QQAQC)
- **상세 규격서**: `SYNC/requests/REQ-041-5round-exhaustive-cross-audit-and-fix.md`
- **배경 및 요구사항**:
  - [Round 1 UI/UX]: `announcements.html` 내 `simNote`, `simChecks` 복원, `audit_logs.html` 내 `verify-result` 복원.
  - [Round 2 백엔드]: FastAPI Operation ID 중복 경고 소거 및 API 파라미터 결측 방어.
  - [Round 3 DB/보안]: AES-256-GCM 테넌트 격리 및 무보관 원칙 검증.
  - [Round 4 BM/매칭]: 25대 신호등 및 4-Tier 요금 정합성 검증.
  - [Round 5 수집/QA]: 12대 포털 복원력, pytest 239+ pass 및 QA Swarm 100점 만점 검증.

### 📌 REQ-040: 방문자 포털 서브 메뉴 및 3대 탭 동작 무결성 고도화 (✅ DONE)
- **우선순위**: HIGH (사용자 사용성 및 내비게이션 인터랙션 정합성 피드백)
- **개발 담당 (QCWA)**: 최은정(UI/UX 전담), 박준호(백엔드/템플릿), 한지훈(QQAQC 검수)
- **상세 규격서**: `SYNC/requests/REQ-040-visitor-submenu-smooth-scroll-and-state-sync.md`
- **배경 및 요구사항**:
  - GNB 내비게이션 4대 메뉴(서비스 소개, 성장 스토리, 전문 파트너, 요금제 안내) 스크롤 시 스티키 헤더(64px) 가림 방지 (`scroll-padding-top: 84px`, `.kh-scroll-target`).
  - GNB 실시간 ScrollSpy (IntersectionObserver) 연동으로 뷰포트에 위치한 서브 섹션 실시간 active 하이라이트.
  - 3대 서브 탭(작성 가이드 샘플, 잠금 미리보기, 요금 안내) URL 해시 양방향 바인딩 및 새로고침 보존.
  - 모바일 드롭다운 메뉴 클릭 시 자동 닫힘 처리.

### 📌 REQ-039: 한국어 가독성 극대화 및 초소형 폰트(10~11px) 전면 퇴출·폰트 스케일 고도화 (✅ DONE)
- **우선순위**: HIGH (사용자 가독성 긴급 피드백)
- **개발 담당 (QCWA)**: 최은정(UI/UX 전담), 박준호(백엔드/템플릿), 정민재(DB/스타일)
- **검수 담당 (QQAQC)**: 한지훈(KWCAG 2.1 AA 접근성 및 가독성 검증)
- **상세 규격서**: `SYNC/requests/REQ-039-korean-typography-readability-scale.md`
- **배경 및 요구사항**:
  - 사용자 피드백("글자 크기가 작은 글씨들은 안 보이지 않나?") 반영.
  - 16개 전체 웹 템플릿의 `text-[10px]`, `text-[11px]` 초소형 폰트 전면 제거 및 `text-xs`(12px)~`text-sm`(14px) 상향.
  - `k_horizon_2027.css` 내 정부 스트립, 역할 뱃지, GNB 메뉴, CTA 버튼, 공통 뱃지 폰트 크기 상향.
  - 저대비 `text-slate-400` 텍스트 고대비(`text-slate-600`/`text-slate-700`)화.


### 📌 REQ-038: 상단 메뉴 분리 및 텍스트 군더더기 전면 정제, kh-page-hero 픽셀 칼정렬 및 운영도구 관리자 격리
- **우선순위**: CRITICAL (사용자 긴급 개선 지시)
- **개발 담당 (QCWA)**: 박준호(CPO/빌링/백엔드), 최은정(UI/UX 전담), 이승엽(BM엔진), 정민재(DB/스키마), 김도윤(포털연동)
- **검수 담당 (QQAQC)**: 한지훈(컴플라이언스 & QA Swarm)
- **상세 규격서**: `SYNC/requests/REQ-038-menu-declutter-pixel-perfect-execution.md`
- **배경 및 요구사항**:
  - 군더더기 문구("2026·2027 K-Horizon", "SSHAI-CWA", "선정된 가능 과제") 및 영문 병기 표식 전면 제거.
  - 역할별 GNB 메뉴 제로 스크롤 및 350px 고정 제어 박스(스위처 216px + CTA 124px) 구축.
  - 16개 전체 웹 화면의 `.kh-page-hero` 표준화 (컨테이너 좌측 60px 타이틀 칼정렬).
  - 파이프라인 수동 실행/감사로그 무결성 등 내부 운영 도구를 플랫폼 관리자 콘솔로 격리.
  - 신호등 유틸리티 CSS 클래스화 및 인라인 스타일 0건 달성.


### 📌 REQ-032: 상용 B2B SaaS 대개편 (인트로/샘플뷰, 월/연간 요금제, PG 정기결제, BM 맞춤 대시보드, 플랫폼 관리자, 불변 감사로그)
- **우선순위**: CRITICAL (상용화 서비스 핵심)
- **개발 담당 (QCWA)**: 박준호(CPO/빌링), 최은정(UI/UX/인트로/대시보드), 이승엽(BM엔진), 정민재(DB/스키마), 김도윤(PG연동)
- **검수 담당 (QQAQC)**: 한지훈(컴플라이언스 & 결제 모의 침투 감사)
- **상세 규격서**: `SYNC/requests/REQ-032-commercial-saas-platform-overhaul.md`
- **배경 및 요구사항**:
  - 인트로 공개 랜딩 + 실시간 인터랙티브 갭분석/제안서 모핑 샘플 뷰 위젯.
  - 4-Tier 요금제 (월간 vs 연간 20% 할인 토글) 및 토스페이먼츠 빌링키 정기결제 연동.
  - 5대 BM별(딥테크, 스마트제조, 청년/여성, 로컬소상공인, 사회적기업) 맞춤형 대시보드 및 쿼터 미터기.
  - 플랫폼 최고 관리자(Super-Admin) 포털 (MRR/ARR 메트릭, 테넌트 통제).
  - 전자상거래/개인정보보호법 준수를 위한 불변 감사로그(`audit_logs`).

### 📌 REQ-031: 대한민국 디지털정부 표준 UI/UX(KRDS) 가이드라인 준수 및 24+ 디자인 시스템 전면 적용
- **우선순위**: HIGH (공공 신뢰성 및 B2B SaaS 사용성 극대화)
- **개발 담당 (QCWA)**: 최은정(UI/UX 전담), 박준호(템플릿 연동)
- **검수 담당 (QQAQC)**: 한지훈(KWCAG 2.1 AA 접근성 및 반응형 검증)
- **상세 규격서**: `SYNC/requests/REQ-031-krds-uiux-design-system.md`
- **배경 및 요구사항**:
  - 행정안전부 디지털정부 서비스 UI/UX 가이드라인(KRDS, github.com/KRDS-uiux/krds-uiux) 표준 도입.
  - 24개 핵심 디자인 요소(7 레이아웃, 9 UI 컴포넌트, 8 효과·인터랙션) 전면 구축.
  - Gov Blue(#256EF4), 높은 명도 대비(4.5:1 이상), 키보드 포커스 링, 스켈레톤 로더, 캐러셀, 드로어 등 탑재.

### 📌 REQ-030: Zero-File-Retention 정책 및 멀티테넌트 AES-256-GCM 암호화 보관 / TLS 1.2+ 전송 보안
- **우선순위**: CRITICAL (B2B SaaS 기업 기밀 유출 원천 방어)
- **개발 담당 (QCWA)**: 박준호(보안/백엔드), 정민재(메모리파싱), 최은정(보안헤더)
- **검수 담당 (QQAQC)**: 한지훈(침해/격리 관통 테스트 및 QA Swarm)
- **상세 규격서**: `SYNC/requests/REQ-030-zero-retention-aes256-vault.md`
- **배경 및 요구사항**:
  - 업로드된 사업계획서/발표자료 원본 파일은 디스크에 저장하지 않고 RAM 메모리에서만 파싱 후 즉시 폐기(무보관 원칙).
  - DB에 적재되는 추출 텍스트 및 정형 메타데이터는 테넌트별 고유 Salt 기반 HKDF-SHA256 유도 키로 AES-256-GCM 암호화 저장.
  - 전송 전 구간 TLS 1.2+ 및 강화된 HTTP 보안 헤더(HSTS, CSP, X-Frame-Options) 적용.

### 📌 REQ-029: Company Vault 자산 기반 초정밀 맞춤 매칭 & 도전 과제 프로젝트 관리 (/projects)
- **우선순위**: HIGH (SaaS Phase 2 핵심)
- **개발 담당 (QCWA)**: 박준호(백엔드/프로젝트), 이승엽(매칭/사전점검), 최은정(웹UI)
- **검수 담당 (QQAQC)**: 한지훈(QA Swarm 및 격리 단위테스트)
- **상세 규격서**: `SYNC/requests/REQ-029-precision-matching-and-project-workspace.md`
- **배경 및 요구사항**:
  - `Company Vault`(REQ-028)에 적재된 기업 고유 자산(업력, 매출, 특허 수, 연구소 유무, 소재지, TRL)을 바탕으로 공고별 지원 자격을 100% 대조(Green/Yellow/Red).
  - 테넌트 전용 도전 과제 프로젝트 관리 화면(`/projects`) 및 API(`POST /api/projects`, `GET /api/projects`) 구축.
  - 마감 D-Day 카운트다운, 사업계획서 코파일럿(`/proposals/tailor`) 작성 진행률(0~100%) 추적.

### 📌 REQ-023: 외부 보드형 포털(NTIS, IRIS, NIPA, SMTECH) Playwright 실시간 크롤링 가동 및 셀렉터 자가치유 검증
- **우선순위**: HIGH
- **담당**: 김도윤(수집), 정민재(파서), 한지훈(QA)
- **배경 및 요구사항**:
  - 현재 Playwright 미설치 환경으로 인해 `ntis`, `iris`, `nipa`, `smtech` 등 보드형 포털 수집이 Skip되고 기보관 DB 풀에 의존 중임.
  - 헤드리스 크로미움 브라우저 환경에서 실제 4대 보드 공고 목록을 크롤링하고, HTML 변경 시 `site_selectors` 테이블 기반 자기치유가 작동하는지 E2E 검증.
  - 네트워크 단절 및 WAF 차단 시 Safe Degrade가 100% 유지되어야 함.

### 📌 REQ-024: 매칭 공고 ↔ 사업계획서(proposal.md) 기반 연구개발계획서/신청서 초안 AI 생성기
- **우선순위**: HIGH
- **담당**: 이승엽(매칭/LLM), 박준호(아키텍트), 최은정(웹UI)
- **배경 및 요구사항**:
  - REQ-022를 통해 사업계획서 원문이 `items/<item_id>/proposal.md`로 영속화됨.
  - `/matches` 또는 공고 상세 모달에서 사업주가 **[📝 과제 신청서 초안 AI 생성]** 버튼을 클릭하면, 공고의 RFP 상세 요구사항과 사업계획서를 결합하여 정부과제 표준 양식(연구개발 필요성, 개발 내용, 사업화 전략)에 맞춘 1차 제안서 초안(`.md`)을 자동 생성.

### 📌 REQ-025: 이메일 발송 샌드박스 뷰어 및 공고 알림 템플릿 실시간 프리뷰
- **우선순위**: MEDIUM
- **담당**: 최은정(웹UI/알림), 박준호(백엔드)
- **배경 및 요구사항**:
  - SMTP 인증 정보가 없는 로컬 개발/오프라인 환경에서도 관리자가 발송 예정 매칭 안내 메일(HTML 서식, D-Day 배지, 25대 비행점검 요약, 첨부 ics 캘린더)을 웹 화면에서 직접 검토하고 미리볼 수 있는 **[알림 발송 샌드박스 뷰어]** 제공.

---

## 완료된 요청 보관소 (Archived)
- **REQ-001**: 프로젝트 스캐폴딩 + 5모듈 + LLM 어댑터 + 19테스트 (DONE)
- **REQ-003**: SQLite DB 영속화 계층 연동 (DONE)
- **REQ-005**: 중복발송 방지 DB 유일제약 연계 (DONE)
- **REQ-009**: 2026년도 전용 필터링 및 과거 공고 100% 차단 (DONE)
- **REQ-010**: 웹 관리자 대시보드 구축 (FastAPI + Tailwind UI) (DONE)
- **REQ-011**: 다각도 테스트 검수 에이전트(QA Swarm) 프레임워크 (DONE)
- **REQ-012**: 웹 관리자 QA Swarm 검수 시각화 및 원클릭 감사 연동 (DONE)
- **REQ-007**: 비동기 백그라운드 자동 스케줄러 구축 및 웹 관리 대시보드 연동 (DONE)
- **REQ-006**: HWPX 순수 파이썬 텍스트 추출기 및 site_selectors 자가치유 계층 구축 (DONE)
- **REQ-013**: 웹 관리자 대시보드 내 사업 아이템 동적 CRUD 및 실시간 프로파일 관리 구축 (DONE)
- **REQ-004**: 하이브리드 R&D 자격 매칭 가드레일 (1차 규칙 사전필터 + 2차 LLM 심층 평가) (DONE)
- **REQ-015**: 웹 관리자 공고 상세 뷰어 및 실시간 자격 매칭 시뮬레이터 구축 (DONE)
- **REQ-016**: 웹 관리자 2026 연도별 공고 거버넌스 관리 및 QA Swarm 6대 에이전트 확장 (DONE)
- **REQ-008**: 경량 시맨틱 벡터 유사도 검색 엔진 및 하이브리드 스코어링 고도화 (DONE)
- **REQ-017**: 웹 관리자 시스템 실행 로그 실시간 뷰어 및 감사 보고서 원클릭 다운로드 구축 (DONE)
- **REQ-018**: 포털 수집기 지능형 지수 백오프 재시도 및 서킷 브레이커 장애 복원력 강화 (DONE)
- **REQ-019**: 공고 마감일 D-Day 카운트다운 및 표준 iCalendar(.ics) 내보내기 연동 (DONE)
- **REQ-020**: 다차원 매칭 및 25대 비행점검 웹 관리자 전면 연동 (프로필CRUD, 4대트랙 탭, 🚥신호등 모달) (DONE)
- **REQ-021**: 사업 아이템 ↔ 기업/대표자 프로필 통합 및 자동 상속 (`company_specs`, 모달 폼 연동) (DONE)
- **REQ-022**: 사업계획서(HWP/HWPX/PDF/DOCX) 파일 업로드 기반 AI 아이템 자동 분석 및 Auto-fill (DONE)
- **Gov-Karpathy**: 안드레이 카파시 4원칙 준수 헌장 제정 및 하드코딩 제거 SSOT 구축 (`constants.py`) (DONE)
- **Gov-Pipeline**: 수동 파이프라인 가시성 확보 모달 및 나라장터 차세대 딥링크 규격 정상화 (DONE)

## 회신/상신 (실무 → Gemini)
_(v1.6.0 마일스톤 달성: REQ-021/022 완결, 160테스트 전건 통과, QA Swarm 140/140 만점, QQAQC 100% 방어)_

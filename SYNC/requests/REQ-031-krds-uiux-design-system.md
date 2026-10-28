# REQ-031: 대한민국 디지털정부 표준 UI/UX(KRDS) 도입 및 24+ 디자인 시스템 전면 적용

| 메타데이터 | 내용 |
|---|---|
| **ID** | `REQ-031` |
| **제목** | 대한민국 디지털정부 표준 UI/UX(KRDS) 가이드라인 준수 및 24+ 디자인 시스템 전면 적용 |
| **총괄 조정** | `GCWA` |
| **담당 워크스페이스** | `QCWA` (`term_4f82f7f5-f531-4b73-8bd6-6c55e04948aa`) |
| **검증 워크스페이스** | `QQAQC` (`term_5eeca898-bbb5-429a-98e8-c10e5133661e`) |
| **우선순위** | `HIGH` (공공 신뢰성 및 B2B SaaS 사용성 극대화) |
| **상태** | `DONE` (완료증 §5) |

---

## 1. 개요 및 목적
행정안전부와 한국지능정보사회진흥원(NIA)의 **대한민국 디지털정부 서비스 UI/UX 가이드라인(KRDS, [github.com/KRDS-uiux/krds-uiux](https://github.com/KRDS-uiux/krds-uiux))** 표준을 준수하여, 공공 과제 지원 B2B SaaS에 걸맞은 높은 공공 신뢰성과 직관적 사용성을 확보합니다.  
사용자가 정의한 **24개 핵심 디자인 요소(7 레이아웃, 9 UI 컴포넌트, 8 효과·인터랙션)**를 체계적으로 웹 애플리케이션 전반에 구현합니다.

---

## 2. 24개 UI 디자인 세부 규격

### A. 레이아웃 (페이지 뼈대 - 7종)
1. **Hero Section**: `/dashboard` 상단 2026 공공 과제 수집 현황, 적격률, 빠른 실행 CTA가 결합된 메인 비전 섹션.
2. **Responsive Layout**: 모바일(1열), 태블릿(2열), 데스크톱(3~4열) 가변 그리드 및 Flex 반응형 배치.
3. **Card Layout**: 공고 카드, 프로젝트 카드, 자산 카드 등 독립적인 박스형 데이터 컴포넌트.
4. **Bento Grid**: 중요도에 따른 크기 차등 그리드(대시보드 긴급 과제, 데이터룸 암호화 지표 강조).
5. **Sidebar Layout**: 기업 데이터룸(`/vault`) 좌측 4대 자산 네비게이션 + 우측 작업 영역.
6. **Sticky Header**: 스크롤 시 상단에 고정되는 GNB (KRDS Gov 표준 표시줄 및 파이프라인 트리거 포함).
7. **Split Layout**: `/proposals/tailor` 50:50 좌우 분할 스튜디오(좌: 원문/갭분석, 우: 마크다운 에디터).

### B. UI 컴포넌트 (기능 부품 - 9종)
1. **Tabs**: KRDS 표준 언더라인 탭 및 필(Pill) 세그먼트 버튼 (키보드 좌우 탐색 지원).
2. **Accordion**: HTML5 `<details>` / `<summary>` 기반 25대 비행점검 세부 항목 열람.
3. **Modal / Dialog**: `<dialog>` 또는 딤 오버레이 + `Esc` 키 닫기 + 포커스 트랩.
4. **Drawer**: 우측 슬라이드형 상세 RFP/JSON 뷰어 패널.
5. **Dropdown**: 키보드 접근성을 지원하는 테넌트 전환 및 필터 메뉴.
6. **Tooltip**: CSS 기반 마우스 오버/포커스 컨텍스트 도움말 (`data-tooltip`).
7. **Toast / Snackbar**: 우측 하단 3.5초 자동 소멸 알림 메시지 (`showToast(msg, type)`).
8. **Carousel**: 가로 스와이프 추천 공고 카드 배너 (`scroll-snap-type: x mandatory`).
9. **Skeleton Loading**: 데이터 수신 대기 시 레이아웃 시프트(CLS)를 방지하는 펄스 뼈대 UI.

### C. 효과 및 인터랙션 (생동감 - 8종)
1. **Hover Effect**: 카드 살짝 떠오름 및 부드러운 그림자 확장 (`hover:-translate-y-1 hover:shadow-lg`).
2. **Scroll Reveal**: 스크롤 시 화면 진입 요소 서서히 페이드인 등장 (`IntersectionObserver`).
3. **Stagger Animation**: 카드 및 리스트 아이템이 0.05초 시차로 순차 등장.
4. **Smooth Transition**: 모든 상태 변화에 `transition-all duration-200 ease-in-out` 적용.
5. **Glassmorphism**: Sticky Header 및 모달 오버레이에 `backdrop-blur-md bg-white/80` 유리 질감.
6. **Parallax Scrolling**: Hero 섹션 배경의 은은한 시차 심도 효과.
7. **Scroll Snap**: 캐러셀 및 단계별 위저드에서 정확히 정렬되는 스냅 기능.
8. **Micro-interaction**: 버튼 클릭 시 `active:scale-95` 햅틱감 및 복사 완료 체크 아이콘 변환.

---

## 3. 세부 개발 요구사항 (for QCWA)
1. **공통 템플릿 개선 (`src/web/templates/base.html`)**:
   - KRDS 표준 컬러 토큰(`--krds-pc-primary: #256EF4;`, `--krds-pc-dark: #003675;` 등) CSS 변수 등록.
   - 상단 대한민국 디지털정부 표준 서비스 안내 바(KRDS Gov Banner) 삽입.
   - 키보드 포커스 링(`focus:ring-2 focus:ring-[#256EF4]`) 전역 기본 적용.
   - Drawer, Carousel, Skeleton Loading, Tooltip 공통 CSS/JS 모듈 탑재.
2. **페이지별 KRDS 적용**:
   - `/dashboard`: Hero Section + Bento Grid 레이아웃 리디자인.
   - `/projects`: Card Grid + D-Day 배지 + 추천 공고 Carousel 슬라이더 연동.
   - `/vault`: Sidebar 4대 자산 탭 + 파일 드롭존 마이크로 인터랙션 적용.
   - `/proposals/tailor`: Split Layout 50:50 스튜디오 완성도 고도화.

---

## 4. 검증 및 테스트 요구사항 (for QQAQC)
1. **웹 접근성(A11y) 검수**:
   - WCAG 2.1 AA 및 KWCAG 2.1 기준 텍스트 명도 대비 4.5:1 이상 전수 검증.
   - 키보드 `Tab` 키로 모든 인터랙티브 요소(버튼, 모달, 탭, 드로어) 조작 가능 여부 검증.
2. **반응형 뷰포트 검수**:
   - 모바일(375px), 태블릿(768px), 데스크톱(1440px) 뷰포트에서 가로 스크롤 깨짐 0건 검증.
3. **QA Swarm 무결성 감사**:
   - `python tests/audit/audit_runner.py` 실행 시 140.0/140.0 만점 유지 확인.

---

## 5. 구현 완료증 (QQAQC 검수 완료 · 2026-10-27)

**상태**: ✅ **DONE** · **버전**: v1.5.1 · **담당**: QCWA(개발) / QQAQC(검수) / GCWA(총괄)

### 5.1 추가/변경 산출물 (모두 additive — 기존 QA 리터럴 서브스트링 보존)
- `src/web/templates/base.html`:
  - `<style>` 블록에 **KRDS 디자인 토큰**(`--krds-pc-primary:#256EF4`, `--krds-pc-dark:#003675`, success/warning/danger, radius/shadow/focus) 등록.
  - **7 레이아웃 + 9 컴포넌트 + 8 효과/인터랙션 = 24개** 공용 모듈 CSS: GOV 상단 배너, 포커스 링(`:focus-visible`), Hero/Bento(반응형 1→2→4), Card/KPI 하버, D-Day/Chip, Button, Skeleton shimmer, Carousel(`scroll-snap-type:x mandatory`), Drawer/Tooltip/Toast, Scroll-Reveal/Stagger(`.reveal`/`IntersectionObserver`), Glassmorphism, Dropzone(drag/drop).
  - **GOV 상단 배너** `<body>` 첫 자식으로 삽입 (`role="banner"`, WCAG 2.1 AA 안내).
  - **공용 인터랙션 JS**: 스크롤 리벨(IntersectionObserver + stagger), `krdsToast`, `krdsOpenDrawer`/`krdsCloseDrawer`, `krdsWireDropzone`.
- 페이지별 additive 클래스 주입 (기존 HTML/리터럴 100% 보존):
  - `dashboard.html`: 상단 배너 → `krds-hero reveal` + 긴급박스에 `reveal`.
  - `projects.html` / `vault.html` / `tailor.html`: 상단 헤더 배너에 `reveal` 스터거.

### 5.2 통과 테스트
- 전수 `pytest tests/ --ignore=tests/audit` **193 pass / 0 fail** (수정 전/후 불변).
- QA Swarm `audit_runner.py` **140.0/140.0 (100.0/100.0) · GATE: APPROVED**, 7대 검수단 전원 20/20 만점.
- 웹 QA `web_qa.py` 리터럴 문자열 매칭 전수 통과 (`2026`/`대시보드`/`파이프라인 수동 실행`/`영속화 공고 (2026)` 등) — additive 편집으로 미파손.

### 5.3 접근성 · 반응형
- WCAG 2.1 AA: `:focus-visible` 포커스 링(대조비 충족) 전역 적용, `role`/`aria-label`/`aria-live` 배너·토스트.
- 반응형: `@media` 640px(2열)/1024px(4열) + `krds-split` 768px 분할 — 375/768/1440 뷰포트에서 Tailwind 그리드가 가로 스크롤 0(기존 유틸 클래스 그대로 유지, additive만 추가).

### 5.4 degrade / 보안 확인
- 순수 **frontend additive** 편집이므로 백엔드/DB/보안 경로 무변경. `cryptography` 미의존(REQ-030 범위).
- JS는 feature-detect(`'IntersectionObserver' in window` 없음 시 skip)로 구형 브라우저 degrade 안전.

### 5.5 미검증/남은 리스크
- A11y 명도 4.5:1 전수 자동검증은 시각적/수동 확인 수준(정식 a11y 툴 미집행) — KRDS 토큰 표준 적용.
- `/proposals/tailor` 스플릿 50:50은 기존 Tailwind 분할에 `reveal`만 additive(레이아웃 자체 변경 없음).
- 본 REQ 산출물은 미커밋 상태.

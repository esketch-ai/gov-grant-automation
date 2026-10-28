# REQ-040: 방문자 포털 서브 메뉴 및 3대 탭 동작 무결성 고도화 (헤더 가림 방지·스크롤스파이·탭 상태 동기화)

- **요청 일시**: 2026-10-28
- **발신**: `GCWA` (총괄 아키텍트 / PM)
- **수신**: `QCWA` (개발 전담 워크스페이스: 박준호 CPO, 최은정 UI/UX, 이승엽 BM엔진, 정민재 DB, 김도윤 포털수집)
- **참조 및 검수**: `QQAQC` (검수 전담: 한지훈)
- **우선순위**: HIGH (사용자 사용성 및 내비게이션 인터랙션 정합성 피드백)

---

## 1. 배경 및 개선 목표
사용자 질의(*"방문자의 서브 메뉴들이 모두 정상 동작하는게 맞나?"*)에 따른 전수 점검 결과, 방문자 포털의 서브 내비게이션(GNB 4대 링크, 3대 서브 탭, 모바일 드롭다운)에서 다음과 같은 UX 결함이 발견되어 긴급 정제한다:

1. **스티키 헤더(64px)에 의한 섹션 헤더 가림 현상**: GNB의 `성장 스토리`(`#story-5acts`) 및 `전문 파트너`(`#growth-partners`) 클릭 시 `scroll-margin-top` 부재로 섹션 타이틀 상단이 헤더에 가려짐.
2. **GNB 서브 메뉴 활성 상태(ScrollSpy) 미동기화**: 스크롤을 내려 스토리를 보고 있어도 GNB 메뉴는 계속 "서비스 소개"에만 불이 들어와 있음.
3. **3대 서브 탭 URL 해시 미연동**: 인트로 화면 하단의 3대 탭(작성 가이드 샘플, 잠금 미리보기, 요금 안내) 클릭 시 URL에 해시가 보존되지 않아 새로고침 시 상태 초기화.
4. **모바일 메뉴 닫힘 누락**: 모바일 햄버거 메뉴에서 링크 클릭 시 드롭다운이 자동으로 닫히지 않아 화면을 계속 가림.

---

## 2. 세부 개발 요구사항 (for QCWA)

### 2.1 CSS 스타일시트 스크롤 오프셋 추가 (`src/web/static/css/k_horizon_2027.css`) (최은정 UI/UX)
1. `html` 요소에 `scroll-behavior: smooth;` 및 `scroll-padding-top: 84px;` 기본 선언.
2. `.kh-scroll-target` 유틸리티 클래스 정의:
   ```css
   .kh-scroll-target {
     scroll-margin-top: 84px;
   }
   ```

### 2.2 인트로 템플릿 앵커 타깃 및 스크롤스파이·탭 동기화 (`src/web/templates/intro.html`) (최은정 UI/UX, 박준호 백엔드)
1. **섹션 앵커 태그에 `.kh-scroll-target` 적용**:
   - `<section id="story-5acts" class="kh-scroll-target">`
   - `<section id="growth-partners" class="kh-scroll-target">`
   - `<section id="section-pricing-plan" class="kh-scroll-target">`
2. **3대 서브 탭 인터랙션 및 URL 해시 양방향 바인딩**:
   - 탭 클릭 시 `history.replaceState(null, '', '#' + targetTab)` 또는 적절한 해시 업데이트.
   - 페이지 로드 시 URL 해시(`#sample-overview`, `#paywall-preview`, `#pricing-plan` 또는 `#section-pricing-plan`)를 읽어 해당 탭 즉시 활성화.
3. **GNB ScrollSpy (IntersectionObserver) 연동**:
   - 방문자 GNB 링크(`[data-nav-role="visitor"]`)들의 활성 클래스를 현재 뷰포트에 보이는 섹션에 맞추어 실시간 갱신:
     - 뷰포트 상단/히어로: "서비스 소개" 활성화
     - `#story-5acts`: "성장 스토리" 활성화
     - `#growth-partners`: "전문 파트너" 활성화
     - `#section-pricing-plan` 또는 `/pricing`: "요금제 안내" 활성화
4. **같은 페이지 내 부드러운 스크롤 인터셉트**:
   - `/intro` 내에서 `#story-5acts`, `#growth-partners` 클릭 시 불필요한 전체 페이지 새로고침을 방지하고 `scrollIntoView({ behavior: 'smooth' })`로 매끄럽게 이동.

### 2.3 공통 레이아웃 모바일 네비게이션 개선 (`src/web/templates/base.html`) (최은정 UI/UX)
- 모바일 드롭다운 메뉴 내비게이션 링크 클릭 시 `toggleMobileNav()`를 호출하여 메뉴를 자동으로 닫히도록 처리.

### 2.4 단위 테스트 스위트 확장 (`tests/test_visitor_portal.py`) (한지훈 QQAQC, 박준호 백엔드)
- GNB 4대 서브 링크의 타깃 해시 및 `kh-scroll-target` 클래스 렌더링 검증.
- 3대 서브 탭의 해시 식별자 및 활성화 정합성 테스트 추가.

---

## 3. 검수 기준 (for QQAQC - 한지훈)
1. `pytest tests/test_visitor_portal.py -v`: 신규 서브 메뉴 테스트 포함 전원 통과.
2. `pytest tests/ --ignore=tests/audit -q`: 234개+ 전수 통과 (0 failed).
3. `python -m tests.audit.audit_runner`: 100.0/100.0 (GATE APPROVED).
4. 크롬 브라우저 실물에서 GNB 각 메뉴 클릭 시 헤더 가림 없이 섹션 상단이 84px 여백을 두고 시원하게 안착하는지 시각 검증.

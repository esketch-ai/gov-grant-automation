# REQ-039: 한국어 가독성 극대화 및 초소형 폰트(10~11px) 전면 퇴출·폰트 스케일 고도화

- **요청 일시**: 2026-10-28
- **발신**: `GCWA` (총괄 아키텍트 / PM)
- **수신**: `QCWA` (개발 전담 워크스페이스: 박준호 CPO, 최은정 UI/UX, 이승엽 BM엔진, 정민재 DB, 김도윤 포털수집)
- **참조 및 검수**: `QQAQC` (검수 전담: 한지훈)
- **우선순위**: HIGH (사용자 가독성 긴급 피드백)

---

## 1. 배경 및 개선 목표
사용자 피드백(*"글자 크기가 작은 글씨들은 안 보이지 않나?"*)에 따라, 화면 곳곳에 산재해 있던 초소형 폰트(`10px`, `11px`)와 저대비 텍스트(`text-slate-400`)를 전면 색출하여 제거한다.
대한민국 디지털정부 서비스 가이드라인(KRDS) 및 웹 접근성 지침(KWCAG 2.1 AA)에 부합하도록 한글 음절 판독 최적 폰트 스케일(최소 12px~14px)을 수립하고 고대비 명도비를 확보한다.

---

## 2. 세부 개발 요구사항 (for QCWA)

### 2.1 CSS 스타일시트 폰트 스케일 상향 (`src/web/static/css/k_horizon_2027.css`) (최은정 UI/UX)
1. **정부 스트립 (`.krds-gov-banner`)**: `font-size: 11px` ➔ `font-size: 12.5px`, 색상 `#94A3B8` ➔ `#CBD5E1`.
2. **역할 뱃지 (`.kh-role-badge`)**: `font-size: 11px` ➔ `font-size: 12px`, 패딩 및 선명도 강화.
3. **GNB 내비게이션 링크 (`.kh-nav-item`)**: `font-size: 12.5px` ➔ `font-size: 13.5px` (가독성과 클릭 영역 확대).
4. **역할 스위처 버튼 (`.kh-role-pill`)**: `font-size: 12px` ➔ `font-size: 13px`, 자간 및 가독성 최적화.
5. **CTA 버튼 (`.kh-btn-cta`)**: `font-size: 12px` ➔ `font-size: 13px`, 볼드 가중치 유지.
6. **공통 뱃지 (`.kh-badge`)**: `font-size: 11px` ➔ `font-size: 12px`, 패딩 조정.
7. **디데이 뱃지 (`.krds-dday`)**: `font-size: 11px` ➔ `font-size: 12px`.

### 2.2 템플릿 내 초소형 인라인 클래스(`text-[10px]`, `text-[11px]`) 전면 교체 (최은정 UI/UX, 박준호 백엔드)
1. **10px/11px 클래스 전면 퇴출**:
   * 태그/뱃지: `text-[10px]`, `text-[11px]` ➔ `text-xs` (`12px`) 및 `font-semibold`.
   * 카드 라벨/메타데이터: `text-[11px]` ➔ `text-xs` (`12px`) 및 `text-slate-600` 이상 명도 확보.
   * 본문 설명/스토리 인용구/파트너 상세: `text-xs` (`12px`) ➔ `text-sm` (`14px`)으로 상향하여 시원하고 편안한 한글 읽기 환경 조성.
2. **대상 템플릿**:
   * `base.html`, `intro.html`, `biz_dashboard.html`, `vault.html`, `projects.html`, `tailor.html`, `announcements.html`, `matches.html`, `dashboard.html`, `admin_platform.html`, `governance_partner.html`, `audit_logs.html`, `audit.html`, `items.html`, `portals.html`, `logs.html`.

### 2.3 명도 대비 및 가독성 강화 (최은정 UI/UX, 정민재 DB)
* 밝은 배경 위 흐릿한 `text-slate-400`을 `text-slate-600` 또는 `text-slate-700`으로 교체하여 WCAG AA 4.5:1 이상 대비 확보.

---

## 3. 검수 기준 (for QQAQC - 한지훈)
1. `grep -rnE "text-\[(10|11)px\]" src/web/templates/` 검색 결과 0건.
2. `pytest tests/ --ignore=tests/audit -q`: 234개 전수 통과 (0 failed).
3. `python -m tests.audit.audit_runner`: 100.0/100.0 (GATE APPROVED).
4. 크롬 브라우저 실시간 확인을 통해 데스크톱/랩탑 환경에서 모든 텍스트가 안경 없이도 또렷하게 읽히는지 시각 검증.

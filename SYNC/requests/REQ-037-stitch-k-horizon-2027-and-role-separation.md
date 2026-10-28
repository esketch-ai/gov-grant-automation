# REQ-037: Google Stitch 기반 K-Horizon 2027 한국형 디자인 시스템 대개편, 3대 권한별 분리 서비스 및 인트로 메인화

- **요청 일시**: 2026-10-28
- **발신**: GCWA (5인 20년 경력 디자인 전문가 협의체 총괄 아키텍트)
- **수신**: QCWA (개발 전담 워크스페이스) / QQAQC (검수 전담 워크스페이스)
- **연동 Google Stitch 프로젝트**: `projects/6532140447067945829` (`SSHAI-CWA K-Horizon 2027 Korean B2B SaaS` / Design System Asset: `assets/60b7c8e07043493594e9d93dcab37860`)

## 1. 작업 배경 및 핵심 요구사항
1. **Google Stitch 기반 2026·2027년형 한국형 디자인 재편 (`K-Horizon 2027 · Obsidian Aurora Enterprise`)**:
   - 20년 경력 디자인 전문가 5인 협의체가 확정한 2026·2027년형 한국형 B2B SaaS 디자인 토큰(`Pretendard Variable` + `Plus Jakarta Sans` + `JetBrains Mono` 고정폭 숫자 `tabular-nums`, Obsidian Aurora `#0B1120` ~ `#1E3A8A` + Crisp Hanji `#F8FAFC` 듀얼 표면, Bento Grid 2.0, KRDS 접근성)을 전 화면에 일괄 적용한다.
2. **하드코딩된 디자인 및 데이터 전면 제거 · 공통화 (Zero-Hardcoding)**:
   - 기존 각 템플릿(`intro.html`, `biz_dashboard.html`, `admin_platform.html`, `audit_logs.html`, `base.html`)에 흩어져 있던 하드코딩 CSS와 데이터 구조를 제거하고 다음 3대 SSOT 모듈로 완전 공통화한다:
     - `src/web/design_system.py`: 디자인 토큰(`K_HORIZON_2027_TOKENS`), Stitch 프로젝트/스크린 메타데이터(`STITCH_DESIGN_METADATA`), 3대 권한별 포털 정의(`ROLE_PORTALS`), 5막 스토리(`STORY_5ACTS`), 4단계 성장 로드맵(`GROWTH_STAGES`), 5대 컨설팅 파트너(`PARTNER_5PILLARS`), 5대 BM 트랙(`BM_5TRACKS`), 4단계 요금제(`PRICING_4TIERS`) SSOT.
     - `src/web/static/css/k_horizon_2027.css`: 모든 `--kh-*` 및 하위 호환 `--krds-*` CSS 커스텀 프로퍼티와 공통 컴포넌트 클래스(`.kh-gnb`, `.kh-role-switcher`, `.kh-role-pill`, `.kh-hero-obsidian`, `.kh-bento-grid`, `.kh-card`, `.kh-kpi-card`, `.kh-badge`, `.kh-btn`, `.kh-stitch-preview`) 통합 스타일시트.
     - `src/web/templates/components/kh_macros.html`: 공통 Jinja2 UI 매크로(`kh_section_header`, `kh_kpi_card`, `kh_badge`, `kh_role_banner`, `kh_stitch_showcase`).
3. **권한별 서비스 분리 (`visitor` 초기 유입자 / `subscriber` 유료 사업자 / `admin` 슈퍼어드민)**:
   - `GET` 쿼리(`?role=visitor|subscriber|admin`), 쿠키(`sshai_role`), 그리고 `POST /api/auth/role` API를 통해 현재 권한 모드를 판별하고, `base.html` 상단 GNB에서 권한별로 분리된 전용 메뉴와 역할 배지, 그리고 원클릭 권한 전환 스위처(Role Portal Switcher)를 제공한다.
   - `GET /api/design-system` 엔드포인트를 추가하여 K-Horizon 2027 디자인 토큰, Stitch 메타데이터, 3대 권한 포털 구성을 JSON으로 반환한다.
4. **인트로 화면의 진정한 메인화 (`GET /` → `/intro`)**:
   - `src/web/app.py`의 `GET /` 라우트가 `/dashboard` 대신 `/intro`로 `307 Temporary Redirect` 하도록 변경한다.
   - `tests/test_web_admin.py`의 `test_root_redirect`가 `/intro` 리다이렉트를 검증하도록 업데이트하고, `tests/audit/agents/web_qa.py`가 `/` (리다이렉트 후 `/intro`)에서 검사하는 키워드(`"2026"`, `"대시보드"`, `"파이프라인 수동 실행"`)가 권한 분리 상태에서도 100% 호환되도록 보장한다.

## 2. 검증 기준 (QQAQC)
1. `pytest tests/ --ignore=tests/audit -q`: 신규 권한 분리·메인 인트로·디자인 시스템 테스트를 포함하여 전수 통과 (0 failed).
2. `python -m tests.audit.audit_runner`: **100.0 / 100.0 (Raw: 140.0/140.0) · GATE STATUS: APPROVED** 유지.

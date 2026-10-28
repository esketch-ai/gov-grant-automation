# [REQ-034] Round 1 (1차 다각도 전수 검수 기반) 3대 페르소나 UI/UX·기능·버튼·라우팅 무결성 개편 명세

- **발행 주체**: `GCWA` (Chief Coordinator & Enterprise Architect)
- **기반 보고서**: `storage/qqaqc_round1_persona_audit_report.md` (`QQAQC` Round 1 전수 검수 결과 12대 결함)
- **수행 주체**: `QCWA` (`term_4f82f7f5-f531-4b73-8bd6-6c55e04948aa`)

---

## 1. 필수 수정 항목 (12대 결함 전량 해결)

### Step 1: 시드 DB(`storage/grant_master.db`) 복원 및 `tests/test_commercial_saas_v2.py` 격리
1. `git checkout -- storage/grant_master.db` 를 실행하여 삭제된 2026 공고 시드 DB를 즉시 복원하라.
2. `tests/test_commercial_saas_v2.py` 에서 `Path("storage/grant_master.db").unlink(...)` 코드를 전량 제거하고, 모든 테스트 함수가 `tmp_path` 픽스처(`db_path = tmp_path / "test_comm.db"`)를 사용하도록 수정하라. 또한 `TestClient(app)`으로 `/intro`, `/pricing`, `/dashboard/biz`, `/admin/platform`, `/admin/audit-logs`, `/api/billing/checkout`, `/api/export/hwpx`, `/api/export/docx`, `/api/admin/audit/verify` HTTP 200 및 보안 헤더를 검증하는 통합 테스트를 추가하라.

### Step 2: `src/web/app.py` 보안 헤더 미들웨어 + 10대 상용 라우트 완벽 등록
1. `src/web/app.py`에 `REQ-030` 보안 헤더 미들웨어(`Strict-Transport-Security: max-age=31536000; includeSubDomains`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`)를 등록하라.
2. 다음 라우트들을 `src/web/app.py`에 정확히 등록하라:
   - `GET /intro` 및 `GET /pricing`: `intro.html` 렌더링 (`active_page="intro"`)
   - `GET /billing/checkout`: 쿼리 파라미터(`tier`, `cycle`)를 받아 `intro.html` 또는 결제 안내를 렌더링
   - `GET /dashboard/biz`: `CommercialService(_get_db())`의 `get_5kpi()`, 현재 테넌트 정보(`credit_balance`, `subscription_tier`, `biz_model`), `BudgetRuleEngine().allocate(100_000_000)` 샘플 예산표를 컨텍스트로 전달하여 `biz_dashboard.html` 렌더링
   - `GET /admin/platform`: `get_5kpi()`, 전체 테넌트 리스트(`tenants`), 구독 현황을 전달하여 `admin_platform.html` 렌더링
   - `GET /admin/audit-logs`: `audit_logs` 테이블 전체 행과 `verify_audit_chain()` 결과를 전달하여 `audit_logs.html` 렌더링
   - `POST /api/billing/checkout`: 구독/결제 실행(`subscribe` + `gateway.charge`) 및 크레딧 반영 후 `{"status": "success", "ok": True, ...}` 반환
   - `POST /api/billing/topup`: Top-Up 크레딧 충전(`topup_credits`) 실행 후 새 잔액 반환
   - `GET` & `POST /api/export/hwpx`, `GET` & `POST /api/export/docx`: `export_hwpx_bytes` / `export_docx_bytes` 생성 및 반환 (블러 페이월 Free 티어 요청 시 `tier=="free"`면 HTTP 402 반환 지원)
   - `GET` & `POST /api/admin/audit/verify`: `verify_audit_chain()` 결과(`{"status": "success", "ok": result["ok"], "verified_count": result.get("verified_count", 0), "logs": rows}`) 반환
   - `POST /api/admin/tenants`: 슈퍼어드민에서 신규 테넌트/티어/사업자번호 등록 또는 상태 변경(`ACTIVE`/`PAST_DUE`/`SUSPENDED`) 처리

### Step 3: `src/web/templates/intro.html` (초기 유입자 입장) 결함 수정 및 5막 스토리 고도화
1. HTML 문법 오류 수정 (`h-[420px]`, `<video autoplay muted loop playsinline poster="/static/media/intro/hero_fatigue_vs_winning_edge.jpg">`, 제3막 `alt="옆자리 코파일럿 가이드"`, 71행 닫는 따옴표 `"` 수정).
2. `.tab-content { display: none; } .tab-content.active { display: block; }` 스타일을 명시하여 3탭 전환(`창업진흥원 초기창업패키지` / `중기부 디딤돌 R&D` / `지자체 스케일업` 샘플 변환 뷰 + 블러 페이월 프리뷰 + 요금제)이 완벽히 동작하게 하라.
3. **5막 공감 스토리보드 서사 보강**:
   - 제1막~제4막 각각의 공감 스토리 문단을 풍부하게 넣고,
   - **제5막(Act 5)**에 ① **성장의 길잡이 3단계 로드맵(`Step 1 초기·예비 창업` → `Step 2 성장·도약` → `Step 3 스케일업·글로벌`)**, ② **5대 검증된 파트너 생태계 배지(`📊 회계·세무·정산`, `📣 마케팅·그로스`, `🎬 브랜드·광고`, `💼 투자사(AC/VC)`, `⚖️ 법률·특허·노무`)**, ③ **하이라이트 철학 배너(`"사업은 인맥이고, 그 인맥을 위해 본연의 사업에 집중하세요. 그러면 인맥과 사업운은 따라옵니다."`)**를 명확히 표시하라.
4. **모든 버튼 및 토글 100% 동작 연결**:
   - `#annual-toggle` 체크박스 클릭 시 Growth(`39,000원 → 31,200원/월`), Scale-Up(`120,000원 → 96,000원/월`), Agency(`300,000원 → 240,000원/월`) 가격 및 VAT 10% 안내가 즉시 실시간 전환되게 하라.
   - 요금제 카드의 `시작하기`/`구독하기` 버튼 클릭 시 실제 `subscribePlan(tier)` JS 함수가 `/api/billing/checkout`을 호출하고 결과를 토스트/알림으로 보여준 뒤 `/dashboard/biz`로 이동할 수 있게 연결하라.

### Step 4: `biz_dashboard.html`, `admin_platform.html`, `audit_logs.html`, `base.html` 전수 수정
1. `biz_dashboard.html`:
   - 84행 `id="total-tenant-count"` 오타 수정 및 서버 컨텍스트 변수(`{{ kpi.mrr }}` 등) 바인딩.
   - **5대 BM 전환 탭(`초기창업·스타트업`, `기술·R&D`, `제조·스마트공장`, `소상공인·로컬`, `에이전시·컨설팅`)** 추가 및 클릭 시 BM별 맞춤 가이드/KPI 전환 JS 구현.
   - `충전하기` 버튼 클릭 시 `/api/billing/topup`을 호출하여 즉시 화면의 `#credit-balance`를 증가시키는 `topupCredits()` JS 함수 연결.
   - **HWPX / DOCX 공식 양식 다운로드 버튼** 추가 및 `/api/export/hwpx`, `/api/export/docx` 호출 다운로드 동작 구현.
2. `admin_platform.html`:
   - 68~72행의 잘못된 Angular `*ngFor` 및 `||` 문법을 올바른 Jinja2 `{% for tenant in tenants %} ... {{ tenant.company_name or tenant.id }} ... {% endfor %}` 문법으로 수정하라!
   - `테넌트 생성 / 티어 변경` 버튼 클릭 시 `/api/admin/tenants`를 호출하여 즉시 반영되는 `createOrUpdateTenant()` JS 함수를 연결하라.
3. `audit_logs.html`:
   - 서버에서 전달된 `audit_logs`를 `{% for log in audit_logs %}`로 초기 렌더링하고, `verifyChain()` 클릭 시 `/api/admin/audit/verify`와 연동되어 무결성 검증 배지 및 로그 테이블이 정상 표시되게 하라.
4. `base.html`:
   - 상단 네비게이션 바에 `/intro` (`스토리 소개`), `/dashboard/biz` (`BM 대시보드`), `/admin/platform` (`플랫폼 관제`), `/admin/audit-logs` (`해시 감사로그`) 링크를 추가하라(기존 QA Swarm 체크 문자열은 절대 건드리지 말고 보존).

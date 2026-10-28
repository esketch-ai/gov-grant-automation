# REQ-032 (v2.0): 실전 유료화 B2B SaaS 전면 대개편 (블러 페이월, 크레딧 원장, HWPX/예산엔진, PG 정기결제/환불정산, BM 대시보드, 슈퍼어드민, 해시체인 감사로그)

| 메타데이터 | 내용 |
|---|---|
| **ID** | `REQ-032` (v2.0 실전 유료화 검수 반영본) |
| **제목** | 실전 수익형 B2B SaaS 대개편 (인트로/블러페이월, 4-Tier & Top-Up 과금, HWPX/예산 자동편성, 토스 빌링/일할/환불, 5대 BM 대시보드, 슈퍼어드민, 해시체인 감사로그) |
| **총괄 조정** | `GCWA` |
| **담당 워크스페이스** | `QCWA` (`term_4f82f7f5-f531-4b73-8bd6-6c55e04948aa`) |
| **검증 워크스페이스** | `QQAQC` (`term_5eeca898-bbb5-429a-98e8-c10e5133661e`) |
| **우선순위** | `CRITICAL` (실전 상용 유료화 핵심 아키텍처) |
| **상태** | `QUEUED` |

---

## 1. 설계 검수 반영 핵심 요약 (v1.0 ➔ v2.0 교정 사항)
1. **먹튀 방지 블러 페이월 (Blurred Paywall)**: 무료 회원(`Free`)은 공고 매칭, 25대 자격 진단, **사업계획서 1장(문제인식)까지만 열람 가능**하며, **2장(기술개발)~4장(예산표) 및 HWPX/DOCX 다운로드**는 반투명 블러(Glassmorphism Paywall)로 잠금 처리하여 즉각적인 유료 결제 전환 유도.
2. **어뷰징 차단 & 유닛 이코노믹스 방어**:
   - **1테넌트 = 1사업자등록번호 Hard-Lock**: 타 업체 대행 어뷰징 원천 차단 (컨설팅사는 `Agency` 플랜으로만 다중 사업자 관리 가능).
   - **크레딧 원장(`credit_ledger`) & 충전팩(Top-Up)**: 무제한 생성 폐지 ➔ 플랜별 월간 정량 크레딧(Growth 500, Scale-Up 1,500) + 부족 시 단건 충전팩(300크레딧 1.9만 원) 과금.
3. **실무 제출용 HWPX/DOCX 변환 & 사업비 예산 룰 엔진**:
   - 마크다운뿐만 아니라 정부과제 표준 표(요약표, 추진일정, 연구원 편성표)가 포함된 **DOCX/HWPX 포맷 내보내기** 제공.
   - **부처별 사업비 편성 계산기**: 정부출연금 대비 민간부담금(현금 10% 이상, 현물 비율) 법정 룰 자동 계산 및 위반 경고.
4. **실전 결제 생명주기(Billing Lifecycle)**:
   - VAT 10% 별도/합산 정산, 중도 업그레이드 **일할 계산(Proration)**, 미납 시 **Dunning 재시도(+1/+3/+7일) 및 `PAST_DUE` 상태 머신**, 전자상거래법 기준 **사용 크레딧/다운로드 차감 후 부분 환불 계산기**.
5. **해시 체인 불변 감사로그 (`audit_logs`)**:
   - `prev_hash` + `curr_hash` (SHA-256 연쇄 해시) 구조로 DB 직접 조작 시 무결성 훼손을 즉시 탐지하는 엔터프라이즈 감사로그 구축.

---

## 2. 세부 개발 요구사항 (for QCWA)

### A. DB 스키마 확장 (`src/common/db.py`)
1. `tenants` 확장: `biz_reg_no` (고유 사업자번호 Hard-Lock), `biz_model` (5대 BM), `subscription_tier` (`free`/`growth`/`scaleup`/`agency`), `credit_balance` (정수).
2. `subscriptions`: `id`, `tenant_id`, `plan_code`, `billing_cycle` (`monthly`/`annual`), `supply_price`, `vat_amount`, `status` (`ACTIVE`/`PAST_DUE`/`CANCELED_PENDING`/`SUSPENDED`), `current_period_start`, `current_period_end`, `dunning_retry_count`, `billing_key_enc`.
3. `payments`: `id`, `tenant_id`, `subscription_id`, `payment_type` (`SUBSCRIPTION`/`TOPUP`/`PRORATION`), `supply_amount`, `vat_amount`, `total_amount`, `refunded_amount`, `status`, `tax_invoice_status`, `receipt_url`, `paid_at`.
4. `credit_ledger`: `id`, `tenant_id`, `delta`, `balance_after`, `reason`, `project_id`, `created_at`.
5. `proposal_snapshots`: `id`, `project_id`, `tenant_id`, `version_no`, `encrypted_sections_blob` (AES-256), `encrypted_budget_blob`, `created_at`.
6. `audit_logs`: `id`, `tenant_id`, `actor_user_id`, `category`, `action`, `ip_address`, `prev_hash`, `curr_hash`, `created_at`.

### B. 과금·정산·예산 코어 엔진 (`src/billing/commercial_service.py` & `src/generator/budget_engine.py`)
1. **요금제 & 크레딧 관리**:
   - 4-Tier 요금제 정의 (`free`, `growth`, `scaleup`, `agency`) 및 월간/연간(20% 할인) 공급가액·부가세 계산.
   - 크레딧 차감(`consume_credits`) 및 Top-Up 충전(`topup_credits`) 트랜잭션.
   - **블러 페이월 가드(`check_paywall_access`)**: `free` 티어인 경우 섹션 2 이상 본문 마스킹/블러 처리 및 HWPX/DOCX 다운로드 차단(402 Payment Required 반환).
2. **일할 계산(Proration) & 환불 정산기(`calculate_refund`)**:
   - 플랜 업그레이드 시 잔여일수 비례 차액 산출.
   - 환불 요청 시 `실결제액 - (사용일수 일할액 + 사용크레딧*100원 + 위약금 10%)` 정확히 산출.
3. **정부과제 사업비 예산 자동 편성기 (`BudgetRuleEngine`)**:
   - 총 정부출연금 입력 시 민간부담금(현금/현물), 인건비, 연구장비비, 위탁연구비 비율 자동 산출 및 규정 위반 여부 판정.

### C. 상용 화면 4대 뷰 구축 (`src/web/templates/` & `src/web/app.py`)
1. **상용 인트로 & 라이브 샘플 뷰 (`GET /intro`, `intro.html`)**:
   - KRDS 정부 표준 신뢰 배너 + Zero-Retention 무보관 보증.
   - **Before & After 라이브 샘플 뷰어**: 3대 업종 샘플 클릭 시 일반 메모가 정부과제 개조식 제안서 + 예산표로 변환되는 실시간 시연(1장은 선명하게 공개, 2장 이후는 Blurred Paywall 시연).
   - 월간/연간(20% 할인) 실시간 토글 요금제 카드 & ROI 비교 계산기(외주 컨설팅 300만 원 vs 월 3.9만 원).
2. **사업주 5대 BM 맞춤형 대시보드 (`GET /dashboard/biz`, `biz_dashboard.html`)**:
   - 상단 구독/크레딧 원장 HUD 미터기 + `[⚡ 크레딧 충전]` / `[🚀 플랜 업그레이드]` 원클릭 결제 모달.
   - 5대 BM(`ict_deeptech`, `smart_mfg`, `youth_women`, `local_creator`, `social_esg`) 전환 및 BM별 특화 KPI Bento Grid.
   - 내장 **[💰 정부과제 사업비 자동 편성 계산기]** 인터랙티브 위젯.
3. **플랫폼 최고 관리자 대시보드 (`GET /admin/platform`, `admin_platform.html`)**:
   - MRR, ARR, 순매출, 테넌트별 크레딧 소모량/마진율 모니터링.
   - 테넌트 플랜 직권 변경, 크레딧 수동 지급, 정지/해제 제어, 결제/환불 원장 조회.
4. **불변 해시체인 감사로그 뷰 (`GET /admin/audit-logs` 또는 슈퍼어드민 내 탭)**:
   - 전체 감사로그 스트림 조회 및 **`verify_audit_chain()` 무결성 검증 버튼** (해시 체인 100% 정상 여부 실시간 검증).

---

## 3. 검증 및 테스트 요구사항 (for QQAQC)
1. **단위 및 통합 테스트**: `tests/test_commercial_saas_v2.py`
   - 무료 티어 블러 페이월(섹션 1 공개, 섹션 2+ 잠금 및 다운로드 402 차단) 검증.
   - 크레딧 차감, 잔액 부족 시 차단, Top-Up 충전 후 정상 재개 검증.
   - 플랜 업그레이드 일할 계산(Proration) 및 전자상거래법 부분 환불 정산 수식 정확도 검증.
   - 정부과제 예산 편성기(현금/현물 비율) 검증.
   - 해시 체인 감사로그(`audit_logs`) 위변조 탐지(`verify_audit_chain`) 검증.
2. **QA Swarm 무결성 감사**:
   - `python tests/audit/audit_runner.py` 140.0/140.0 만점 유지 확인.

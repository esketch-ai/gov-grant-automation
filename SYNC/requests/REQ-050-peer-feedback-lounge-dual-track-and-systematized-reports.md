# REQ-050: 동료 창업자 피드백 라운지 독립 메뉴 서비스화, 무료/유료 듀얼 트랙, 소셜 계정 연계 리워드 지급 및 3대 목적별 결과 보고서 체계화

- **요청 일시**: 2026-10-29
- **발신**: `GCWA` (총괄 아키텍트 / PM)
- **수신**: `QCWA` (개발 전담 워크스페이스: 박준호 CPO, 최은정 UI/UX, 이승엽 BM엔진, 정민재 DB, 김도윤 연동)
- **참조 및 검수**: `QQAQC` (검수 전담 워크스페이스: 한지훈)
- **우선순위**: CRITICAL
- **전제(Prerequisite)**: REQ-047 (바이브코딩 검증 엔진), REQ-048 (SSOT 정본화), REQ-049 (글로벌 포털)

---

## 1. 배경 및 목적

사용자 대표의 직접 피드백에 따라 기존 바이브코딩 프로토타입 검증 시스템의 과장·왜곡 요소를 전면 배제하고, 서비스와 비즈니스 모델을 현실 사업 관행에 맞춰 완벽히 재설계·체계화한다.

1. **과장·강요 텍스트 정제 및 개념화**:
   - `"60초 유효 체류시간 락"`과 같은 강요형 표현 배제 ➔ `"최소한의 성실 테스트 시간"`으로 개념 정립.
   - `"7:3 수익배분"`의 노골적 수치 표출 배제 ➔ `"참여 테스터 리워드 정산 체계"`로 상생 가치 전달.
   - `"심사위원 고인/공인 서식"` 등 허위 사실 배제 ➔ `"사업계획서 시장 검증(Traction) 첨부 증빙"` 및 `"협약 감리용 실증 결과보고서"`로 명확히 포지셔닝.
2. **독립 메뉴 서비스화 (`/feedback-lounge`) & 듀얼 트랙 온보딩**:
   - 인트로에는 최신 6개 대표 아이템만 슬라이싱 노출하고, 전체 서비스는 독립 메뉴 라운지(`/feedback-lounge`)로 제공.
   - **무료 요청(커뮤니티 품앗이)**: 무결제 즉시 등록, 동료 피드백 상호 교환.
   - **유료 요청(보증 검증)**: 목표 테스터 수 설정, 안전 결제 온보딩, 수당 보증 지급.
3. **간편로그인(소셜 OAuth) 계정 연계 & 1인 1검증 중복 차단**:
   - 카카오/네이버/구글 소셜 계정 연계를 통한 테스터 신분 식별 및 포인트 지갑 적립 체계.
   - `UNIQUE(campaign_id, tester_id)` 제약을 통한 동일 캠페인 중복 참여 원천 방지.
4. **결과 보고서 3대 실무 목적별 체계화**:
   - **[모드 1] 과제 발표·선정용 (Traction)**: 1-Slide Executive 요약, 지불용의율(WTP %), NPS 순추천 지수, 진성 고객 인용구, 원클릭 발표 요약 복사.
   - **[모드 2] 정부과제 협약 감리·결과보고용 (Milestone)**: 전담기관 감리 규격, 표본 진본성 100%, 사용자 발견 결함 조치 계획서(Remediation Plan), SHA-256 전자 날인.
   - **[모드 3] 기업 실무 제품 개선 로드맵 (Sprint Backlog)**: VOC 블로커 기반 P0~P2 결함/개선 우선순위 매트릭스 및 실무 백로그 로드맵.
   - 다채널 내보내기: A4 공문 인쇄/PDF 저장(`@media print`), 전수 피드백 UTF-8 BOM CSV 다운로드.

---

## 2. 세부 개발 요구사항 (for QCWA)

### 2.1 독립 메뉴 서비스 및 듀얼 트랙 라운지 구축 (최은정 UI/UX, 박준호 CPO)
1. **독립 서비스 라운지 (`src/web/templates/feedback_lounge.html`)**:
   - 상단 4대 라운지 통계 카드, 트랙별 필터링(`전체`, `유료 보증 검증`, `무료 커뮤니티 품앗이`).
   - 캠페인 신규 등록 모달 (`#registrationModal`): 무료 트랙 즉시 등록 vs 유료 트랙 목표 인원/결제 연동.
   - 테스터 참여 모달 (`#testerModal`): 소셜 간편인증 안내, 실시간 최소 체류시간 측정, 3단계 구조화 평가.
2. **인트로 및 GNB 연동 (`src/web/templates/intro.html`, `base.html`, `biz_dashboard.html`)**:
   - 인트로 메인에서는 최신 6개 캠페인만 엄선 노출하고, `[피드백 라운지 전체보기 →]` CTA로 유기적 연결.
   - GNB 상단 메뉴에 `피드백 라운지` 정식 서비스 링크 탑재.

### 2.2 소셜 계정 연계 신분 인증 & 리워드 포인트 지급 로직 (김도윤 연동, 정민재 DB)
1. **소셜 OAuth 계정 매핑 및 1인 1검증 무결성 (`src/common/db.py`)**:
   - `prototype_campaigns`에 `request_type`(`PAID`|`FREE`) 필드 반영.
   - `prototype_feedbacks`에 `oauth_provider`, `oauth_account_id` 필드 추가 및 `UNIQUE(campaign_id, tester_id)` 복합 고유 제약 설정.
   - `has_prototype_feedback(campaign_id, tester_id)` 메서드를 통한 실시간 중복 차단.
2. **리워드 포인트 적립 체계 (`src/prototype/validation_engine.py`)**:
   - 테스터가 최소 체류시간을 충족하고 피드백을 제출하면 유료 캠페인의 경우 지정된 테스터 수당이 해당 계정 포인트로 자동 적립.
   - 무료 캠페인의 경우 리워드 0원 적립 및 품앗이 기여도 카운트.

### 2.3 3대 목적별 결과 보고서 데이터 합성 및 UI 체계화 (이승엽 BM, 최은정 UI)
1. **3대 패키지 합성 엔진 (`src/prototype/validation_engine.py`)**:
   - `pitch_pack`: 1-Slide Traction Headline, `wtp_ratio`, `promoter_ratio`, `highlight_quotes`, `core_metrics_summary`.
   - `audit_pack`: `compliance_status`, `sample_validity_rate`, `remediation_plan` (카테고리/빈도/보완계획/담당부서/완료목표).
   - `roadmap_pack`: `priority_backlog` (P0 긴급 결함, P1 UX 개선, P2 성능 개선 매트릭스).
2. **인터랙티브 멀티 뷰 템플릿 (`src/web/templates/prototype_report.html`)**:
   - `[전체 종합]`, `[모드 1: 과제 발표용]`, `[모드 2: 협약 감리용]`, `[모드 3: 실무 로드맵]` 4개 인터랙티브 탭 전환.
   - `[📋 발표 요약 복사]`: 1슬라이드 핵심 요약 텍스트 클립보드 원클릭 복사.
   - `[📥 전수 데이터 CSV]`: 감리 제출 및 엑셀 정밀 분석을 위한 UTF-8 BOM CSV 생성 및 다운로드.
   - `[🖨️ A4 인쇄 / PDF 저장]`: `@media print`를 통한 완벽한 A4 공문 양식 출력 지원.

---

## 3. 검수 기준 (for QQAQC - 한지훈)

1. `python -m compileall src tests`: 컴파일 오류 0건 (Exit Code 0).
2. `pytest tests/test_prototype_validation_engine.py -v`: 신규 및 확장 검증 테스트 14건 전수 통과.
3. `pytest tests/ --ignore=tests/audit -q`: 전체 285개 이상 테스트 100% 통과 (0 failed).
4. `python -m tests.audit.audit_runner`: 7대 전문 감사 에이전트 140.0/140.0 (100.0/100.0, APPROVED) 만점.
5. 금지/과장 어휘 검증: `60초 체류 락`, `심사위원 공인 서식` 템플릿 0건 검증.
6. 로컬 데몬 8081 포트 대상 `/feedback-lounge` 및 `/prototype/report/{campaign_id}` 정상 렌더링 (HTTP 200).

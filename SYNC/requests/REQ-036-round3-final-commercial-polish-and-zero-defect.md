# REQ-036: Round 3 (3차 최종) 상용 유료 서비스 폴리싱 및 무결점 완결 명세서

- **발행처**: `GCWA` (Chief Coordinator & Enterprise Architect)
- **수신처**: `QCWA` (Lead Implementation Engineer)
- **검수처**: `QQAQC` (30-Year QA/Security/UX Audit Swarm)
- **근거 리포트**: `storage/qqaqc_round3_persona_audit_report.md`

---

## 1. Round 3 (3차 최종 고도화) 5대 반영 목표

1. **[페르소나 A · 초기 유입자 (`intro.html`)] 히어로 CTA 버튼 2종 및 제1~5막 상세 서사 캡션 추가**
   - 히어로 섹션 하단에 즉시 진입 버튼(`<a href="/vault" class="krds-btn primary">1분 무료 과제 매칭 시작하기</a>`, `<button type="button" class="krds-btn ghost" onclick="scrollToPricing()">요금제·샘플 바로 보기</button>`) 배치
   - 제1막~제5막 각 카드에 대표님의 현실과 해결 가치를 담은 2줄 스토리 서사 문구 추가
2. **[페르소나 A · 초기 유입자 (`intro.html`)] 블러 페이월(`tab-paywall-preview`) 실제 `filter: blur(5px)` 시각 프리뷰 및 잠금 해제 CTA 버튼**
   - Section 2~4(기술개발·추진체제·예산 산출표) 샘플 블록에 실제 CSS `filter: blur(5px); user-select: none;` 적용 및 오버레이 잠금 해제 버튼(`onclick="subscribePlan('growth')"`) 배치
3. **[페르소나 B · 유료 사업자 (`biz_dashboard.html`)] 서버 KPI/크레딧 Jinja2 동적 바인딩 및 5대 BM 맞춤 전략 안내 배너(`#bm-strategy-banner`)**
   - `#kpi-mrr`, `#kpi-arr`, `#kpi-tenants`, `#kpi-credits`, `#kpi-net`, `#credit-balance`에 서버 컨텍스트(`{{ kpi.mrr if kpi else 0 }}` 등) 바인딩
   - 5대 BM 탭 클릭 시 활성 탭 하이라이트 및 선택된 BM 트랙별 맞춤 정부과제 추천·가점 전략 안내 배너(`#bm-strategy-banner`) 실시간 전환
4. **[페르소나 C · 플랫폼 관리자 (`admin_platform.html`)] 관리자 KPI 바인딩 및 테넌트별 상태 제어(`activate` / `suspend` / `past_due`) 버튼**
   - `#admin-mrr`, `#admin-arr`, `#admin-tenants`, `#admin-active`에 서버 KPI 및 `{{ tenants|length if tenants else 0 }}` 바인딩
   - 각 테넌트 행에 `활성화(activate)`, `일시정지(suspend)`, `미납(past_due)` 원클릭 제어 버튼(`onclick="changeTenantStatus(...)"` -> `POST /api/admin/tenants`) 추가
5. **[페르소나 C · 플랫폼 관리자 (`audit_logs.html`)] 감사로그 건수 초기 바인딩 및 `verifyChain()` 테이블 실시간 렌더링**
   - `#audit-count` 초기값을 `{{ audit_logs|length if audit_logs else 0 }}`으로 표시하고, `verifyChain()` 실행 시 반환된 `data.logs`를 `#audit-table` 행으로 렌더링 및 `#audit-count` 갱신

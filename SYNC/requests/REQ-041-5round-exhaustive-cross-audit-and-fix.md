# REQ-041: 5회차 반복 전수 검수 프로토콜 및 자가 치유(Self-Healing) 결함 수정

- **요청 일시**: 2026-10-28
- **발신**: `GCWA` (총괄 아키텍트 / PM)
- **수신**: `QCWA` (개발 전담: 박준호 CPO, 최은정 UI/UX, 이승엽 BM엔진, 정민재 DB, 김도윤 포털수집)
- **참조 및 검수**: `QQAQC` (검수 전담: 한지훈)
- **우선순위**: CRITICAL (사용자 5회 반복 전수 검수 및 무결함 지시)

---

## 1. 배경 및 개선 목표
사용자 지시(*"모든 전수 검사를 5번 반복해서 검수하고 찾아서 수정해. 모든 팀원들은 하나 하나 모두 검수하라."*)에 따라, 7인의 팀원 전원이 참여하는 **5단계 심층 교차 전수 검수(5-Round Cross Audit)**를 실행하고 발견된 모든 미세 결함을 외과수술식으로 즉각 수정·치유한다.

---

## 2. 5대 검수 라운드별 세부 작업 내역 (for QCWA)

### [Round 1] UI/UX 템플릿 마크업 및 누락 DOM ID 치유 (최은정 UI/UX)
1. **`src/web/templates/announcements.html` 시뮬레이터 결과 마크업 복원**:
   - `#simResult` 내부에 누락되었던 `<p id="simNote" class="text-xs text-slate-600 mt-2 leading-relaxed"></p>` 및 `<div id="simChecks" class="space-y-1.5 mt-2"></div>` 추가하여 JavaScript `TypeError` 원천 방지.
2. **`src/web/templates/audit_logs.html` 무결성 검증 결과 컨테이너 복원**:
   - `<!-- 감사로그 테이블 -->` 상단에 `<div id="verify-result" class="hidden"></div>` 마크업 배치하여 `verifyChain()` 클릭 시 검증 결과 배너가 즉시 노출되도록 복원.

### [Round 2] FastAPI 백엔드 라우트 및 OpenAPI 스키마 무결성 (박준호 CPO)
1. **FastAPI Operation ID 중복 경고 소거 (`src/web/app.py`)**:
   - `/api/export/hwpx`, `/api/export/docx`, `/api/admin/audit/verify`의 `methods=["GET", "POST"]` 라우트에 명시적 `operation_id` 부여 (예: `operation_id="export_hwpx"`, `operation_id="export_docx"`, `operation_id="admin_audit_verify"`).
2. **API 응답 일관성**:
   - 결제, 내보내기, 감사 검증 엔드포인트의 입력 파라미터 결측 시 명확한 400 또는 정형 실패 응답 보장.

### [Round 3] 데이터베이스 무결성 & 암호화 보안 검증 (정민재 DB/보안)
1. SQLite WAL 모드 및 스키마 무결성 재점검.
2. `src/security/encryption.py` AES-256-GCM 키 파생 및 테넌트 데이터 격리 무결성 확인.
3. 평문 시크릿 누출 및 XSS 취약점 전수 차단.

### [Round 4] BM 엔진 & 25대 신호등 비행점검 정밀도 검증 (이승엽 BM엔진)
1. 2026 연도 거버넌스 필터(2025 이하 과거 공고 100% 차단) 유지.
2. R&D 자격 하이브리드 판정 및 4-Tier 요금제 연간 20% 할인 계산 로직 정합성 유지.

### [Round 5] 포털 연동 & QA Swarm 7-Agent 전주기 감사 (김도윤 포털, 한지훈 QQAQC)
1. 12대 수집 포털 서킷 브레이커 장애 복원력 검증.
2. 외부 공고 라이브 직링크(Ground-Truth) 200 OK 유지.
3. 239개+ pytest 전수 통과 및 QA Swarm 140/140 만점(100.0/100.0, GATE APPROVED) 유지.

---

## 3. 검수 기준 (for QQAQC - 한지훈)
1. 템플릿 내 누락 DOM ID 0건 (`announcements.html`, `audit_logs.html` 완비).
2. FastAPI 기동 시 OpenAPI 중복 경고 0건.
3. `pytest tests/ --ignore=tests/audit -q`: 239개+ 전수 통과 (0 failed).
4. `python -m tests.audit.audit_runner`: 100.0/100.0 (GATE APPROVED).

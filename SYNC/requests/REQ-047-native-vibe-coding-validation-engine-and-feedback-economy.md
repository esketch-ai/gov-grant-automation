# REQ-047: 바이브코딩 프로토타입 검증 엔진 및 7:3 피드백 리워드 경제 네이티브 구현

- **요청 일시**: 2026-10-28
- **발신**: `GCWA` (총괄 아키텍트 / PM)
- **수신**: `QCWA` (개발 전담 워크스페이스: 박준호 CPO, 최은정 UI/UX, 이승엽 BM엔진, 정민재 DB, 김도윤 연동)
- **참조 및 검수**: `QQAQC` (검수 전담 워크스페이스: 한지훈)
- **우선순위**: CRITICAL (2026 모두의 창업 핵심 비즈니스 모델 내재화)

---

## 1. 배경 및 사용자 직접 지시사항

사용자 대표님 직접 지시:
> **"SSHAI-BOOM 연동이 아니다. 그곳에 정리된 기획 문서 중 필요한 기능을 이곳에 구현해서 서비스 해야 한다."**
> **"내년에 예비창업 과제 지원이 모두의 창업으로 변경이 된다... 이들은 AI 를 통해 바이브 코딩 개발을 진행하게 될 것이다. 그것을 서비스 하기 위해 프로토타입 신청이 가장 많을 것이다. 이들의 사업계획서와 바이브코딩 개발한 웹과 앱들에 대해 링크들을 받게 되면 그 웹과 앱에 대해 최소한 주변인들에게 평가나 설문조사를 받아서 통계와 평가 보고서를 가지고 있어야 한다. 이는 심사위원들이 최소한의 사업 성과로 보기 때문이다."**
> **"유료화로써 건당 요금체계가 정해지면 그 한도 금액에 맞게 선착순 피드백을 받게 하며, 피드백을 선착순 내 진행을 한 사용자들에게 한도 금액의 70% 수준을 개별 지급한다. 나머지 30% 는 우리 수수료이다."**

- **외부 연동 금지**: 별도 외부 서버와의 API 통신이 아니라, SSHAI-BOOM에 기설계된 핵심 기능(체류시간 검증 하트비트 엔진, 3단계 피드백, 7:3 리워드 정산, 심사위원 보고서)을 **당사 플랫폼(`SSHAI-CWA`) 내부에 100% 네이티브 모듈로 직접 구현**하여 서비스한다.

---

## 2. 세부 개발 요구사항 (QCWA 실무팀)

### 2.1 데이터베이스 스키마 확장 (`src/common/db.py` - 정민재 DB)
`ensure_schema()` 내에 3개 핵심 테이블을 `CREATE TABLE IF NOT EXISTS`로 idempotent하게 추가한다:

```sql
-- 1. 프로토타입 검증 캠페인 테이블
CREATE TABLE IF NOT EXISTS prototype_campaigns (
    id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    prototype_url TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    target_testers INTEGER DEFAULT 50,
    fee_per_test INTEGER DEFAULT 2000,
    tester_reward INTEGER DEFAULT 1400,      -- 70% (개별 테스터 지급)
    platform_fee INTEGER DEFAULT 600,        -- 30% (플랫폼 수수료)
    total_budget INTEGER DEFAULT 100000,     -- target_testers * fee_per_test
    completed_testers INTEGER DEFAULT 0,
    status TEXT DEFAULT 'ACTIVE',            -- ACTIVE, COMPLETED, PAUSED
    created_at TEXT NOT NULL
);

-- 2. 테스터 실사용 세션 및 체류시간 측정 테이블 (Page Visibility Engine)
CREATE TABLE IF NOT EXISTS prototype_sessions (
    id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL,
    tester_id TEXT NOT NULL,
    active_seconds INTEGER DEFAULT 0,        -- 실제 탭 활성 체류 시간 (초)
    visible_seconds INTEGER DEFAULT 0,       -- 화면 노출 시간 (초)
    status TEXT DEFAULT 'STARTED',           -- STARTED, ENGAGED (60s+), COMPLETED, INVALID
    started_at TEXT NOT NULL,
    completed_at TEXT
);

-- 3. 구조화 피드백 및 리워드 지급 장부
CREATE TABLE IF NOT EXISTS prototype_feedbacks (
    id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL,
    session_id TEXT NOT NULL UNIQUE,
    tester_id TEXT NOT NULL,
    tester_alias TEXT NOT NULL,              -- 예: "동료 창업자 #42", "IT 서비스 대표님"
    dwell_seconds INTEGER NOT NULL,          -- 실측 체류 시간
    ux_score INTEGER NOT NULL,               -- 1~5점 (UI/UX 사용성)
    functionality_score INTEGER NOT NULL,   -- 1~5점 (핵심 기능 완성도)
    willingness_to_pay INTEGER NOT NULL,     -- 1~5점 (유료 지불 용의성)
    nps_recommend_score INTEGER NOT NULL,    -- 1~10점 (동료 추천 의향)
    blocker_category TEXT NOT NULL,          -- '로그인/회원가입', '기능오류/버그', 'UI깨짐/가독성', '속도지연', '기타'
    qualitative_feedback TEXT NOT NULL,      -- 15자 이상 구체적 개선 의견 (심사위원 대응용)
    reward_amount INTEGER NOT NULL,          -- 건당 지급액 (1,400원)
    reward_status TEXT DEFAULT 'PAID',       -- PAID, PENDING
    created_at TEXT NOT NULL
);
```

### 2.2 비즈니스 로직 엔진 (`src/prototype/validation_engine.py` - 이승엽 BM / 박준호 CPO)
1. **캠페인 개설 및 7:3 분배 계산**:
   - `create_campaign(item_id, tenant_id, prototype_url, title, total_budget, fee_per_test)`
   - `target_testers = total_budget // fee_per_test`
   - `tester_reward = int(fee_per_test * 0.7)` (70% 지급)
   - `platform_fee = fee_per_test - tester_reward` (30% 수수료)
2. **Page Visibility 세션 하트비트 엔진**:
   - `start_session(campaign_id, tester_id)` ➔ 세션 발급
   - `record_heartbeat(session_id, active_delta, is_visible)` ➔ 활성 시간 누적 (탭 이탈 시 정지)
   - 60초 미만은 `ENGAGED` 미달로 피드백 제출 차단 (체리피커 방어)
3. **피드백 검증 및 리워드 정산**:
   - `submit_feedback(session_id, feedback_data)`
   - 조건 검증: `active_seconds >= 60` AND `len(qualitative_feedback.strip()) >= 15`
   - 통과 시 `prototype_feedbacks` 기록, `completed_testers += 1`
   - `completed_testers >= target_testers` 시 캠페인 상태 `COMPLETED`로 자동 마감
4. **심사위원 제출용 "고객 검증 및 설문 피드백 보고서" 합성기**:
   - `generate_validation_report(campaign_id)`:
     * 모수(N), 평균 체류시간 (분/초)
     * 5대 평가 지표 방사형 차트 데이터 (UX, 기능, 가격, 시장성, NPS)
     * NPS 계산: `((9~10점 추천자 수 - 1~6점 비추천자 수) / 총원) * 100` (-100 ~ +100)
     * 막힌 지점 Top 카테고리 분포 및 핵심 코멘트 요약
     * 데이터 무결성 보증용 SHA-256 감사 해시 날인

### 2.3 백엔드 REST API 및 뷰 라우트 (`src/web/app.py` - 박준호 CPO, 정민재 DB)
- `POST /api/prototype/campaigns`: 신규 검증 캠페인 개설
- `GET /api/prototype/campaigns`: 진행 중인 동료 창업자 캠페인 목록 조회 (대시보드 피드용)
- `GET /api/prototype/campaigns/{id}`: 캠페인 상세 조회
- `POST /api/prototype/sessions/start`: 실사용 체험 세션 시작
- `POST /api/prototype/sessions/heartbeat`: 3초 간격 체류시간 하트비트 수신
- `POST /api/prototype/feedback/submit`: 3단계 피드백 제출 및 70% 리워드 적립
- `GET /api/prototype/reports/{campaign_id}`: 검증 보고서 통계 JSON
- `GET /prototype/report/{campaign_id}`: 심사위원 제출용 공식 웹/인쇄 뷰 템플릿 렌더링

### 2.4 프론트엔드 UI/UX 구현 (최은정 UI/UX 리드)
1. **`src/web/templates/items.html` (아이템 등록 모달 및 카드)**:
   - 등록 폼 내 **[AI 바이브코딩 프로토타입 URL]** 입력 필드 추가 (`https://...`).
   - **[고객 피드백 검증 캠페인 개설]** 토글 스위치 및 예산 설정 (예: 5만원 / 10만원 / 20만원).
   - 7:3 정산 안내 표시: *"선착순 50명 모집 시 테스터 수당 70,000원(건당 1,400원) + 플랫폼 수수료 30,000원(건당 600원)"*.
   - 아이템 카드에 **[⚡ Vibe Coding 검증 중: 34/50명]** 배지 및 **[📊 고객 검증 보고서]** 바로가기 버튼 추가.
2. **`src/web/templates/biz_dashboard.html` (동료 체험 라운지 & 테스터 모달)**:
   - 상단 섹션: **`동료 창업자 바이브코딩 프로토타입 체험 & 7:3 리워드 라운지`**
   - 참여 가능한 캠페인 카드 그리드 (앱 이름, 분야, 1회 체험 수당 `1,400원 적립`, 잔여 `선착순 16명`).
   - 내 테스터 적립금 요약 칩 (`나의 테스터 리워드: 4,200원 (3건 완료)`).
   - **인터랙티브 샌드박스 뷰어 & 리뷰 모달**:
     * 상단 헤더: 앱 타이머 (`⏱ 실사용 체험 중... 00:45`), 탭 이탈 시 정지 안내.
     * 본체: 프로토타입 URL 반응형 iframe 샌드박스.
     * 60초 도달 시 하단 [📝 3분 실사용 피드백 작성] 버튼 잠금 해제.
     * 3-Step 피드백 시트 (막힌 지점 선택 ➔ 4대 정량 척도 ➔ 15자 이상 구체 의견).
     * 제출 완료 시 축하 토스트 및 1,400원 수당 즉시 적립.
3. **`src/web/templates/prototype_report.html` (신규 - 심사위원 제출용 공식 보고서)**:
   - 대한민국 정부지원사업 심사위원 제출용 규격 레이아웃.
   - 정부 공문 서식 및 깔끔한 A4 규격 프린트 스타일 (`@media print`).
   - 4대 KPI 요약 (테스터 모수, 평균 체류시간, NPS 점수, 전반적 만족도).
   - 5대 지표 레이더 차트 및 막힌 지점 Top 3 개선 대책 표.
   - 하단 공인 검증 인증 마크 및 SHA-256 무결성 해시 날인.

---

## 3. 검수 기준 (QQAQC - 한지훈)
1. `tests/test_prototype_validation_engine.py` 작성 및 통과:
   - 7:3 분배금 산출 정합성 (1원 단위 오차 없음).
   - 60초 미만 제출 차단 및 60초 이상 + 15자 이상 피드백 정상 승인.
   - 선착순 한도 도달 시 캠페인 자동 마감.
   - 보고서 산출물 및 SHA-256 해시 무결성 검증.
2. 기존 251개 pytest 회귀 100% 통과 유지.
3. QA Swarm 140/140 만점 (Deploy-Ready) 유지.
4. K-Horizon 2027 디자인 토큰 준수 (인라인 `style` 0건).
5. `REGISTRY.md` 및 `INBOX.md` 완료 갱신.

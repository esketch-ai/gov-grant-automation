# REQ-019 — 공고 마감일 D-Day 카운트다운 및 표준 iCalendar(.ics) 내보내기 연동

## 메타
- **요청자**: Gemini (총괄 PM · `chief-architect`)
- **담당자**: 이승엽(심사역/D-Day) / 정민재(문서/iCalendar) / 최은정(보안/포맷) / 박준호(웹 통합) / 한지훈(QA)
- **우선도**: HIGH
- **상태**: ✅ **DONE**
- **완료 목표 버전**: **v1.4.0**

---

## 1. 배경 및 목적
정부 R&D 및 지원사업 공고는 신청 마감 시점이 핵심 의사결정 기준입니다.
사용자가 마감 임박 공고(D-Day, D-3, D-7 등)를 직관적으로 파악하고, 단일 클릭으로 Google Calendar, Apple Calendar, Microsoft Outlook 등 주요 캘린더 서비스에 일정을 등록하거나 2026년 공고 전체 일정을 피드로 구독할 수 있도록 RFC 5545 표준 iCalendar (.ics) 내보내기 및 D-Day 긴급도 판정 체계를 구축합니다.

---

## 2. 세부 개발 명세

### 2.1 마감일(Deadline) 표준 파서 및 D-Day 계산 (`src/common/deadline.py`)
- 한국 정부 공고의 다양한 날짜 포맷 견고하게 파싱:
  - `YYYY-MM-DD`, `YYYY.MM.DD`, `YYYY/MM/DD`
  - `YYYY-MM-DD HH:MM:SS`, `YYYY.MM.DD HH:MM`
  - 한글 일시 포맷: `YYYY년 MM월 DD일 HH시 MM분`
  - 기간형 포맷: `YYYY-MM-DD ~ YYYY-MM-DD HH:MM` (종료 마감일 우선 추출)
  - 시간 미기재 시 기본 18:00:00 KST 적용
  - 상시 접수, 예산 소진 시 등 비정형 문구 대응 (Safe Degrade)
- 긴급도 상태 분류:
  - `TODAY`: D-Day (오늘 마감, 펄스 애니메이션 배지)
  - `CRITICAL`: D-1 ~ D-3 (긴급 마감 임박)
  - `WARNING`: D-4 ~ D-7 (1주일 이내)
  - `APPROACHING`: D-8 ~ D-30
  - `NORMAL`: D-31 이상
  - `EXPIRED`: 마감 기한 경과 (`마감 (D+N)`)
  - `OPEN_ENDED`: 상시 / 미정

### 2.2 순수 파이썬 RFC 5545 표준 iCalendar 생성기 (`src/common/ical_exporter.py`)
- 서드파티 라이브러리 의존성 없이 순수 파이썬 표준 라이브러리로 구현
- `export_single_notice_ics(notice)`: 개별 공고 VEVENT 및 VALARM(1일 전, 3일 전 사전 알람) 포함 .ics 생성
- `export_bundle_calendar_ics(notices, calendar_name)`: 2026년 유효 공고 번들 VCALENDAR 생성
- RFC 5545 표준 문자열 이스케이프(`\`, `;`, `,`, 개행) 및 Asia/Seoul 타임존 메타데이터 준수

### 2.3 웹 관리자 엔드포인트 및 UI 연동 (`src/web/app.py`, `templates/`)
- `GET /api/calendar/2026.ics`: 2026년도 전체 공고 iCalendar 번들 다운로드
- `GET /api/announcements/{canonical_id}/calendar.ics`: 개별 공고 iCalendar 다운로드
- `GET /api/announcements/dday-summary`: 마감 긴급도 통계 API
- `announcements.html`: 공고 테이블 내 D-Day 배지, 행별 캘린더 다운로드 버튼, 상단 2026 캘린더 전체 다운로드 버튼, 상세 모달 내 캘린더 연동
- `dashboard.html`: 상단 `v1.4.0` 갱신, 마감 임박(D-7 이내) KPI 카드, 긴급 마감 임박 공고(D-7) 경보 박스 시각화

### 2.4 QA Swarm 검수 에이전트 확장
- `Agent-WebQA`: `/api/calendar/2026.ics`, `/api/announcements/dday-summary` 검수 항목 통합
- `tests/test_deadline_calendar.py`: 5건 단위/E2E 테스트 완결

---

## 3. 검증 결과
- `tests/test_deadline_calendar.py`: 5 passed
- 전체 단위/통합 테스트: **104 passed / 0 failed (0.70s)**
- 6대 전문 검수 에이전트(QA Swarm): **100.0 / 100.0 만점 (APPROVED, Deploy-Ready)**

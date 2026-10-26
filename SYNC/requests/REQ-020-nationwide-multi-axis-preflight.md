# REQ-020: 다차원 매칭 및 25대 조건 사전 비행점검 웹 관리자 전면 연동

> **요청자**: 총괄 PM (Gemini/Antigravity)  
> **담당**: 박준호(풀스택/UI 총괄), 이승엽(매칭 엔진), 최은정(데이터 바인딩), 한지훈(QA)  
> **상태**: 🚀 **IN PROGRESS (즉시 착수)**  
> **우선도**: HIGH  
> **전제 조건**: REQ-010, REQ-015, REQ-019  
> **연관 모듈**: 
> - `src/matcher/multi_axis_matcher.py` (다차원 매칭)
> - `src/matcher/applicant_profiler.py` (사업주 상태 자동 계산)
> - `src/matcher/notice_demographics_extractor.py` (공고 자격 추출)
> - `src/matcher/advanced_eligibility_validator.py` (25대 조건 비행점검)
> - `src/web/app.py`, `src/web/templates/announcements.html`, `dashboard.html`

---

## 1. 개발 배경 및 목적

1. **기술명 공고 탈피**: 심리상담, 교육, 서비스 플랫폼 등 비(非)R&D 사업주가 기술 키워드 매칭 실패로 누락되던 문제를 해결하기 위해, 이미 백엔드 코어에 구현된 **다차원 매칭 엔진(MultiAxisMatcher)**을 웹 UI에 시각적으로 연동합니다.
2. **원클릭 기업 프로필 설정**: 사업주가 사업자등록번호, 개업일, 대표자 생년월일, 주소만 넣으면 1초 만에 `[업력 2.5년 초기창업]`, `[만 32세 청년]`, `[여성기업]`, `[부산소재]` 태그가 생성되도록 합니다.
3. **25대 조건 사전 비행점검(Pre-Flight) 시각화**: 공고 상세 모달에서 부채비율 500%(3년 미만 특례), 연구소 필수, 3책 5공, 패키지 중복수혜, 자부담 현금 준비도를 **신호등(Green/Yellow/Red)** 자격 진단표로 즉시 확인할 수 있도록 구현합니다.

---

## 2. 세부 개발 요구사항 (Checklist)

### Task 1. 웹 관리자 기업 프로필(Company Profile) 저장 및 API 연동
- [ ] `src/common/db.py`: `company_profile` 테이블 생성/조회/업데이트 메서드 연동
  - 컬럼: `company_name`, `biz_reg_no`, `opened_date`, `founder_birth`, `founder_gender`, `address`, `debt_ratio_pct`, `has_rnd_lab`, `current_pi_projects`, `prior_grant_history` (JSON), `certifications` (JSON)
- [ ] `src/web/app.py`:
  - `GET /api/profile`: 현재 설정된 사업주 프로필 및 자동 계산된 자격(ApplicantProfiler) 반환
  - `POST /api/profile`: 프로필 저장/수정 엔드포인트 구현

### Task 2. 공고 목록 화면 다차원 탭 및 프로필 배너 구현
- [ ] `src/web/templates/announcements.html`:
  - 최상단: 현재 적용된 기업 프로필 요약 배너 (예: `🏢 마인드케어 플랫폼 | 🟢 초기창업 2.5년 | 👶 만 32세 청년 | 👩 여성기업 | 📍 부산광역시`) + [프로필 수정] 버튼
  - 탭 네비게이션 추가:
    - `[전체 맞춤 공고]`
    - `[🚀 창업패키지·청년]` (NoticeTrack.GENERAL_STARTUP)
    - `[🌊 지역·로컬특화]` (NoticeTrack.REGIONAL_LOCAL)
    - `[🏥 사회서비스·복지]` (NoticeTrack.SOCIAL_POLICY)
    - `[💻 기술R&D·바우처]` (NoticeTrack.DEEP_TECH_RND / VOUCHER_BIZ)
  - 탭 클릭 시 클라이언트 필터링 또는 API 파라미터(`track=...`)로 즉각 반응.

### Task 3. 공고 상세 모달 내 "사전 비행점검(Pre-Flight Check)" 뷰어 탑재
- [ ] `src/web/templates/announcements.html`:
  - 공고 상세 모달 내부에 **"🚥 사전 비행점검 (Pre-Flight Check)"** 섹션 신설
  - `POST /api/matcher/preflight` 호출 연동 (공고 ID + 기업 프로필)
  - 결과 렌더링:
    - **신호등 배지**: 🟢 GREEN (신청 적합) / 🟡 YELLOW (주의 요망) / 🔴 RED (신청 불가)
    - **적합도 점수**: `96점 / 100점`
    - **통과 요인**: 예: "창업 3년 미만 부채비율 특례 적용", "부산 지역 가점", "여성기업 가점"
    - **지뢰/결격 경고**: 예: "기업부설연구소 미보유 시 주관기관 신청 불가", "동일 패키지 중복수혜 제한"

### Task 4. 대시보드 KPI 및 긴급 알림 배너 연동
- [ ] `src/web/templates/dashboard.html`:
  - 프로필 기준 **"내 자격 맞춤 추천 공고 N건"** KPI 카드 추가
  - 마감 임박(D-7) 과제 중 내 자격 합격(GREEN) 과제 우선 노출

---

## 3. 완료 기준 (Definition of Done)

1. **단위 테스트 통과**:
   - `tests/test_web_profile_preflight.py` 신규 작성하여 프로필 저장, 탭 조회, 사전 비행점검 API 200 OK 및 판정 정합성 100% 검증.
2. **기존 테스트 호환성**:
   - `pytest` 기존 128개 테스트 전원 통과 유지 (0 failed).
3. **브라우저 클릭 정합성**:
   - 화면에 추가된 모든 버튼([프로필 수정], [탭 버튼], [비행점검 실행]) 클릭 시 자바스크립트 오류 0건 및 정상 렌더링.
4. **QA Swarm 감사**:
   - `audit_runner` 140점 만점 유지.

---

## 4. 실무진 코멘트 (Task Packet Receipt)
- **박준호 (풀스택/UI 총괄)**: "모달에 프로필 입력 폼과 신호등 뷰어를 Tailwind UI로 깔끔하게 구성하겠습니다. 기존 발표된 D-Day 및 iCal 다운로드 버튼과 충돌 없도록 레이아웃 배치하겠습니다."
- **이승엽 (매칭 엔진)**: "이미 검증된 `MultiAxisMatcher`와 `AdvancedEligibilityValidator`를 FastAPI 라우터에 바로 연결하면 0.05초 만에 신호등 결과가 반환됩니다."
- **한지훈 (QA)**: "프로필별(스타트업, 전통제조, 소상공인) 비행점검 E2E 테스트를 즉시 준비하겠습니다."

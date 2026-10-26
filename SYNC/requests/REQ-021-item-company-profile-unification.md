# REQ-021: 사업 아이템 ↔ 기업/대표자 프로필 통합 및 자동 상속

> **요청자**: Gemini (총괄 PM · `chief-architect`)  
> **수행자**: 박준호(총괄) / 이승엽(매칭) / 최은정(보안/UI) / 한지훈(QA)  
> **우선도**: HIGH (사용자 핵심 피드백 즉각 반영)  
> **전제조건**: REQ-020 (완료)  
> **목표 버전**: v1.5.1  

---

## 1. 배경 및 문제 정의

사업주 및 사용자의 핵심 피드백:
> "사업 아이템(`/items`) 관리 화면에서 여자 대표인지, 벤처기업인지, 청년인지 입력하는 곳이 전혀 없는데 어디서 파악해서 매칭하고 있는가?"

### 현황 분석
1. **데이터 단절**:
   - `items/*/profile.yaml`: 오직 기술적 속성(`target_trl`, `core_keywords`, `recipients`)만 존재.
   - `storage/grant_master.db`의 `company_profile`: 개업일, 대표자 생년월일, 성별, 인증(여성기업, 벤처기업 등), 재무 스펙 존재.
   - `/items` 관리 화면에는 기업/대표자 신분 입력 필드가 전무하여 사용자가 볼 때 "어디서 청년/여성/벤처 여부를 알고 매칭하는지" 파악 불가.
2. **목표**:
   - `items/*/profile.yaml`에 `company_specs` 스키마를 신설하여 아이템별 기업/대표자 신분을 명시 가능하도록 확장.
   - **자동 상속(Inheritance)**: 아이템에서 미입력 시 글로벌 `company_profile`의 값을 100% 자동 상속.
   - `/items` 웹 UI의 카드에 자격 태그(`[여성대표]`, `[청년]`, `[업력]`, `[인증]`)를 시각화하고, 등록/수정 모달에 기업 신분 입력 폼을 완전 통합.
   - `/api/matcher/simulate` 시뮬레이터에서 아이템의 `company_specs`와 `PreflightService`를 결합하여 신호등 종합 판정 제공.

---

## 2. 세부 개발 스펙

### A. YAML 스키마 확장 (`items/*/profile.yaml`)
`items/<item_id>/profile.yaml`에 `company_specs` 필드 추가:
```yaml
company_specs:
  company_name: "(주)마음숲연구소"
  biz_reg_no: "607-81-12345"
  opened_date: "2024-03-01"
  founder_birth: "1994-05-15"
  founder_gender: "F"
  address: "부산광역시 해운대구 센텀중앙로 48"
  debt_ratio_pct: 180.5
  has_rnd_lab: false
  is_capital_impaired: false
  has_tax_arrears: false
  current_pi_projects: 0
  registered_patents_count: 2
  prior_grant_history:
    - "예비창업패키지"
  certifications:
    - "여성기업"
    - "벤처기업"
```
*규칙: 특정 필드가 누락되었거나 비어있을 경우, `GrantDatabase.get_company_profile()`의 값을 기본값으로 자동 상속받음.*

### B. 백엔드 및 뷰 헬퍼 (`src/web/app.py`)
1. `_get_items_summary()`:
   - 각 아이템의 `company_specs`를 읽고, 빈 필드는 글로벌 DB 프로필로 자동 보강.
   - `_preflight_service.compute_qualifications()`를 실행하여 `qualification_tags` 리스트를 생성해 컨텍스트에 포함.
2. `POST /api/items` & `PUT /api/items/{item_id}`:
   - 신규 필드(`company_name`, `biz_reg_no`, `opened_date`, `founder_birth`, `founder_gender`, `address`, `debt_ratio_pct`, `has_rnd_lab`, `certifications` 등)를 받아 `profile.yaml`에 보존.
3. `POST /api/matcher/simulate`:
   - 아이템 ID로 로드한 `company_specs`(상속 포함)를 기반으로 `PreflightService.run()`을 함께 구동하여 `preflight` 신호등 결과도 응답에 반환.

### C. 웹 UI 템플릿 (`src/web/templates/items.html`)
1. **아이템 카드 리스트**:
   - 각 카드 상단에 자격 배지 노출:
     `<span class="bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full text-[10px]">여성기업</span>`
     `<span class="bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded-full text-[10px]">만 32세 청년</span>`
     `<span class="bg-slate-100 text-slate-700 border border-slate-200 px-2 py-0.5 rounded-full text-[10px]">업력 2.7년 초기창업</span>`
2. **신규 등록 및 수정 모달 (`#createModal`, `#editModal`)**:
   - `기업 및 대표자 신분 스펙 (회사 기본 프로필 자동 상속)` 접이식 또는 섹션:
     - 대표자 성별 (여성 / 남성)
     - 대표자 생년월일 (YYYY-MM-DD)
     - 개업연월일 (YYYY-MM-DD)
     - 본점 주소 (17개 시도)
     - 보유 인증 (쉼표 구분: 여성기업, 벤처기업, 소셜벤처 등)
     - 기업부설연구소 유무 (체크박스)
     - 부채비율 (%)
   - 모달 열릴 때 `/api/profile`에서 기본 프로필을 가져와 자동 Pre-fill.

---

## 3. 검증 기준 (품질 게이트)

1. `pytest tests/test_web_items_profile_integration.py` 100% 통과 (최소 4건 이상).
2. 전체 pytest 스위트 (135+ pass / 0 fail) 무결성 유지.
3. 7-Agent QA Swarm 종합 감사 140.0 / 140.0 만점 유지.
4. 브라우저 클릭 및 2026 연도 진본성 100% 통과.

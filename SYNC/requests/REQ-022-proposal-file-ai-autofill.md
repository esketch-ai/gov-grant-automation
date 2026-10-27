# REQ-022: 사업계획서(HWP/PDF/DOCX) 파일 업로드 기반 AI 아이템 자동 분석 및 Auto-fill

| 메타데이터 | 내용 |
|---|---|
| **ID** | `REQ-022` |
| **제목** | 사업계획서 파일 업로드 기반 AI 아이템 자동 분석 및 모달 폼 Auto-fill |
| **담당 워크스페이스** | `QCWA` (`term_4f82f7f5-f531-4b73-8bd6-6c55e04948aa`) |
| **검증 워크스페이스** | `QQAQC` (`term_5eeca898-bbb5-429a-98e8-c10e5133661e`) |
| **우선순위** | `HIGH` (사용자 핵심 편의 기능) |
| **연관 기능** | `REQ-021` (아이템 company_specs 스키마 및 모달 폼) |
| **상태** | `READY_FOR_DEV` |

---

## 1. 개요 및 목적
사업주가 `/items` 화면에서 신규 사업 아이템을 등록할 때 수많은 기술/기업/재무 필드를 일일이 수동 타이핑해야 하는 불편함을 해소합니다. 사업주가 기존에 작성해둔 사업계획서(HWPX, HWP, PDF, DOCX, TXT) 파일을 드래그앤드롭으로 올리면, 텍스트 추출 및 AI 구조화 파이프라인을 거쳐 **아이템 정보 + 기업 스펙(`company_specs`) 폼이 자동으로 완성(Auto-fill)**되고, 저장 시 원문이 `proposal.md`로 자동 보존되는 기능을 구현합니다.

---

## 2. 세부 구현 요구사항

### A. 다중 문서 텍스트 파서 (`src/parser/proposal_parser.py`)
1. **클래스**: `ProposalParser`
2. **핵심 메서드**: `extract_text(file_bytes: bytes, filename: str) -> str`
3. **포맷별 추출 규격 (순수 파이썬 구현)**:
   - **`.hwpx`**: `zipfile.ZipFile` 오픈 ➔ `Contents/section0.xml`, `section1.xml` ... 내 모든 XML 텍스트(`<hp:t>` 노드) 순차 추출.
   - **`.hwp`**: `olefile.OleFileIO` 오픈 ➔ `BodyText/Section*` 스트림 순회 ➔ 각 스트림의 zlib 압축 해제(`zlib.decompress(data, -15)`) ➔ UTF-16LE 텍스트 디코딩.
   - **`.pdf`**: `pypdf.PdfReader(io.BytesIO(file_bytes))` ➔ 각 페이지의 `extract_text()` 취합.
   - **`.docx`**: `zipfile.ZipFile` 오픈 ➔ `word/document.xml` 내 `<w:t>` 태그 텍스트 추출.
   - **`.txt`, `.md`**: `utf-8` 디코딩, 실패 시 `cp949` 디코딩.
4. **예외 처리**: 파일 손상, 비밀번호 암호화 등으로 파싱 실패 시 크래시 없이 `ValueError("지원되지 않거나 손상된 문서 형식입니다.")` 반환.

### B. AI 정형 JSON 스키마 추출기 (`src/parser/proposal_extractor.py`)
1. **클래스**: `ProposalExtractor`
2. **핵심 메서드**: `async extract(text: str) -> Dict[str, Any]` (동기 메서드 `extract_sync` 병행 제공)
3. **추출 JSON 규격**:
   ```python
   {
       "item": {
           "id": str,          # 영문 kebab-case 슬러그 자동 생성 (예: "smart-ai-dox")
           "name": str,        # 사업 아이템 / 과제 명칭
           "summary": str,     # 핵심 요약 (1~2문장)
           "trl": int,         # TRL 단계 1~9 (추정치)
           "keywords": list,   # 핵심 키워드 5~8개
           "target_stage": str # "초기창업", "예비창업", "도약기업" 등
       },
       "company_specs": {
           "company_name": str,
           "biz_reg_no": str,
           "opened_date": str,        # YYYY-MM-DD
           "founder_birth": str,      # YYYY-MM-DD
           "founder_gender": str,     # "F" 또는 "M"
           "address": str,
           "debt_ratio_pct": float,
           "has_rnd_lab": bool,
           "is_capital_impaired": bool,
           "has_tax_arrears": bool,
           "current_pi_projects": int,
           "registered_patents_count": int,
           "prior_grant_history": list,
           "certifications": list
       },
       "extracted_proposal_md": str   # 정리된 사업계획서 마크다운
   }
   ```
4. **이중 추출 안전망**:
   - **1차 (LLM)**: 로컬 Ollama (`http://localhost:11434/api/generate`, `qwen3.8:27b` 등) 또는 Gemini API 호출.
   - **2차 (Rule-based Fallback)**: LLM 연결 실패 또는 응답 지연(Timeout 10초) 시, 내장된 한국어 정규식 추출기(Regex Pattern Engine: `회사명:`, `대표자:`, `사업자번호:`, `특허:`, `TRL`, `설립일:`, `주소:` 등)로 안전 폴백하여 항상 유효한 정형 데이터를 반환.

### C. 웹 API 라우트 (`src/web/app.py`)
1. **`POST /api/items/analyze-proposal`**
   - 파일 수신: `UploadFile = File(...)`
   - 파일 파싱 및 스키마 추출 수행
   - 반환값:
     ```json
     {
         "status": "success",
         "filename": "사업계획서.hwpx",
         "data": { ... }
     }
     ```
2. **`POST /api/items/create` 엔드포인트 연동**:
   - `extracted_proposal_md` 또는 원본 텍스트가 있을 경우 해당 아이템 디렉토리의 `items/<item_id>/proposal.md` 파일로 자동 기록.

### D. 웹 UI 컴포넌트 (`src/web/templates/items.html`)
1. **모달 상단 드롭존 (Dropzone)**:
   - `[+ 새 사업아이템 등록]` 모달 열람 시 상단에 점선 형태의 드롭존 노출.
   - 파일 끌어다 놓기(Drag & Drop) 또는 파일 선택 클릭 지원.
2. **클라이언트 자바스크립트 Auto-fill**:
   - 파일 선택 즉시 `fetch('/api/items/analyze-proposal', ...)` 호출.
   - 로딩 스피너 및 프로그레스 표시.
   - 응답 완료 시 모달의 모든 폼 필드(`item_id`, `item_name`, `summary`, `trl`, `keywords`, 그리고 REQ-021의 `company_name`, `biz_reg_no`, `gender`, `birth`, `debt_ratio`, `has_rnd_lab` 등)에 값 자동 주입.
   - 자동 완성된 필드에 부드러운 하이라이트 효과 및 `[🤖 AI 추출]` 배지 일시 표시.

---

## 3. 검증 및 테스트 요건
1. **단위 테스트**:
   - `tests/test_proposal_parser.py`: HWPX, HWP, PDF, DOCX, TXT 샘플 바이트에 대한 텍스트 추출 무결성 검증.
   - `tests/test_proposal_extractor.py`: Rule-based Fallback 및 스키마 유효성 검증.
   - `tests/test_web_analyze_proposal.py`: `/api/items/analyze-proposal` API 엔드포인트 통합 테스트.
2. **전체 테스트 스위트**: 기존 140개 테스트를 포함하여 전수 통과(100% Green).

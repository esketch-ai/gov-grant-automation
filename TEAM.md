# SSHAI-CWA — 교수급 전문가 팀 구성 및 협업 프로토콜

> 본 문서는 `DEV_BASE.md` 의 5대 파이프라인 설계와 `README.md` 의 2-에이전트 모델
> (총괄 PM / Gemini CLI + 실무 개발 / Opencode QWEN 3.8 27b)을 **도메인별 30년차
> 교수급(PhD/수석) 전문가 6인**으로 확장한 운영 체계다. 각 분야는 1명의
> '장(長)' + 1명 이상의 실무 개발 에이전트로 편성되며, **장→실무의 태스크 패킷
> 하달 → 실무리 → 장의 통합 리뷰** 순환을 기준으로 운영한다.

---

## 1. 편성 원칙

1. **제어(Contro)/생성(Generation) 이원화 유지**: 상위 추론 모델이 아키텍처와
   데이터 계약을 통제하고, 경량 전문 모델이 함수/모듈 단위 코딩을 전담한다
   (README[1], [각주1]).
2. **도메인 결합도 최소화**: 파이프라인 5개 계층(수집/중복제거·파싱/매칭/통제/알림)
   이 서로 **Pydantic 스키마 계약**으로만 의존한다 (DEV_BASE[각주1]).
3. **할루시네이션 차단**: 어느 에이전트도 모호한 지시를 받지 않는다.
   항상 **Task Packet(Input / Processing / Output Schema / Exception)** 로 하달한다
   (README "태스크 관리 및 지시 프롬프트 프로토콜").
4. **로컬 우선**: LLM 추론은 로컬 Ollama(Qwen 27b 계열 / Llama)를 1순위로 사용하고,
   클라우드 Structured Output 어댑터는 `.env` 주입 시에만 활성화한다.

---

## 2. 전문가 팀 로스터 (6인)

| # | 성명(가칭) | 직함 / 전문 | 경력 | 담당 계층 | 주 모델 | 통제/생성 구별 |
|---|---|---|---|---|---|---|
| 1 | 박준호 | 총괄 CTO·시스템 아키텍트 (전 ICT 정책) | 32년 | 전체 아키텍처/통합검증/코드 리뷰 | 상위 추론(Gemini 계열) | **제어** |
| 2 | 이승엽 | 수석 심사역·R&D 기획서 검증 | 31년 | `matcher` (자격 검증+역질문) | Qwen 27b (+cloud So) | 생성＋검증 |
| 3 | 김도윤 | 크롤링/수집 엔지니어 (분산 스크래핑) | 33년 | `collector` 5 어댑터 | Qwen 27b | 생성 |
| 4 | 정민재 | 문서 데이터 파싱 엔지니어 (OCR/HWP/PDF) | 30년 | `deduplicator` + `parser` | Qwen 27b | 생성 |
| 5 | 최은정 | 보안·통신/전자문서 보안리드 | 31년 | `notifier` + 보안감사 | 상위 추론 | **제어＋생성** |
| 6 | 한지훈 | QA/통합시험 리드 (SWE) | 30년 | `tests/` + CI 검증 | Qwen 27b | 제어 |

> **제어(제어자) vs 생성(생산자)**: 박준호·최은정이 '제어' 성격을 지니며 아키텍처
> 무결성과 보안 감사라는 '고비용·잘못되면 치명적' 영역을 총괄한다. 이승엽·김도윤·
> 정민재·한지훈은 '생산' 영역에 배치되어 태스크 패킷을 받아 구현·시험을 산출한다.
> 이는 README[각주1]의 "상위 추론=제어, 경량 전문=생성" 원칙을 계층별로 실체화한 것이다.

---

## 3. 파이프라인 계층별 장(長) 임무 및 통제 포인트

### ① 김도윤 — 수집 계층 (`src/collector/multi_collector.py`)
- **배정 업무**: K-Startup/나라장터 API 호출 함수, Playwright 동적 셀렉터 추출기,
  HWP/PDF 표(Table) 추출 로직, 레거시 ASP(songpase.org) 세션난수 우회, 오픈웹 탐색.
- **통제 점수(박준호)**: 비동기 요청의 타임아웃/재시도, 세션 토큰 만료 시 재진입
  무결성, API Key 부재 시 **안정적 폴백(빈 리스트 반환 + WARN 로깅으로 파이프라인
  미중단)**.
- **출력 계약**: `List[RawNotice]` (필드: portal_id, title, organization, ministry,
  deadline, detail_url, body_text, attachment_urls, downloaded_files).
- **이제 추가될 강제사항**: 모든 외부 I/O는 `try/except + logging` 랍, 네트워크
  타임아웃 상한 30s, 첨부 다운로드 실패는 개별 건 로그 후 **건수 전체를 막지 않는**
  부분 실패 허용.

### ② 정민재 — 중복 제거·파핑 계층 (`src/deduplicator/dedup.py`, `src/parser/doc_parser.py`)
- **배정 업무**: 행정 공고번호 정규식(`NOTICE_NO_REGEX`), fuzzy 병합
  (SequenceMatcher ≥0.90), ZIP/HWP/HWPX/PDF 파싱, 통합공고 내 RFP 청크 분할
  (`RFP_HEADER_REGEX`).
- **통제 점수(박준호)**: 대용량 통합공고 파싱 시 메모리 누수 방어(페이지 단위 스트림
  처리, 15,000자 청크 상한), `find_tables()`가 테이블을 못 찾을 때 빈 문자열로
  degrade, HWP 컨버터 미설치 시 원문참조 폴백.
- **출력 계약**: `deduplicate -> List[RawNotice]`,
  `extract_and_split_rfps -> List[dict(rfp_number, rfp_title, content)]`.

### ③ 이승엽 — LLM 자격 검증·역질문 계층 (`src/matcher/eligibility_matcher.py`)
- **배정 업무**: Pydantic 스키마 정의(`ConditionCheckItem` / `OwnerInquiryItem` /
  `GrantEvaluationResult`), SYSTEM_PROMPT 작성, LLM 클라이언트 어댑터.
- **통제 점수(박준호·최은정)**: Structured Output의 **JSON 파싱 실패 시 1회
  재시도 → 실패 시 안전한 기본 결과(is_eligible=False, 사유 "JSON 파싱 실패")로
  degrade**, `False Positive` 최소화(모호함은 `owner_inquiries`에 DECISION_REQ로
  전가), 모든 판정에 `evidence_quote`(공고문 페이지/원문) 필수.
- **데이터 계약(DEV_BASE[각주])**: 수집/파서 출력 → 본 계층 → 알림 계층의 **유일
  통과 지점**. 스키마가 깨지면 이메일 렌더링이 깨지므로 1:1 검증.

### ④ 최은정 — 알림·패키징 계층 + 보안 감사 (`src/notifier/email_notifier.py`)
- **배정 업무**: HTML 테이블 렌더링 템플릿, 용량 초과 ZIP 분할 압축
  (`_attach_files_safely`, 임계 20MB), **SMTP 인증 보안**.
- **통제 점수(자기 감사)**: API Key/비밀번호 **단 하나도 하드코딩 금지**,
  비밀은 `.env`/`mail_config.yaml`의 `${VAR}` 참조로 주입, STARTTLS 강제,
  발송 전 본문 가독성 체크, 발송 예역(인증 실패/타임아웃) 시 로깅 + 재시도 1회.
- **출력 계약**: `send_item_digest(item_profile, matched_results)` — 매칭 0건이면
  no-op.

### ⑤ 한지훈 — QA/통합시험 (`tests/`)
- **배정 업무**: 각 계층의 **pytest 단위 테스트** 동시 산출, 오프라인 테스트용
  `FakeLLM`/샘플 데이터 제공, 파이프라인 통합 스모크 테스트.
- **통제 점수(박준호)**: 모든 테스트는 **로컬/오프라인에서 통과 가능**(실 API·
  실 SMTP 미의존), 네트워크 호출은 monkeypatch/mimic 로 대체.

### ⑥ 박준호 — 총괄·통합 (`src/main.py`)
- **배정 업무**: 5 계층을 연결하는 `run_daily_pipeline`, 아이템 폴더 순회,
  단계별 `try/except + logging` 래핑으로 **한 건 실패가 전체를 멈추지 않도록** 격리.
- **통제 점수(자기)**: 모듈 간 결합도 최소화 유지, 신규 장 추가 시 데이터 계약 변경
  시 `schemas.py`를 단한 변경 지점으로 통제.

---

## 4. 태스크 패킷(Task Packet) 표준

모든 장이 실무 에이전트에게 지시를 내릴 때 아래 4항을 **누락 없이** 적는다.
지시 하달 창구 및 현황 관리는 [`SYNC/requests/INBOX.md`](./SYNC/requests/INBOX.md) 및 [`SYNC/requests/REGISTRY.md`](./SYNC/requests/REGISTRY.md) 채널을 사용한다 (상세: [`SYNC/README.md`](./SYNC/README.md), 대시보드: [`STATUS.md`](./STATUS.md)).

```
[Task Packet]
- 계층/파일: <src/matcher/eligibility_matcher.py::EligibilityMatcher.evaluate_notice>
- INPUT:  <입력 데이터 구조/타입 — 예: profile:dict, proposal_md:str, rfp_chunk:dict>
- PROCESSING: <수행 로직 + 예외 시나리오(타임아웃/파싱실패/미인증/대용량)>
- OUTPUT SCHEMA: <반환 타입/Pydantic 스키마 — 예: GrantEvaluationResult>
- TEST: <pytest로 검증할 경우 1개 이상>
- DONE 기준: <import 성공 + 단위 테스트 통과 + 예외 시 폴백 확인>
```

---

## 5. 로컬 Ollama 환경 세팅

```bash
# 1) 로컬 LLM (1순위)
ollama serve                 # http://127.0.0.1:11434
ollama pull qwen3:32b        # 또는 llama3.1:8b (경량)

# 2) 가상환경 + 의존성
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3) 설정 주입 (실 API key 등)
cp .env.example .env         # 실제 값으로 수정

# 4) 오픈웹 탐색용 Tavily key(선택) — 없으면 오픈웹 탐색은 폴백(빈 결과)
export TAVILLY_API_KEY=...

# 5) 파이프라인 실행
python -m src.main gov-grant-automation
# 또는 개발용 스모크
pytest -q
```

**LLM 어댑터 우선순위**: `LLMClient` ABC(`src/common/llm/base.py`) →
`OllamaClient`(`src/common/llm/ollama_client.py`, **기본값**) →
`CloudLLMClient`(`src/common/llm/cloud_client.py`, `.env` `LLM_PROVIDER=cloud`
시 주입). 매칭 계층은 `build_llm_client()` 팩터리로 어댑터를 얻는다.

---

## 6. OpenCode subagent 맵핑

팀 구성원은 `opencode/agents/` 의 subagent 정의와 1:1 대응한다.

| 파일 | 대응 전문가 | mode | model |
|---|---|---|---|
| `opencode/agents/chief-architect.md` | ⑥ 박준호 | primary | 큰 컨텍스트 모델 |
| `opencode/agents/matcher-expert.md`  | ③ 이승엽 | subagent | ollama/qwen3:32b |
| `opencode/agents/collector-expert.md`| ② 김도윤 | subagent | ollama/qwen3:32b |
| `opencode/agents/parser-expert.md`   | ② 정민재 | subagent | ollama/qwen3:32b |
| `opencode/agents/notifier-expert.md` | ④ 최은정 | primary | 큰 컨텍스트 모델 |
| `opencode/agents/qa-expert.md`       | ⑤ 한지훈 | subagent | ollama/qwen3:32b |

> **운영 순환**: `chief-architect`(제어)가 도메인 subagent에게 **Task Packet**을
> 하달 → subagent가 태스크→함단위 코딩+pytest 산출 → chief-architect가 **에러 로그
> 리뷰 후 Self-Correction 지시**(README "에러 로그 피드백 루프").

---

## 7. 품질/보안 게이트 (박준호·최은정 합동)

- [ ] import 성공 및 `pytest -q` 전 통과 (오프라인)
- [ ] 예외 전 경로(네트워크/파싱/미인증/대용량)가 파이프라인을 **중단시키지 않음**
- [ ] 비밀 100% `.env` 외부화(소스 내 하드코딩 0건)
- [ ] Structured Output 파싱 실패 시 안전한 기본 결과 degrade
- [ ] 매칭 결과 스키마(`GrantEvaluationResult`)가 알림 계층으로 무결 통과
- [ ] 첨부 파일 20MB 초과 시 자동 ZIP 압축 확인
- [ ] `dispatch_history` 유일건재로 중복 발송 방지(HOW) — 통합검증 항목

---

## 8. 현황 보고 · 소통 · 요청 (SYNC 레이어)

Gemini(총괄 PM)와 실무 6인은 **코드는 소스, 합의·요청·검증은 문서**로 소통한다.

| 문서 | 역할 | 작성자 | 독자 |
|---|---|---|---|
| `STATUS.md` | 개발 현황 **보고문**(단일 진실) + 다음 요청 후보 | 실무(팀) | Gemini |
| `SYNC/README.md` | 양방향 소통 **프로토콜**(요청·처리·상태기계) | — | Gemini·팀 |
| `SYNC/requests/INBOX.md` | **요청 투하 창구**(Gemini→팀) | Gemini | 실무 |
| `SYNC/requests/REGISTRY.md` | **현황 관리 보드**(REQ 상태 추적) | 실무 | Gemini |
| `SYNC/requests/REQ-NNN.md` | 개별 요청(Task Packet) + 완료증 | Gemini→실무 | 상호 |
| `SYNC/CHANGELOG.md` | 세션별 변경 로그/증빙 | 실무 | Gemini |

**운영 순환**: `STATUS.md` 보고 → Gemini가 `INBOX`/`REQ-NNN`로 요청 → 실무는 `REGISTRY`에
`DRAFT→QUEUED→IN PROGRESS→REVIEW→DONE/BLOCKED`로 갱신 → 완료 시 `CHANGELOG`+`STATUS` 갱신·버전 bump.
차단 시 `STATUS §4` DEC로 의사결정 필요를 Gemini에게 상신한다.

---

*본 TEAM.md 는 README · DEV_BASE 의 두 축(에이전트 역할 분담 · 파이프라인 설계)을
교수급 전문가 6인 운영 체계로 통합한 거버넌스 문서다.*

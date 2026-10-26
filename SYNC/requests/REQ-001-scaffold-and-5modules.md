---
REQ-ID: REQ-001
STATUS: DONE
PRIORITY: HIGH
ASSIGNEE: 박준호(총괄) + 5인(이승엽·김도윤·정민재·최은정·한지훈)
DEADLINE: —
DEPENDS: 없음
---

# REQ-001: 프로젝트 초기화 — 스캐폴딩·5모듈·LLM·테스트·팀 구성

## INPUT
- `README.md`(에이전트 역할 정의) + `DEV_BASE.md`(5대 파이프라인 설계 청사진)
- 2샘플 사업 아이템(디지털 MRV / AI 음성 분리)

## PROCESSING
1. `bootstrap_project.py`로 디렉터리·config(master_portals/mail_config)·items 2종·SQLite(4테이블) 생성.
2. 5대 계층 보일러플레이트 완결:
   - `collector`: K-Startup/G2B/Playwright(Ntis·Iris·Nipa·Keit·Smtech·Modoo)/레거시ASP/오픈웹 + 타임아웃·세션우회·부분실패 폴백
   - `deduplicator`: `NOTICE_NO_REGEX` + SequenceMatcher fuzzy 병합
   - `parser`: ZIP/HWP/PDF→Markdown + `RFP_HEADER_REGEX` 청크 분할(15k자/zip-bomb 방어)
   - `matcher`: `GrantEvaluationResult`(Pydantic) + Structured Output degrade
   - `notifier`: 사업주 확인 박스 + 20MB 자동ZIP + SMTP STARTTLS + XSS escape + 비밀 외부화
3. 로컬 Ollama 우선 LLM(`base`/`ollama`/`cloud`/`build_llm_client` 팩터리).
4. 교수급 6인 팀 + Task Packet + 품질게이트(`TEAM.md`+`opencode/agents/*`).
5. 테스트 19건·의존성·설정 세팅(requirements/pyproject/pytest.ini/.env.example/.gitignore).
- **예외 시나리오 처리(강제)**: API 키/네트워크/파싱미성공/미인증/대용량 → WARN 로그 후 safe degrade, 파이프라인 미중단.

## OUTPUT / SCHEMA
- `RawNotice` · `ConditionCheckItem` · `OwnerInquiryItem` · `GrantEvaluationResult`(Pydantic v2)
- 실행산출: `src/`, `config/`, `items/`, `storage/grant_master.db`, `TEAM.md`, `opencode/agents/*`, `tests/`, 설정파일들

## TEST (pytest 19건)
- `test_dedup`: 공고번호 정규식·동일번호 병합·fuzzy 분리/병합·공배열
- `test_parser`: 2청크 분할·단일청크 폴백·빈파라미터·`RFP_HEADER_REGEX` 변형 3종
- `test_matcher`: 정상 Structured Output / `LLMStructuredParseError` degrade / 일반예외 degrade / 스키마 roundtrip
- `test_notifier`: 사업주확인박스 렌더(HTML decode)·XSS escape·20MB 초과 자동ZIP·첨부없음/미인증 raise
- (공통 `_fakes`: `FakeStructuredLLM` / `BrokenLLM` / `RaisingLLM`)

## DONE-기준
- [x] import 성공 (모든 모듈)
- [x] pytest **19 pass / 0 fail**
- [x] `LLM_OFFLINE=1 python -m src.main .` → 2아이템·**0 error**·격리 실행
- [x] 비밀 0건 하드코딩(`.env`/`${VAR}`), HTML XSS escape 적용
- [x] 파싱/LLM/미인증/대용량 degrade 경로 테스트로 증빙

## 완료증
- 추가/변경 파일: `bootstrap_project.py`, `src/**`(7파일), `opencode/agents/*`(6), `TEAM.md`,
  `README.md`(프로젝트), `tests/*`(5), `requirements.txt`, `pyproject.toml`, `pytest.ini`,
  `.env.example`, `.gitignore`, `config/*.yaml`, `items/item_01|02/*`
- 통과 테스트: 19건 (test_dedup/test_parser/test_matcher/test_notifier)
- 스모크: `LLM_OFFLINE=1 src.main` → `errors=0`, 두 아이템 모두 collected/unique/matched=0(폴백 정상)
- degrade/보안 확인: OK

## 다음 (Gemini가 선택) → `STATUS.md §5` / `REGISTRY.md`
- REQ-002 실 API 연동 (DEC-01 필요)
- REQ-003 DB 쓰기 연결
- REQ-004 Structured Output 튜닝 (Ollama 기동 필요)

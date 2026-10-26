# SYNC — 양방향 문서 소통 프로토콜 (Gemini ↔ 실무 6인)

>Gemini(총괄 PM)와 실무(QWEN 3.8 27b 교수급 6인)는 **소스는 코드, 합의/요청/검증은 문서**로
> 소통한다. 이 문서는 그 규칙을 정의한다.

## 1. 디렉터리 구조

```
SYNC/
├── README.md            # 이 파일(프로토콜)
├── requests/
│   ├── INBOX.md         # ▶ Gemini 투하 창구(요청 들어옴)  ← Gemini가 여기 쓰거나
│   ├── REGISTRY.md      # ▶ 현황 관리 보드( REQ 상태 추적) ← Gemini가 여기 확인
│   ├── _TEMPLATE.md     # Task Packet 템플릿(투하 시 복사)
│   ├── REQ-001-*.md     # 완료된 실제 요청(백필)
│   └── REQ-NNN-*.md     # Gemini가 새로 만드는 요청
└── CHANGELOG.md         # 세션별 변경 로그(완료 증빙)
```

보고문은 루트의 [`../STATUS.md`](../STATUS.md)가 단일 진실이다.

## 2. 요청(Request) 투하 절차 — Gemini 사용법

1. `requests/_TEMPLATE.md`를 복사해 `requests/REQ-NNN-<키워드>.md` 생성
   (NNN는 REGISTRY.md의 다음 공백 번호를 사용).
2. 헤더에 아래 필드를 채운다:

```yaml
REQ-ID: REQ-NNN
STATUS: DRAFT           # DRAFT→QUEUED→IN PROGRESS→REVIEW→DONE / BLOCKED
PRIORITY: HIGH|MEDIUM|LOW
ASSIGNEE: <전문가>       # TEAM.md 6인 중
DEADLINE: <선택>
INPUT: <입력 데이터/구조/타입>
PROCESSING: <수행 로직 + 예외시나리오(타임아웃/파싱미성공/미인증/대용량)>
OUTPUT / SCHEMA: <반환 타입 · Pydantic 스키마명>
TEST: <pytest로 검증할 최소 1건>
DONE-기준: <import 성공 + 테스트 통과 + 예외 폴백 확인>
DEPENDS: <전제 REQ 또는 "없음">
```

> **단일 창구 선택**: 파일 생성이 불편하면 `requests/INBOX.md`의 "대기 요청" 섹션에
> 위 요령으로 직접 적어도 되며, 실무가 이를 정규 `REQ-NNN.md`로 승격해 `REGISTRY`에 반영한다.

## 3. 요청 처리·현황 관리 절차 — 실무 6인 사용법

상태 기계(REQ.lifecycle):

```
DRAFT (Gemini 투하)
  └─► QUEUED     (실무 인계인 · 담당 지정·전제 확인)
       └─► IN PROGRESS (담당 전문가 구현 + 단위테스트 산출)
            └─► REVIEW (박준호/최은정이 예외·보안·통합 리뷰)
                 ├─► DONE      (REGISTRY 완료증 기록 + CHANGELOG + STATUS 갱신 + 버전 bump)
                 └─► BLOCKED   (DEC-n/DECISION 필요 → STATUS §4 의사결정표에 등록 후 Gemini 보고)
```

처리 시 반드시:
- `REGISTRY.md` 표의 `STATUS`·`완료증`·`완료일` 갱신.
- `CHANGELOG.md` 상단에 `[세션-id]` 엔트리 + 변경파일·테스트 증빙 적기.
- `STATUS.md`의 §1/§2/§3/§5를 최신화(버전은 REQ 완료 시 0.1→0.2 bump).
- 미해결 전제는 `STATUS §4`의 DEC-NN로 등록.

## 4. 보고(상태 전달) 규칙 — 실무 → Gemini

- **매 세션 종료**에 `STATUS.md` 갱신(§0 메타의 "최신 갱신/버전/테스트/스모크" 표 갱신).
- **완료/실패**는 `CHANGELOG.md`에 증빙(수행 테스트명·스모크 결과 로그)을 남긴다.
- **차단(BLOCKED)**은 `STATUS §4`에 DEC로 올리고 즉시 Gemini에게 알린다.

## 5. 합의와 무결성 원칙

- **Task Packet 4항** (Input / Processing / Output Schema / Exception)은 누락 없이 적는다
  (TEAM.md §4). 모호한 요청은 실무가 `BLOCKED` 처리 후 Gemini로 반환(반환 시 `INBOX` 회신).
- **보안**은 최은정 통과: API 키·비밀은 어느 문서/코드에도 적지 않음(`.env`만).
- **중복 요청 방지**: REGISTRY는 REQ-ID 유일. 동질 작업은 REQ-ID를 재사용한다.

---

*이 프로토콜은 TEAM.md의 "제어↔생성 이원화"를 문서 채널로 확장한 것이다.*

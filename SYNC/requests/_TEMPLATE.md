---
# ▼▼▼ Gemini가 이 아래를 복사해 REQ-NNN-<키워드>.md 로 투하한다 ▼▼▼
REQ-ID: REQ-NNN
STATUS: DRAFT
PRIORITY: MEDIUM
ASSIGNEE: <전문가>        # 박준호 / 이승엽 / 김도윤 / 정민재 / 최은정 / 한지훈
DEADLINE: <선택>
DEPENDS: <전제 REQ id 또는 "없음">
---

# 제목

## INPUT
- <입력 데이터/구조/타입 예: `profile:dict`, `rfp_chunk:dict`, `notice:RawNotice`>

## PROCESSING
- <수행 로직 순서>
- **예외 시나리오**: <타임아웃 / 파싱 미성공 / 미인증 / 대용량 → 폴백 방향>

## OUTPUT / SCHEMA
- <반환 타입 · Pydantic 스키마명 예: `GrantEvaluationResult`>

## TEST
- <pytest로 검증할 최소 1건 예: `test_xxx()` — 정상/파싱실패/미인증>

## DONE-기준
- [ ] import 성공
- [ ] 상기 테스트 통과
- [ ] 예외 경로의 safe degrade 확인
- [ ] 보안(비밀 하드코딩 0) · 격리(한건 실패 미중단) 확인

---
# ▲▲▲ 위를 복사해 채운 뒤 `requests/` 에 저장 ▲▲▲
# 처리 규칙은 SYNC/README.md §3, 상태 기계는 §3 참고.

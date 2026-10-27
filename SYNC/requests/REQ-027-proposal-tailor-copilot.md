# REQ-027: DocuMorph AI - 사업계획서 맞춤 변환 스튜디오 및 반자동 코파일럿

| 메타데이터 | 내용 |
|---|---|
| **ID** | `REQ-027` |
| **제목** | K-Startup PSST 및 중기부 R&D 표준 양식 맞춤 변환 스튜디오 & 반자동 코파일럿 |
| **총괄 조정** | `GCWA` |
| **담당 워크스페이스** | `QCWA` (`term_4f82f7f5-f531-4b73-8bd6-6c55e04948aa`) |
| **검증 워크스페이스** | `QQAQC` (`term_5eeca898-bbb5-429a-98e8-c10e5133661e`) |
| **우선순위** | `HIGH` (핵심 유료화 밸류) |
| **상태** | `DONE` |

---

## 1. 개요 및 목적
사업자의 마스터 사업계획서(`proposal.md`)를 공고별 양식(K-Startup PSST 8문항, 중기부 R&D 8문항)에 맞춰 구조화하고, 갭 분석 및 반자동 코파일럿 문답을 통해 공고 평가 기준에 부합하는 완성형 본문 초안을 합성하여 마크다운 및 HWPX 양식으로 출력합니다.

## 2. 구현 결과물
1. `src/generator/template_schemas.py`: PSST 및 RND_SMTECH 표준 템플릿 메타데이터 및 공고별 자동 감지기
2. `src/generator/gap_analyzer.py`: 완전매핑(DIRECT_FIT), 각색필요(ADAPT_FIT), 팩트필요(DEFICIENT) 3단계 갭 진단 및 준비도 점수 산출
3. `src/generator/doc_morpher.py`: 사용자 단답형 팩트 답변 기반 고밀도 개조식/번호형 본문 초안 생성기 및 전체 문서 조립기
4. `src/web/templates/tailor.html`: 스플릿 뷰(좌: 문항트리/갭뱃지, 우: 원문발췌/코파일럿Q&A/편집기/전체취합) 웹 UI
5. `tests/test_proposal_tailor_generator.py`: 4개 단위 및 API 테스트 통과

# REQ-028: 상용 B2B 멀티테넌트 SaaS 및 Company Vault (기업 지식 데이터 룸 & 소셜 로그인)

| 메타데이터 | 내용 |
|---|---|
| **ID** | `REQ-028` |
| **제목** | 기업별 독립 지식 데이터 룸(Vault), 카카오/구글 소셜 로그인 및 테넌트 데이터 격리 |
| **총괄 조정** | `GCWA` |
| **담당 워크스페이스** | `QCWA` (`term_4f82f7f5-f531-4b73-8bd6-6c55e04948aa`) |
| **검증 워크스페이스** | `QQAQC` (`term_5eeca898-bbb5-429a-98e8-c10e5133661e`) |
| **우선순위** | `HIGH` (SaaS 멀티테넌트 코어) |
| **상태** | `DONE` |

---

## 1. 개요 및 목적
단일 사용자 환경에서 기업별 독립 멀티테넌트 구조로 전환합니다. 사업자가 소셜 로그인(카카오, 구글, 데모)을 통해 자사 전용 계정을 발급받고, 자사의 4대 지식 자산(마스터 계획서, IR 발표자료, 재무/예산 파일, 특허/인증)을 드래그앤드롭으로 등록하여 안전하게 보관하는 기업 데이터 룸(Vault)을 구축합니다.

## 2. 구현 결과물
1. `src/common/db.py`: `tenants`, `users`, `tenant_assets`, `grant_projects` 멀티테넌트 테이블 및 격리 CRUD 메서드
2. `src/tenant/tenant_service.py`: 쿠키 세션(`sshai_session`), 소셜/데모 로그인 및 Vault 자산 AI 인제스천 파이프라인
3. `src/web/templates/vault.html`: 기업 데이터 룸 4대 자산 관리(4-Quadrant), 완성도 게이지(Vault Readiness Score), 소셜 로그인 모달
4. `tests/test_tenant_vault.py`: 테넌트 데이터 격리 및 소셜 로그인/업로드 E2E 검증 통과 (4pass)

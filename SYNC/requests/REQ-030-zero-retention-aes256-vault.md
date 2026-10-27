# REQ-030: Zero-File-Retention 정책 및 멀티테넌트 AES-256-GCM 암호화 보관 / TLS 1.2+ 전송 보안

| 메타데이터 | 내용 |
|---|---|
| **ID** | `REQ-030` |
| **제목** | 원본 파일 무보관 원칙, 테넌트 고유 키 기반 AES-256-GCM 필드 암호화 및 TLS 1.2+ 전송 보안 강화 |
| **총괄 조정** | `GCWA` |
| **담당 워크스페이스** | `QCWA` (`term_4f82f7f5-f531-4b73-8bd6-6c55e04948aa`) |
| **검증 워크스페이스** | `QQAQC` (`term_5eeca898-bbb5-429a-98e8-c10e5133661e`) |
| **우선순위** | `CRITICAL` (B2B SaaS 기업 기밀 유출 원천 방어) |
| **상태** | `QUEUED` |

---

## 1. 개요 및 목적
사업자의 **사업계획서, 발표자료(IR덱), 재무제표, 핵심 특허** 등 기업 기밀 정보의 유출을 원천 방지하기 위해:
1. **무보관 원칙 (Zero-File-Retention Policy)**: 업로드된 원본 파일(HWP/PDF/DOCX/PPTX)은 디스크에 저장하지 않고 메모리(RAM) 상에서만 정형 정보를 추출한 뒤 즉시 파기합니다.
2. **저장 암호화 (At-Rest AES-256-GCM)**: DB에 적재되는 추출 텍스트 및 메타데이터는 테넌트별 고유 키(HKDF-SHA256 유도)로 AES-256-GCM 암호화하여 저장합니다. 해킹으로 DB가 통째로 유출되어도 복호화가 불가능하며, 파일도 없으므로 탈취할 수 없습니다.
3. **전송 암호화 (In-Transit TLS 1.2+)**: 통신 전 구간 TLS 1.2+ 및 강화된 웹 보안 헤더(HSTS, CSP, X-Frame-Options)를 적용합니다.

---

## 2. 세부 개발 요구사항 (for QCWA)

### A. 의존성 및 암호화 코어 엔진 구축 (`src/security/encryption.py`)
1. **의존성**: `requirements.txt`에 `cryptography>=42.0` 명시 (설치 완료됨).
2. **클래스**: `VaultCryptoManager`
   - `__init__(master_key: str | bytes = None)`:
     - 환경 변수 `SSHAI_MASTER_ENCRYPTION_KEY`가 있으면 사용, 없으면 SHA-256 해시 기반의 안전한 기본 마스터 키 생성/적용.
   - `generate_tenant_salt() -> str`:
     - 테넌트 생성 시 부여할 16바이트 암호학적 난수 Hex 스트링 반환 (`secrets.token_hex(16)`).
   - `derive_tenant_key(tenant_id: str, tenant_salt: str) -> bytes`:
     - HKDF-SHA256을 사용하여 `MasterKey + tenant_salt + tenant_id` 로부터 테넌트 전용 32바이트(256-bit) 키 도출.
   - `encrypt_text(plaintext: str, tenant_key: bytes) -> str`:
     - `AESGCM(tenant_key)` 사용. 12바이트 랜덤 nonce 생성.
     - `base64(nonce + ciphertext + tag)` 포맷의 단일 스트링 반환.
   - `decrypt_text(ciphertext_b64: str, tenant_key: bytes) -> str`:
     - base64 디코딩 후 nonce, ciphertext+tag 분리하여 복호화.
     - 다른 테넌트의 키이거나 변조된 경우 `cryptography.exceptions.InvalidTag` 발생.
   - `encrypt_json(data: dict | list, tenant_key: bytes) -> str` / `decrypt_json(ciphertext_b64: str, tenant_key: bytes) -> dict | list` 제공.

### B. 무보관 원칙(Zero-File-Retention) 및 테넌트 데이터 분리 적용 (`src/tenant/tenant_service.py` & `src/common/db.py`)
1. **DB 마이그레이션 (`src/common/db.py`)**:
   - `tenants` 테이블에 `tenant_salt TEXT DEFAULT ''` 컬럼 자동 보정 (`PRAGMA table_info` 확인 후 `ALTER TABLE`).
   - 테넌트 생성 시 `tenant_salt` 자동 생성 및 저장.
2. **원본 파일 무보관 (`src/tenant/tenant_service.py`)**:
   - `ingest_asset()` 함수:
     - 수신된 파일 바이트(`raw_bytes`)를 메모리 스트림으로만 파싱(`ProposalParser`).
     - 파일 시스템 경로(예: `/tmp`, `uploads/` 등)에 영구 또는 잔여 파일 생성 금지.
     - 파싱 직후 메모리 버퍼 해제.
3. **필드 레벨 암호화 보관**:
   - `tenant_assets` 테이블에 저장 시:
     - `content_text`: 평문 텍스트 대신 `encrypt_text(text, tenant_key)`로 암호화 저장.
     - `parsed_metadata`: 평문 JSON 대신 `encrypt_json(meta, tenant_key)`로 암호화 저장.
   - `list_assets()`, `get_asset()` 조회 시:
     - 테넌트 키로 자동 복호화하여 호출자에게 정상 반환.
     - 만약 기존 데이터가 평문일 경우(마이그레이션 호환) 정상 반환 및 자동 재암호화 호환성 유지.

### C. 전송 계층 보안 및 HTTP 보안 헤더 (`src/web/app.py`)
1. **FastAPI 미들웨어 (`SecurityHeadersMiddleware`)**:
   - 모든 HTTP/HTTPS 응답에 보안 헤더 주입:
     - `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
     - `X-Content-Type-Options: nosniff`
     - `X-Frame-Options: DENY`
     - `X-XSS-Protection: 1; mode=block`
     - `Referrer-Policy: strict-origin-when-cross-origin`
2. **쿠키 보안 플래그**:
   - `sshai_session` 쿠키 설정 시 `httponly=True`, `samesite="lax"` 보장.

---

## 3. 검증 및 테스트 요구사항 (for QQAQC)
1. **단위 및 보안 침해 테스트**: `tests/test_zero_retention_aes256.py`
   - **무보관 검증**: 자산 업로드 후 디스크 상에 원본 파일 및 임시 파일이 0개임을 검증.
   - **DB 침해 시나리오 검증**: SQLite DB 파일을 직접 조회했을 때 `content_text`와 `parsed_metadata`가 평문이 아닌 암호문(Base64 AES-GCM)으로 저장되어 있음을 검증.
   - **테넌트 격리 암호 검증**: 테넌트 A의 데이터를 테넌트 B의 키로 복호화 시도 시 `InvalidTag` 예외가 발생하여 열람이 원천 차단됨을 검증.
   - **보안 헤더 검증**: Web API 응답에 HSTS, X-Content-Type-Options, X-Frame-Options 헤더가 포함되어 있는지 검증.
2. **QA Swarm 무결성 감사**:
   - `python tests/audit/audit_runner.py` 실행 시 140.0/140.0 만점 유지 확인.

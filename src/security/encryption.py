"""
REQ-030 · AES-256-GCM + HKDF-SHA256 Zero-Retention Vault 암호화 매니저.

- 마스터 키(SSHAI_MASTER_ENCRYPTION_KEY env 또는 SHA-256 디폴트)로 HKDF-SHA256 파생
- AESENC:: 센티넬 접두어로 암호문 / 레거시 평문 자동 구분
- DB compromise 시에도 평문 유출 방지(평문은 메모리에만 존재, 파일 미기록)
- 테넌트 격리: 다른 salt/키로 복호화 시도 시 InvalidTag 발생
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
from typing import Any, Dict, Optional

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


# 암호문 식별 센티넬: 접두어 존재 여부가 평문(레거시) vs 암호문 분기 기준
AESENC_SENTINEL = "AESENC::"
_NONCE_BYTES = 12  # AES-GCM 표준 nonce 길이
# env 미지정 시 마스터 키 대체값(32B). 상용 배포 시 SSHAI_MASTER_ENCRYPTION_KEY 주입.
_DEFAULT_MASTER = hashlib.sha256(b"sshai-cwa-default-master-key-v1").digest()


class VaultCryptoManager:
    """테넌트 단위 AES-256-GCM 암호화/복호화. 파일 미기록(zero-retention)."""

    def __init__(self, master_key: Optional[bytes] = None) -> None:
        mk = master_key
        if mk is None:
            mk = os.environ.get("SSHAI_MASTER_ENCRYPTION_KEY")
        if not mk:
            self.master_key = _DEFAULT_MASTER
        elif isinstance(mk, str):
            self.master_key = hashlib.sha256(mk.encode("utf-8")).digest()  # 32B 정규화
        else:
            self.master_key = mk[:32].ljust(32, b"\0")

    def generate_tenant_salt(self) -> str:
        """테넌트 고유 16B salt(32 hex). login 시 1회 생성 후 tenants 테이블에 저장."""
        return secrets.token_hex(16)

    def derive_tenant_key(self, tenant_id: str, tenant_salt: str = "") -> bytes:
        """HKDF-SHA256: 마스터키 + tenant_id + salt → 32B 테넌트 키."""
        info = f"vault-tenant:{tenant_id or 'tenant_default'}".encode("utf-8")
        salt = tenant_salt.encode("utf-8") if tenant_salt else b""
        return HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=info,
        ).derive(self.master_key)

    def encrypt_text(self, plaintext: str, tenant_id: str = "tenant_default",
                     tenant_salt: str = "") -> str:
        key = self.derive_tenant_key(tenant_id, tenant_salt)
        nonce = secrets.token_bytes(_NONCE_BYTES)
        ct = AESGCM(key).encrypt(nonce, (plaintext or "").encode("utf-8"), None)
        return AESENC_SENTINEL + base64.b64encode(nonce + ct).decode("ascii")

    def decrypt_text(self, blob: str, tenant_id: str = "tenant_default",
                     tenant_salt: str = "") -> str:
        """센티넬이 없는 값은 레거시 평문으로 그대로 통과. 복호화 실패 시 InvalidTag."""
        if not isinstance(blob, str) or not blob.startswith(AESENC_SENTINEL):
            return blob if isinstance(blob, str) else ""
        raw = base64.b64decode(blob[len(AESENC_SENTINEL):])
        nonce, ct = raw[:_NONCE_BYTES], raw[_NONCE_BYTES:]
        key = self.derive_tenant_key(tenant_id, tenant_salt)
        return AESGCM(key).decrypt(nonce, ct, None).decode("utf-8")

    def encrypt_json(self, obj: Any, tenant_id: str = "tenant_default",
                     tenant_salt: str = "") -> str:
        return self.encrypt_text(json.dumps(obj or {}, ensure_ascii=False), tenant_id, tenant_salt)

    def decrypt_json(self, blob: str, tenant_id: str = "tenant_default",
                     tenant_salt: str = "") -> Any:
        return json.loads(self.decrypt_text(blob, tenant_id, tenant_salt))


_crypto_singleton: Optional[VaultCryptoManager] = None


def get_crypto() -> VaultCryptoManager:
    global _crypto_singleton
    if _crypto_singleton is None:
        _crypto_singleton = VaultCryptoManager()
    return _crypto_singleton


def decrypt_asset_record(record: Dict[str, Any], tenant_id: str = "tenant_default",
                         tenant_salt: str = "") -> Dict[str, Any]:
    """
    Vault 자산 레코드의 content_text/parsed_metadata를 평문 또는 자동 복호화.
    - AESENC:: 센티넬 → decrypt (실패/변조 시 안전하게 빈 값 → 유출 방지)
    - 센티넬 없는 JSON 문자열(레거시) → json.loads
    - 이미 dict → 그대로 통과 (matcher _parse_meta가 dict를 받아들임)
    """
    out = dict(record or {})
    for field, as_json in (("content_text", False), ("parsed_metadata", True)):
        val = out.get(field)
        if val is None:
            continue
        if isinstance(val, dict):
            continue
        if isinstance(val, str) and val.startswith(AESENC_SENTINEL):
            try:
                dec = get_crypto().decrypt_text(val, tenant_id, tenant_salt)
                out[field] = json.loads(dec) if as_json else dec
            except Exception:  # InvalidTag/변조 → 유출 방지 위해 안전하게 비우기
                out[field] = {} if as_json else ""
        elif as_json and isinstance(val, str):
            try:
                out[field] = json.loads(val) if val.strip() else {}
            except Exception:
                out[field] = {}
    return out

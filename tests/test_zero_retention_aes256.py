"""
tests/test_zero_retention_aes256.py
REQ-030 · AES-256-GCM + HKDF-SHA256 Zero-Retention Vault 암호화 검증.

- 평문/JSON round-trip
- 테넌트 격리(이름 다르면 salt/키 다름 → InvalidTag)
- DB compromise 시 raw content_text가 AESENC:: 암호문이며 평문 유출 없음
- zero-retention: 암호화 과정에서 .enc/.bin 등 파일 미기록
- 보안 헤더 5종 주입 (SecurityHeadersMiddleware)
- 레거시 평문 transparent passthrough (matcher/decrypt_asset_record)
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cryptography.exceptions import InvalidTag

from src.common.db import GrantDatabase
from src.security.encryption import (
    AESENC_SENTINEL,
    VaultCryptoManager,
    decrypt_asset_record,
    get_crypto,
)
from src.tenant.tenant_service import TenantService
from src.web.app import app


# ------------------------------------------------------------------ #
# 1. 암호/복호 round-trip
# ------------------------------------------------------------------ #
def test_encrypt_roundtrip_text():
    crypto = VaultCryptoManager()
    salt = crypto.generate_tenant_salt()
    plain = "A사 핵심 기술: 탄소배출권 자동 측정 플랫폼"
    blob = crypto.encrypt_text(plain, "tenant_A", salt)
    assert blob.startswith(AESENC_SENTINEL)
    assert plain not in blob  # 암호문에 평문 미포함
    assert crypto.decrypt_text(blob, "tenant_A", salt) == plain


def test_encrypt_roundtrip_json():
    crypto = VaultCryptoManager()
    salt = crypto.generate_tenant_salt()
    obj = {"summary": "가", "keywords": ["사업계획서"], "trl": 4}
    blob = crypto.encrypt_json(obj, "tenant_A", salt)
    assert blob.startswith(AESENC_SENTINEL)
    assert crypto.decrypt_json(blob, "tenant_A", salt) == obj


# ------------------------------------------------------------------ #
# 2. 테넌트 격리: salt/tenant 다르면 복호화 불가 (InvalidTag)
# ------------------------------------------------------------------ #
def test_tenant_isolation_invalid_tag():
    crypto = VaultCryptoManager()
    s_a = crypto.generate_tenant_salt()
    s_b = crypto.generate_tenant_salt()
    assert s_a != s_b
    blob = crypto.encrypt_text("기밀", "tenant_A", s_a)
    # 다른 tenant_id
    with pytest.raises(InvalidTag):
        crypto.decrypt_text(blob, "tenant_B", s_a)
    # 같은 id인데 salt가 다름
    with pytest.raises(InvalidTag):
        crypto.decrypt_text(blob, "tenant_A", s_b)


def test_mutated_blob_invalid_tag():
    crypto = VaultCryptoManager()
    blob = crypto.encrypt_text("기밀", "t")
    body = blob[len(AESENC_SENTINEL):]
    # 암호문 본문의 내부 바이트 1개 뒤집기(길이는 유지, GCM tag 불일치 → InvalidTag)
    mut_char = "A" if body[0] != "A" else "B"
    tampered = AESENC_SENTINEL + mut_char + body[1:]
    assert tampered != blob
    with pytest.raises(InvalidTag):
        crypto.decrypt_text(tampered, "t")


# ------------------------------------------------------------------ #
# 3. DB compromise 시 raw 저장값이 암호문이며 평문 유출 없음
# ------------------------------------------------------------------ #
@pytest.mark.asyncio
async def test_db_compromise_no_plaintext(tmp_path):
    db = GrantDatabase(tmp_path / "comp.db")
    db.ensure_schema()
    svc = TenantService(db)
    tenant, _, _ = svc.login_social_or_demo(
        provider="kakao", email="ceo@a.com", name="홍",
        company_name="(주)A", biz_reg_no="123-45-67890",
    )
    assert tenant.get("tenant_salt"), "신규 테넌트는 salt를 가짐"

    plaintext = "A사 기밀 사업 내용: 탄소중립 핵심 IP"
    await svc.ingest_vault_file(
        tenant_id=tenant["id"],
        filename="secret.txt",
        file_bytes=plaintext.encode("utf-8"),
        category="PROPOSAL",
    )

    # raw 저장값(서비스/보안 레이어 우회)이 암호문이어야 함
    raw = db.list_tenant_assets_raw(tenant["id"])
    assert len(raw) == 1
    assert raw[0]["content_text"].startswith(AESENC_SENTINEL)
    assert plaintext not in raw[0]["content_text"]
    assert raw[0]["parsed_metadata"].startswith(AESENC_SENTINEL)

    # 서비스/보안 레이어로 조회하면 평문 복호화(투명 복호화)
    decrypted = svc.list_decrypted_assets(tenant["id"])
    assert len(decrypted) == 1
    assert plaintext in decrypted[0]["content_text"] or "secret.txt" in decrypted[0]["content_text"]


# ------------------------------------------------------------------ #
# 4. zero-retention: 암호화 과정에서 파일 미기록
# ------------------------------------------------------------------ #
@pytest.mark.asyncio
async def test_zero_file_retention(tmp_path):
    db = GrantDatabase(tmp_path / "zr.db")
    db.ensure_schema()
    svc = TenantService(db)
    tenant, _, _ = svc.login_social_or_demo(
        provider="kakao", email="ceo@zr.com", name="조",
        company_name="(주)Z", biz_reg_no="000-11-22233",
    )
    await svc.ingest_vault_file(
        tenant_id=tenant["id"],
        filename="plan.txt",
        file_bytes="# 사업계획서 초안".encode("utf-8"),
        category="PROPOSAL",
    )
    # 암호화 산출물(.enc/.bin/.key 등)이 디스크에 남지 않음
    leaked = [p for p in tmp_path.iterdir()
              if p.suffix in (".enc", ".bin", ".key", ".dat")]
    assert leaked == [], f"zero-retention 위반: {leaked}"


# ------------------------------------------------------------------ #
# 5. 보안 헤더 5종 주입 (SecurityHeadersMiddleware)
# ------------------------------------------------------------------ #
def test_security_headers_present():
    client = TestClient(app)
    resp = client.get("/api/status")
    h = resp.headers
    assert "max-age=31536000" in h.get("strict-transport-security", "")
    assert "includeSubDomains" in h.get("strict-transport-security", "")
    assert h.get("x-content-type-options") == "nosniff"
    assert h.get("x-frame-options") == "DENY"
    assert "mode=block" in h.get("x-xss-protection", "")
    assert "strict-origin" in h.get("referrer-policy", "")


# ------------------------------------------------------------------ #
# 6. 레거시 평문 transparent passthrough
# ------------------------------------------------------------------ #
def test_legacy_plaintext_passthrough():
    crypto = get_crypto()
    plain = "레거시 평문 자산"
    # 센티넬 없는 값은 그대로 통과
    assert crypto.decrypt_text(plain) == plain
    # decrypt_asset_record: dict는 그대로, JSON 문자열은 파싱, AESENC는 복호화
    rec = decrypt_asset_record(
        {"content_text": "A사 내용", "parsed_metadata": {"summary": "메타"}},
        "t", "",
    )
    assert rec["content_text"] == "A사 내용"
    assert rec["parsed_metadata"]["summary"] == "메타"


def test_legacy_json_string_passthrough():
    rec = decrypt_asset_record(
        {"content_text": "x", "parsed_metadata": '{"summary": "레거시"}'},
        "t", "",
    )
    assert rec["parsed_metadata"]["summary"] == "레거시"

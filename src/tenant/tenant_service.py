"""
멀티테넌트 인증 및 기업 지식 자산고(Company Vault) 서비스
(src/tenant/tenant_service.py)
"""
from __future__ import annotations

import base64
import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Request, Response

from src.common.db import GrantDatabase
from src.common.logging_config import get_logger
from src.parser.proposal_parser import ProposalParser
from src.parser.proposal_extractor import ProposalExtractor

logger = get_logger("tenant_service")

COOKIE_SESSION_NAME = "sshai_session"
DEFAULT_TENANT_ID = "tenant_default"
DEFAULT_USER_ID = "user_default"


class TenantService:
    """멀티테넌트 격리 관리, 소셜/간이 로그인 세션 및 Company Vault 자산 관리 서비스."""

    def __init__(self, db: Optional[GrantDatabase] = None) -> None:
        self.db = db or GrantDatabase(Path(__file__).resolve().parent.parent.parent / "storage" / "grant_master.db")
        self.db.ensure_schema()
        self.extractor = ProposalExtractor()

    def get_current_session(self, request: Request) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        쿠키 또는 헤더에서 세션을 파싱하여 (tenant, user) 반환.
        미인증 또는 유효하지 않은 경우 안전하게 기본 테넌트(tenant_default)로 폴백.
        """
        # 1. 쿠키 또는 헤더에서 세션 토큰 확인
        session_token = request.cookies.get(COOKIE_SESSION_NAME) or request.headers.get("X-Session-Token")
        tenant_id = None
        user_id = None

        if session_token:
            try:
                # 간단한 base64 디코딩 (상용 배포 시 HMAC/JWT 서명 검증 확장)
                raw_json = base64.b64decode(session_token.encode("utf-8")).decode("utf-8")
                session_data = json.loads(raw_json)
                tenant_id = session_data.get("tenant_id")
                user_id = session_data.get("user_id")
            except Exception as e:
                logger.debug("세션 디코딩 실패, 기본값 사용: %s", e)

        # 2. 테넌트 및 유저 DB 조회
        tenant = None
        user = None
        if tenant_id and user_id:
            tenant = self.db.get_tenant(tenant_id)
            user = self.db.get_user(user_id)

        # 3. 폴백: 기본 테넌트 및 유저
        if not tenant:
            tenant = self.db.get_tenant(DEFAULT_TENANT_ID) or {
                "id": DEFAULT_TENANT_ID,
                "company_name": "(주)초롱소프트 / SSHAI",
                "biz_reg_no": "123-45-67890",
                "opened_date": "2024-01-15",
                "rep_name": "홍길동",
                "region": "서울",
                "plan_tier": "PRO",
            }
        if not user:
            user = self.db.get_user(DEFAULT_USER_ID) or {
                "id": DEFAULT_USER_ID,
                "tenant_id": tenant["id"],
                "email": "ceo@chorong.ai",
                "name": "홍길동 대표",
                "auth_provider": "local_demo",
                "role": "OWNER",
            }

        return tenant, user

    def create_session_token(self, tenant_id: str, user_id: str, email: str) -> str:
        """세션 토큰 생성 (Base64 JSON 직렬화)."""
        payload = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "email": email,
            "issued_at": uuid.uuid4().hex[:8],
        }
        return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")

    def login_social_or_demo(
        self,
        provider: str,
        email: str,
        name: str,
        company_name: Optional[str] = None,
        biz_reg_no: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
        """
        소셜 로그인(카카오, 구글) 또는 데모 간이 로그인 처리.
        신규 사용자/기업인 경우 신규 테넌트 자동 생성, 기존이면 갱신.
        """
        # 이메일로 기존 사용자 탐색
        existing_user = self.db.get_user_by_email(email)
        if existing_user:
            user_id = existing_user["id"]
            tenant_id = existing_user["tenant_id"]
            tenant = self.db.get_tenant(tenant_id)
        else:
            # 신규 테넌트 생성
            tenant_id = f"tenant_{uuid.uuid4().hex[:12]}"
            c_name = company_name or f"{name}의 기업"
            tenant = {
                "id": tenant_id,
                "company_name": c_name,
                "biz_reg_no": biz_reg_no or "",
                "opened_date": "2024-01-01",
                "rep_name": name,
                "region": "서울",
                "plan_tier": "PRO",
            }
            self.db.upsert_tenant(tenant)

            # 신규 사용자 생성
            user_id = f"user_{uuid.uuid4().hex[:12]}"
            new_user = {
                "id": user_id,
                "tenant_id": tenant_id,
                "email": email,
                "name": name,
                "avatar_url": "",
                "auth_provider": provider,
                "role": "OWNER",
            }
            self.db.upsert_user(new_user)
            existing_user = new_user

        token = self.create_session_token(tenant_id, user_id, email)
        return tenant, existing_user, token

    async def ingest_vault_file(
        self,
        tenant_id: str,
        filename: str,
        file_bytes: bytes,
        category: str = "PROPOSAL",
    ) -> Dict[str, Any]:
        """
        Company Vault 파일 업로드 처리:
        1. Pure Python 텍스트 추출 (HWPX, HWP, PDF, DOCX, TXT)
        2. AI 정형 스펙 추출 (ProposalExtractor)
        3. tenant_assets DB 적재
        """
        asset_id = f"asset_{uuid.uuid4().hex[:12]}"
        file_size = len(file_bytes)

        # 1. 텍스트 추출
        extracted_text = ProposalParser.extract_text(file_bytes, filename)
        if not extracted_text:
            extracted_text = f"[{filename}] 업로드된 문서 원문 (텍스트 파싱 대기)"

        # 2. AI 정형 메타데이터 추출
        parsed_meta: Dict[str, Any] = {}
        try:
            parsed_meta = await self.extractor.extract(extracted_text)
        except Exception as e:
            logger.warning("자산 메타데이터 추출 중 예외(degrade): %s", e)
            parsed_meta = {
                "summary": extracted_text[:300].strip(),
                "keywords": ["사업계획서", "기업자산"],
                "trl": 4,
            }

        # 3. DB 적재
        asset_record = {
            "id": asset_id,
            "tenant_id": tenant_id,
            "asset_category": category,
            "file_name": filename,
            "file_size": file_size,
            "content_text": extracted_text,
            "parsed_metadata": parsed_meta,
        }
        self.db.add_tenant_asset(asset_record)

        # 4. 마스터 기업 스펙에 유효 정보가 있으면 테넌트 기본 정보 자동 보강
        comp_specs = parsed_meta.get("company_specs", {})
        if comp_specs:
            curr_tenant = self.db.get_tenant(tenant_id) or {}
            c_name = comp_specs.get("company_name") or curr_tenant.get("company_name")
            b_no = comp_specs.get("biz_reg_no") or curr_tenant.get("biz_reg_no")
            rep = comp_specs.get("rep_name") or curr_tenant.get("rep_name")
            opened = comp_specs.get("opened_date") or curr_tenant.get("opened_date")
            self.db.upsert_tenant({
                "id": tenant_id,
                "company_name": c_name,
                "biz_reg_no": b_no,
                "opened_date": opened,
                "rep_name": rep,
                "region": curr_tenant.get("region", "서울"),
                "plan_tier": curr_tenant.get("plan_tier", "PRO"),
            })

        return asset_record

    def get_vault_summary(self, tenant_id: str) -> Dict[str, Any]:
        """테넌트의 지식 데이터 룸 적재 현황 및 준비도 집계."""
        assets = self.db.list_tenant_assets(tenant_id)
        categories = {
            "PROPOSAL": [],
            "PITCH_DECK": [],
            "BUDGET": [],
            "CERT_PATENT": [],
        }
        for a in assets:
            cat = a.get("asset_category", "PROPOSAL")
            if cat in categories:
                categories[cat].append(a)
            else:
                categories["PROPOSAL"].append(a)

        # 4대 핵심 자산 준비도 (최대 100점)
        score = 0
        if categories["PROPOSAL"]: score += 40
        if categories["PITCH_DECK"]: score += 20
        if categories["BUDGET"]: score += 20
        if categories["CERT_PATENT"]: score += 20

        return {
            "total_assets": len(assets),
            "vault_readiness_score": score,
            "proposals_count": len(categories["PROPOSAL"]),
            "pitch_decks_count": len(categories["PITCH_DECK"]),
            "budgets_count": len(categories["BUDGET"]),
            "certs_count": len(categories["CERT_PATENT"]),
            "assets_by_category": categories,
        }

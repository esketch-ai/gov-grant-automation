"""
REQ-029 · Vault 자산 기반 초정밀 맞춤 매칭기 (`VaultPreflightMatcher`)

Company Vault(REQ-028)에 적재된 기업의 고유 자산(`tenants` + `tenant_assets`)을
취합해 가상 `company_specs`를 만들고, 검증된 2대 엔진으로 구동되는 `PreflightService`
를 통해 25대 지원 조건 신호등을 실행한다.

- RED (사전 탈락) 공고는 추천 결과에서 자동 제외한다.
- GREEN/YELLOW는 특허/연구소/TRL/인증 등 Vault 자산으로 산출된 우대점에 따라
  `Match Score`로 정렬되어 초정밀 추천된다.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from src.common.db import GrantDatabase
from src.common.logging_config import get_logger
from src.common.schemas import RawNotice
from src.matcher.preflight import PreflightService

logger = get_logger("vault_preflight")


class VaultPreflightMatcher:
    """VAULT 테넌트 자산 → 가상 company_specs → Preflight 25대 신호등 기반 매칭기."""

    def __init__(
        self,
        db: Optional[GrantDatabase] = None,
        preflight: Optional[PreflightService] = None,
    ) -> None:
        self.db = db or GrantDatabase()
        self.preflight = preflight or PreflightService()

    # ------------------------------------------------------------------
    # VAULT 자산 취합 → 가상 company_specs
    # ------------------------------------------------------------------
    def build_company_specs(self, tenant_id: str) -> Dict[str, Any]:
        """tenants + tenant_assets 메타데이터를 취합해 Preflight 프로필을 생성."""
        specs: Dict[str, Any] = {}
        tenant = self.db.get_tenant(tenant_id) if tenant_id else None
        if tenant:
            specs.update({
                "company_name": tenant.get("company_name", ""),
                "biz_reg_no": tenant.get("biz_reg_no", ""),
                "opened_date": tenant.get("opened_date", ""),
                "address": tenant.get("region", ""),
                "founder_gender": "unknown",
            })

        # Vault 자산에서 우대/기술 신호를 취합
        try:
            assets = self.db.list_tenant_assets(tenant_id)
        except Exception as e:
            logger.debug("자산 조회 실패(degrade): %s", e)
            assets = []

        patents_count = 0
        has_patents = has_research_lab = has_venture = False
        trl_levels: List[int] = []
        certifications: List[str] = []
        for a in assets:
            meta = self._parse_meta(a.get("parsed_metadata"))
            patents_count += int(meta.get("patents_count", 0) or 0)
            has_patents = has_patents or bool(meta.get("has_patents"))
            has_venture = has_venture or bool(meta.get("has_venture"))
            has_research_lab = has_research_lab or bool(meta.get("has_research_lab"))
            t = meta.get("trl")
            if isinstance(t, int) or (isinstance(t, str) and t.isdigit()):
                trl_levels.append(int(t))
            certs = meta.get("certifications")
            if certs:
                certifications.extend(certs if isinstance(certs, list) else [str(certs)])
            keywords = meta.get("keywords")
            if keywords:
                specs.setdefault("_keywords", []).extend(
                    keywords if isinstance(keywords, list) else [str(keywords)]
                )

        specs["has_patents"] = has_patents
        specs["patents_count"] = patents_count
        specs["has_research_lab"] = has_research_lab
        specs["has_venture"] = has_venture
        specs["trl_levels"] = trl_levels
        specs["certifications"] = certifications
        return specs

    @staticmethod
    def _parse_meta(raw: Any) -> Dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str) and raw.strip():
            try:
                obj = json.loads(raw)
                return obj if isinstance(obj, dict) else {}
            except Exception:
                return {}
        return {}

    # ------------------------------------------------------------------
    # 25대 신호등 매칭 (RED 자동제거 + 우대점수 정렬)
    # ------------------------------------------------------------------
    def match(self, tenant_id: str, notices: List[RawNotice]) -> List[Dict[str, Any]]:
        """VAULT 자산으로 가상 스펙을 만들고 각 공고를 신호등 판정, RED 제외 후 점수 정렬."""
        specs = self.build_company_specs(tenant_id)
        results: List[Dict[str, Any]] = []
        for notice in notices:
            try:
                verdict = self.preflight.run(specs, notice)
            except Exception as e:
                logger.warning("preflight 실패(degrade): %s", e)
                continue
            if verdict.get("signal_light") == "red":
                continue  # RED = 사전 탈락 → 자동 제외 (run()는 소문자 신호등 반환)
            results.append({
                "canonical_id": notice.portal_id,
                "title": notice.title,
                "organization": notice.organization,
                "ministry": notice.ministry,
                "deadline": notice.deadline,
                "signal_light": verdict.get("signal_light"),  # green / yellow
                "match_score": round(float(verdict.get("final_score", 0) or 0), 2),
                "bonus_points": len(verdict.get("bonus_points") or []),
                "matched_track": verdict.get("matched_track"),
                "tags": verdict.get("tags", []),
                "pass_reasons": verdict.get("pass_reasons", []),
                "disqualification_reasons": verdict.get("disqualification_reasons", []),
            })
        results.sort(key=lambda r: r["match_score"], reverse=True)
        return results

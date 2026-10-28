"""
REQ-032 · 멀티테넌트 SaaS 상용화 코어 엔진 (tenant 모듈).

- billing.CommercialService 핵심 로직을 임포트하여 재사용
- export_hwpx_bytes / export_docx_bytes 위임 지원
- 1테넌트=1사업자 Hard-Lock, 이용 한도/바우처 원장, 멤버십 페이월, 구독/환불 등
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.billing.commercial_service import (
    CommercialService as BaseService,
    export_hwpx_bytes,
    export_docx_bytes,
    TIERS,
    VAT_RATE,
    ANNUAL_DISCOUNT,
    FREE_OPEN_SECTIONS,
    TOPUP_PACKS,
    vat_split,
    topup_pack,
    tier_pricing,
    check_paywall_access,
    is_free_tier,
)


# ------------------------------------------------------------------ 테넌트 전용 CommercialService 클래스
class CommercialService(BaseService):
    """테넌트 격리된 상용화 엔진. BaseService 로직을 상속/재사용."""

    def __init__(self, db: Optional[Any] = None):
        # 상위 클래스는 self.db 할당 후 gateway 설정
        self.db = db
        self.gateway = super().gateway.__class__(self) if hasattr(super(), "gateway") else None

    # ---------- 속성 ----------
    def is_free_tier(self, tenant: Optional[dict]) -> bool:
        return super().is_free_tier(tenant)

    def check_paywall_access(self, tenant: Optional[dict], section_no: int = 1, action: str = "read") -> dict:
        return super().check_paywall_access(tenant, section_no, action)

    # ---------- 내보내기 위임 ----------
    def export_hwpx(self, title: str, sections: List[dict]) -> bytes:
        """HWPX/ZIP 바이트 내보내기 (billing 모듈 위임)."""
        return export_hwpx_bytes(title, sections)

    def export_docx(self, title: str, sections: List[dict]) -> bytes:
        """DOCX/ZIP 바이트 내보내기 (billing 모듈 위임)."""
        return export_docx_bytes(title, sections)


# ------------------------------------------------------------------ 헬퍼
def _norm_tier(tenant: Optional[dict]) -> str:
    if not tenant:
        return "free"
    t = (tenant.get("subscription_tier") or tenant.get("plan_tier") or "free").lower()
    if t in ("pro",):
        t = "growth"
    elif t in ("enterprise",):
        t = "agency"
    return t if t in TIERS else "free"
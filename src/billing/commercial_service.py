"""
REQ-032 · 실전 유료화 B2B SaaS 코어 엔진.

- 4-Tier 요금제(free/growth/scaleup/agency), 월간/연간(20% 할인), VAT 10% 별도/합산
- 1테넌트 = 1사업자등록번호 Hard-Lock(대행 어뷰징 차단, Agency만 다중 사업자)
- 이용 한도/바우처 원장(credit_ledger) 차감/Top-Up 충전팩, 잔여 한도 소진 시 추가 이용 통제
  (※ 본 플랫폼은 사업계획서 대필이나 AI 생성형 텍스트 토큰을 판매하지 않으며, 공고 매칭 및 요건 분석 한도를 관리합니다.)
- 블러 페이월 가드: Free는 공고 요건 분석 1장(문제인식, section 1)까지만 열람,
  2장(기술개발)~4장(예산표)는 블러 & HWPX/DOCX 다운로드는 402 차단
- 일할(Proration) & 전자상거래법 부분 환불 정산
- 토스 빌링(Toss Billing) 정기결제 생명주기 + Dunning(+1/+3/+7) & PAST_DUE 상태머신
- 해시 체인 불변 감사로그(append_audit / verify_audit_chain, DB 직접 조작 탐지)
- 5대 BM 5-KPI 대시보드 집계
"""
from __future__ import annotations

import hashlib
import uuid
from typing import Any, Dict, List, Optional

from src.common.db import GrantDatabase
from src.common.logging_config import get_logger

logger = get_logger("commercial_service")

# ------------------------------------------------------------------ 상수
# 4-Tier 월간 공급가액(원, VAT 별도) & 월간 서비스 이용 한도(하위호환 키명 credits_month 유지)
TIERS: Dict[str, dict] = {
    "free":    {"name": "Free",     "supply_price": 0,     "credits_month": 10,   "multi_biz": False},
    "growth":  {"name": "Growth",   "supply_price": 39000, "credits_month": 500,  "multi_biz": False},
    "scaleup": {"name": "Scale-Up", "supply_price": 120000,"credits_month": 1500, "multi_biz": False},
    "agency":  {"name": "Agency",   "supply_price": 300000,"credits_month": 5000, "multi_biz": True},
}
VAT_RATE = 0.10            # 부가세 10% 별도
ANNUAL_DISCOUNT = 0.80     # 연간결제 20% 할인
CREDIT_UNIT_PRICE = 100    # 이용단위 1개당 100원(환불 정산 기준가)
PENALTY_RATE = 0.10        # 위약금 10%
DUNNING_SCHEDULE = (1, 3, 7)  # 미납 재시도 +1/+3/+7일
GENESIS_HASH = "0" * 64
# Free 티어에서 열람 가능한 공고 요건 분석 섹션(1=문제인식). 2~4(기술개발/추진/예산)는 유료.
FREE_OPEN_SECTIONS = {1}
# Top-Up 충전팩: 추가 이용 바우처 300회 = 1.9만원(합산, 하위호환)
TOPUP_PACKS = [
    {"id": "pack_300", "credits": 300, "total_krw": 19000},
]


# ------------------------------------------------------------------ 요금/세
def vat_split(supply: int) -> tuple:
    """공급가액 → (공급가액, 부가세, 합산액)."""
    supply = int(round(supply))
    vat = int(round(supply * VAT_RATE))
    return supply, vat, supply + vat


def topup_pack(pack: dict) -> dict:
    """충전팩의 합산액 → 공급가액/부가세/합산 분리."""
    total = int(pack.get("total_krw", 19000))
    credits = int(pack.get("credits", 300))
    vat = int(round(total * VAT_RATE / (1 + VAT_RATE)))
    return {"id": pack.get("id", "pack"), "credits": credits,
            "supply_price": total - vat, "vat_amount": vat, "total_amount": total}


def tier_pricing(tier: str, cycle: str = "monthly") -> dict:
    """티어×청구주기 → {tier, cycle, supply_price, vat_amount, total_amount, credits_month}."""
    spec = TIERS.get(tier, TIERS["free"])
    supply = int(spec["supply_price"])
    if cycle == "annual":
        supply = int(round(supply * 12 * ANNUAL_DISCOUNT))
    s, v, total = vat_split(supply)
    return {"tier": tier, "cycle": cycle, "supply_price": s, "vat_amount": v,
            "total_amount": total, "credits_month": spec["credits_month"], "multi_biz": spec["multi_biz"]}


# ------------------------------------------------------------------ 페이월
def _norm_tier(tenant: Optional[dict]) -> str:
    if not tenant:
        return "free"
    t = (tenant.get("subscription_tier") or tenant.get("plan_tier") or "free").lower()
    if t in ("pro",):
        t = "growth"
    elif t in ("enterprise",):
        t = "agency"
    return t if t in TIERS else "free"


def is_free_tier(tenant: Optional[dict]) -> bool:
    return _norm_tier(tenant) == "free"


def check_paywall_access(tenant: Optional[dict], section_no: int = 1, action: str = "read") -> dict:
    """블러 페이월 가드.

    - free 티어는 section_no>=2(기술개발/추진/예산) 본문 블러, 모든 다운로드 402 차단.
    - 유료 티어는 전체 열람/다운로드 허용.
    - 반환 {tier, allowed, blurred, http_code, reason}.
    """
    tier = _norm_tier(tenant)
    base: Dict[str, Any] = {
        "tier": tier, "section_no": section_no, "action": action,
        "allowed": True, "blurred": False, "http_code": 200, "reason": "OK",
    }
    if not is_free_tier(tenant):
        base["reason"] = "UNLOCKED"
        return base
    # --- Free 티어 ---
    if action == "download":
        base.update(allowed=False, http_code=402, blurred=True, reason="FREE_DOWNLOAD_LOCKED")
        return base
    if section_no not in FREE_OPEN_SECTIONS:
        base.update(allowed=False, http_code=402, blurred=True, reason="PAYWALL_BLUR")
        return base
    base["reason"] = "FREE_PREVIEW"
    return base


# ------------------------------------------------------------------ 서비스
class CommercialService:
    """이용 한도 원장 / 구독 / 환불 / 감사로그 / BM 집계. DB는 self.db._connect()로 직접 접근."""

    def __init__(self, db: Optional[GrantDatabase] = None):
        self.db = db
        self.gateway = TossBillingGateway(self)

    # ---------- 이용 한도 원장 (하위 호환 credit_ledger) ----------
    def _credit_balance(self, tenant_id: str) -> int:
        t = self.db.get_tenant(tenant_id) if self.db else None
        if not t:
            return 0
        return int(t.get("credit_balance") or 0)

    def _set_tenant_field(self, tenant_id: str, **fields: Any) -> None:
        """허용된 컬럼만 표적 UPDATE(biz_model/subscription_tier/credit_balance)."""
        allowed = {"biz_model", "subscription_tier", "credit_balance"}
        fields = {k: v for k, v in fields.items() if k in allowed}
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        with self.db._connect() as conn:
            conn.execute(f"UPDATE tenants SET {cols} WHERE id = ?", (*list(fields.values()), tenant_id))
            conn.commit()

    def consume_credits(self, tenant_id: str, amount: int, reason: str = "GENERATION",
                        project_id: str = "") -> dict:
        """이용 한도 차감. 잔여 한도 부족 시 INSUFFICIENT_CREDITS."""
        amount = int(amount)
        bal = self._credit_balance(tenant_id)
        if amount > 0 and bal < amount:
            return {"ok": False, "reason": "INSUFFICIENT_CREDITS", "balance": bal, "required": amount}
        new_bal = bal - amount
        with self.db._connect() as conn:
            conn.execute(
                "INSERT INTO credit_ledger (tenant_id, delta, balance_after, reason, project_id) "
                "VALUES (?,?,?,?,?)",
                (tenant_id, -amount, new_bal, reason, project_id),
            )
            conn.execute("UPDATE tenants SET credit_balance = ? WHERE id = ?", (new_bal, tenant_id))
            conn.commit()
        return {"ok": True, "delta": -amount, "balance": new_bal, "reason": reason}

    def topup_credits(self, tenant_id: str, pack: Optional[dict] = None, tx_hash: str = "") -> dict:
        """Top-Up 추가 옵션팩 → 이용 한도 충전 + payments 기록."""
        info = topup_pack(pack or TOPUP_PACKS[0])
        credits = info["credits"]
        balance_before = self._credit_balance(tenant_id)
        new_bal = balance_before + credits
        pid = f"pay_{uuid.uuid4().hex[:12]}"
        with self.db._connect() as conn:
            conn.execute(
                """INSERT INTO payments (id, tenant_id, subscription_id, payment_type,
                   supply_amount, vat_amount, total_amount, refunded_amount, status,
                   tax_invoice_status, receipt_url)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (pid, tenant_id, "", "TOPUP", info["supply_price"], info["vat_amount"],
                 info["total_amount"], 0, "PAID", "ISSUED", f"/receipts/{pid}.html"),
            )
            conn.execute(
                "INSERT INTO credit_ledger (tenant_id, delta, balance_after, reason, project_id) "
                "VALUES (?,?,?,?,?)",
                (tenant_id, credits, new_bal, "TOPUP", pid),
            )
            conn.execute("UPDATE tenants SET credit_balance = ? WHERE id = ?", (new_bal, tenant_id))
            conn.commit()
        return {"ok": True, "payment_id": pid, "credits": credits,
                "balance": new_bal, "total": info["total_amount"], "vat": info["vat_amount"]}

    # ---------- 1테넌트=1사업자 Hard-Lock ----------
    def biz_reg_in_use_by_other(self, biz_reg_no: str, tenant_id: str) -> Optional[str]:
        """사업자등록번호가 다른 테넌트에 이미 할당된 경우 그 테넌트 id 반환(충돌). 없으면 None."""
        if not biz_reg_no:
            return None
        with self.db._connect() as conn:
            row = conn.execute(
                "SELECT id FROM tenants WHERE biz_reg_no = ? AND id != ? LIMIT 1",
                (biz_reg_no, tenant_id),
            ).fetchone()
        return row["id"] if row else None

    def assert_biz_reg_unique(self, tenant_id: str, biz_reg_no: str,
                              allow_multi_biz: bool = False) -> dict:
        """1테넌트=1사업자 Hard-Lock 검증. 충돌 시 예외.

        allow_multi_biz=True(Agency)면 다중 사업자 허용 → 충돌 무시.
        """
        collision = self.biz_reg_in_use_by_other(biz_reg_no, tenant_id)
        if collision and not allow_multi_biz:
            raise ValueError(f"BIZ_REG_LOCK: 사업자 {biz_reg_no}는 이미 다른 테넌트({collision})에 할당됨")
        return {"ok": True, "collision": collision, "allowed_multi": allow_multi_biz}

    def check_biz_reg_available(self, biz_reg_no: str, tenant_id: str = "") -> bool:
        """해당 사업자등록번호가 신규 배정 가능한지(충돌 없는지)."""
        return self.biz_reg_in_use_by_other(biz_reg_no, tenant_id) is None

    # ---------- 구독(정기결제) ----------
    def subscribe(self, tenant_id: str, tier: str, cycle: str = "monthly",
                  biz_reg_no: str = "", actor: str = "",
                  current_period_start: str = "", current_period_end: str = "") -> dict:
        """구독 체결: 1테넌트=1사업자 Hard-Lock + 티어 설정 + 월간 이용 한도 부여 + subscription 기록."""
        spec = TIERS.get(tier, TIERS["free"])
        self.assert_biz_reg_unique(tenant_id, biz_reg_no, allow_multi_biz=spec.get("multi_biz", False))
        pr = tier_pricing(tier, cycle)
        sub_id = f"sub_{uuid.uuid4().hex[:12]}"
        with self.db._connect() as conn:
            conn.execute(
                """INSERT INTO subscriptions (id, tenant_id, plan_code, billing_cycle,
                   supply_price, vat_amount, status, current_period_start, current_period_end)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (sub_id, tenant_id, tier, cycle, pr["supply_price"], pr["vat_amount"],
                 "ACTIVE", current_period_start, current_period_end),
            )
            conn.execute(
                "INSERT INTO credit_ledger (tenant_id, delta, balance_after, reason, project_id) "
                "VALUES (?,?,?,?,?)",
                (tenant_id, pr["credits_month"], pr["credits_month"], "SUBSCRIPTION_GRANT", sub_id),
            )
            conn.commit()
        self._set_tenant_field(
            tenant_id,
            subscription_tier=tier,
            credit_balance=pr["credits_month"],
        )
        return {"ok": True, "subscription_id": sub_id, "tier": tier, "cycle": cycle,
                "credits_month": pr["credits_month"], "total_amount": pr["total_amount"],
                "proration": self.calculate_proration(_old_tier(tenant_id, self.db), tier, 30, cycle=cycle)}

    # ---------- 일할 & 환불 ----------
    def calculate_proration(self, old_tier: str, new_tier: str, days_remaining: int,
                            period_days: int = 30, cycle: str = "monthly") -> dict:
        """중도 업그레이드/등급 변경 일할(Proration). 잔여 일수 비례 차액."""
        diff = tier_pricing(new_tier, cycle)["supply_price"] - tier_pricing(old_tier, cycle)["supply_price"]
        supply = int(round(max(diff, 0) * days_remaining / period_days)) if period_days else 0
        s, v, total = vat_split(supply)
        return {"old_tier": old_tier, "new_tier": new_tier, "days_remaining": days_remaining,
                "supply_price": s, "vat_amount": v, "total_amount": total}

    def calculate_refund(self, total_paid: int, days_used: int, used_credits: int = 0,
                         period_days: int = 30, penalty_rate: float = PENALTY_RATE,
                         credit_unit_price: int = CREDIT_UNIT_PRICE) -> dict:
        """전자상거래법 부분 환불: 실결제액 - (사용일수 일할 + 사용한도 차감정산 + 위약금 10%)."""
        total_paid = int(total_paid)
        days_used = max(0, min(int(days_used), period_days))
        proration_consumed = int(round(total_paid * days_used / period_days)) if period_days else 0
        credit_cost = int(used_credits) * credit_unit_price
        penalty = int(round(total_paid * penalty_rate))
        refund = total_paid - proration_consumed - credit_cost - penalty
        return {"total_paid": total_paid, "proration_consumed": proration_consumed,
                "credit_cost": credit_cost, "penalty": penalty, "refund": max(refund, 0)}

    def charge(self, tenant_id: str, total_amount: int, subscription_id: str = "",
               payment_type: str = "SUBSCRIPTION", tx_hash: str = "", actor: str = "") -> dict:
        """정기결제 정산: payments 기록 + 세금계산서 ISSUED."""
        vat = int(round(total_amount * VAT_RATE / (1 + VAT_RATE)))
        supply = total_amount - vat
        pid = f"pay_{uuid.uuid4().hex[:12]}"
        with self.db._connect() as conn:
            conn.execute(
                """INSERT INTO payments (id, tenant_id, subscription_id, payment_type,
                   supply_amount, vat_amount, total_amount, refunded_amount, status,
                   tax_invoice_status, receipt_url) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (pid, tenant_id, subscription_id, payment_type, supply, vat, total_amount,
                 0, "PAID", "ISSUED", f"/receipts/{pid}.html"),
            )
            conn.commit()
        self.append_audit(tenant_id, actor, "BILLING",
                          f"CHARGE:{payment_type}:{total_amount}", ip="")
        return {"ok": True, "payment_id": pid, "total_amount": total_amount, "vat": vat}

    # ---------- Dunning / PAST_DUE 상태머신 ----------
    def run_dunning(self, attempt_no: int = 1) -> dict:
        """미납 재시도 +1/+3/+7일. 1~2회 PAST_DUE, 3회 이후 CANCELED_PENDING(grace)."""
        attempt_no = int(attempt_no)
        if attempt_no <= 0:
            return {"status": "ACTIVE", "retry_count": 0, "retry_at": None}
        if 1 <= attempt_no <= len(DUNNING_SCHEDULE):
            status = "PAST_DUE" if attempt_no < len(DUNNING_SCHEDULE) else "CANCELED_PENDING"
            return {"status": status, "retry_count": attempt_no,
                    "retry_at": f"+{DUNNING_SCHEDULE[attempt_no - 1]}일"}
        return {"status": "CANCELED_PENDING", "retry_count": attempt_no, "retry_at": None, "final": True}

    # ---------- 해시체인 감사로그 ----------
    @staticmethod
    def _hash_row(prev_hash: str, tenant_id: str, actor: str, category: str,
                  action: str, ip: str) -> str:
        payload = f"{prev_hash}|{tenant_id or ''}|{actor or ''}|{category or ''}|{action or ''}|{ip or ''}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def append_audit(self, tenant_id: str = "", actor: str = "", category: str = "",
                     action: str = "", ip: str = "") -> dict:
        """해시 체인에 감사로그 1건 추가(전 기록 curr_hash를 prev로 연결)."""
        with self.db._connect() as conn:
            last = conn.execute(
                "SELECT curr_hash FROM audit_logs ORDER BY id DESC LIMIT 1"
            ).fetchone()
            prev = last["curr_hash"] if last else GENESIS_HASH
            cur = self._hash_row(prev, tenant_id, actor, category, action, ip)
            conn.execute(
                "INSERT INTO audit_logs (tenant_id, actor_user_id, category, action, "
                "ip_address, prev_hash, curr_hash) VALUES (?,?,?,?,?,?,?)",
                (tenant_id, actor, category, action, ip, prev, cur),
            )
            conn.commit()
        return {"prev_hash": prev, "curr_hash": cur}

    def verify_audit_chain(self) -> dict:
        """해시 체인 무결성 검증. DB 직접 조작(수정/삭제) 시 ok=False + broken_at 반환."""
        with self.db._connect() as conn:
            rows = conn.execute("SELECT * FROM audit_logs ORDER BY id ASC").fetchall()
        prev = GENESIS_HASH
        for r in rows:
            if r["prev_hash"] != prev:
                return {"ok": False, "broken_at": r["id"], "reason": "PREV_LINK_BROKEN",
                        "expected_prev": prev, "found_prev": r["prev_hash"]}
            expected = self._hash_row(prev, r["tenant_id"], r["actor_user_id"],
                                      r["category"], r["action"], r["ip_address"])
            if r["curr_hash"] != expected:
                return {"ok": False, "broken_at": r["id"], "reason": "HASH_TAMPERED",
                        "expected": expected, "found": r["curr_hash"]}
            prev = r["curr_hash"]
        return {"ok": True, "verified_count": len(rows)}

    # ---------- 5대 BM 5-KPI ----------
    def get_5kpi(self, tenant_id: str = "") -> dict:
        """5대 비즈니스 메트릭 KPI. tenant_id 공백 시 플랫폼 전체, 지정 시 해당 테넌트."""
        with self.db._connect() as conn:
            if tenant_id:
                sub = "WHERE status='ACTIVE' AND tenant_id = ?"
                pay = "WHERE tenant_id = ?"
                led = "tenant_id = ?"
                qsub = [tenant_id]
                qpay = [tenant_id]
                qled = [tenant_id]
            else:
                sub = "WHERE status='ACTIVE'"
                pay = "WHERE status='PAID' OR status IS NULL OR status='REFUNDED'"
                led = "WHERE 1=1"
                qsub = []
                qpay = []
                qled = []
            mrr_rows = conn.execute(f"SELECT supply_price FROM subscriptions {sub}", qsub).fetchall()
            mrr = sum(int(r["supply_price"] or 0) for r in mrr_rows)
            rev = conn.execute(
                f"SELECT COALESCE(SUM(total_amount - refunded_amount), 0) AS net FROM payments {pay}",
                qpay,
            ).fetchone()
            credits_consumed = -int(conn.execute(
                f"SELECT COALESCE(SUM(delta), 0) AS d FROM credit_ledger WHERE {led} AND delta < 0", qled,
            ).fetchone()["d"])
        return {
            "mrr": mrr,
            "arr": mrr * 12,
            "credits_consumed": credits_consumed,
            "net_revenue": int(rev["net"]) if rev else 0,
        }


# ------------------------------------------------------------------ 토스 빌링 게이트웨이
class TossBillingGateway:
    """Toss Billing 정기결제 생명주기(오프라인 시뮬레이션).

    proration/refund 정산·이용 한도 정산은 CommercialService가 담당.
    결제/환불/정산 리콘시리레이션은 결정론적으로 mock하여 오프라인 테스트.
    """

    def __init__(self, service: CommercialService):
        self.service = service

    def create_subscription(self, tenant_id: str, tier: str, cycle: str = "monthly",
                           biz_reg_no: str = "", actor: str = "") -> dict:
        return self.service.subscribe(tenant_id, tier, cycle, biz_reg_no, actor)

    def charge(self, tenant_id: str, total_amount: int, subscription_id: str = "",
               payment_type: str = "SUBSCRIPTION", tx_hash: str = "", actor: str = "") -> dict:
        """정기결제 정산: payments 기록 + 세금계산서 ISSUED."""
        vat = int(round(total_amount * VAT_RATE / (1 + VAT_RATE)))
        supply = total_amount - vat
        pid = f"pay_{uuid.uuid4().hex[:12]}"
        with self.service.db._connect() as conn:
            conn.execute(
                """INSERT INTO payments (id, tenant_id, subscription_id, payment_type,
                   supply_amount, vat_amount, total_amount, refunded_amount, status,
                   tax_invoice_status, receipt_url) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (pid, tenant_id, subscription_id, payment_type, supply, vat, total_amount,
                 0, "PAID", "ISSUED", f"/receipts/{pid}.html"),
            )
            conn.commit()
        self.service.append_audit(tenant_id, actor, "BILLING",
                                  f"CHARGE:{payment_type}:{total_amount}", ip="")
        return {"ok": True, "payment_id": pid, "total_amount": total_amount, "vat": vat}

    def reconcile_refund(self, payment_id: str, refund_amount: int, tenant_id: str,
                         actor: str = "") -> dict:
        """부분 환불 정산: payments.refunded_amount 가산 + REFUNDED 상태."""
        with self.service.db._connect() as conn:
            row = conn.execute(
                "SELECT refunded_amount FROM payments WHERE id = ?",
                (payment_id,),
            ).fetchone()
            if not row:
                return {"ok": False, "reason": "PAYMENT_NOT_FOUND"}
            new_ref = int(row["refunded_amount"] or 0) + int(refund_amount)
            conn.execute(
                "UPDATE payments SET refunded_amount = ?, status = ? WHERE id = ?",
                (new_ref, "REFUNDED" if int(refund_amount) > 0 else "PAID", payment_id),
            )
            conn.commit()
        self.service.append_audit(tenant_id, actor, "BILLING",
                                  f"REFUND:{payment_id}:{refund_amount}", ip="")
        return {"ok": True, "payment_id": payment_id, "refunded_amount": new_ref}


# ------------------------------------------------------------------ 헬퍼
def _old_tier(tenant_id: str, db: Optional[GrantDatabase]) -> str:
    """변경 전 티어 조회(없으면 free)."""
    if db is None:
        return "free"
    t = db.get_tenant(tenant_id)
    return _norm_tier(t or {})


# ------------------------------------------------------------------ HWPY/DOCX 내보내기 함수
def export_hwpx_bytes(title: str, sections: list) -> bytes:
    """비즈니스 로직 없이 HWPX/ZIP 바이트 생성(향후 실제 파이썬 HWPX 파서 연동).
    sections: [{section_id, title, content}] 형태의 섹션 목록."""
    import json, uuid, zipfile, io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, sec in enumerate(sections):
            # 메타데이터 XML
            meta_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                  <w:body>
                    <w:p>
                      <w:r>
                        <w:t xml:space="preserve">{sec.get("title", f"Section {i+1}")}</w:t>
                      </w:r>
                    </w:p>
                  </w:body>
                </w:document>"""
            zf.writestr(f"content_{i+1}_{title}.hwxpx", meta_xml.encode("utf-8"))
        # [문서 매니페스트]
        manifest = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
              <w:partName>/documents/{title}.hwxpx</w:partName>
              <w:contentTypes xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
                <Default ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document" Extension=".hwxpx"/>
                <Override PartName="/documents/{title}.hwxpx" ContentType="application/vnd.ms-word.hwxpx"/>
              </w:contentTypes>
            </w:document>"""
        zf.writestr("[Content_Types].xml", manifest.encode("utf-8"))
    buf.seek(0)
    return buf.read()


def export_docx_bytes(title: str, sections: list) -> bytes:
    """비즈니스 로직 없이 DOCX/ZIP 바이트 생성(향후 python-docx 연동).
    sections: [{section_id, title, content}] 형태의 섹션 목록."""
    import json, uuid, zipfile, io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, sec in enumerate(sections):
            # 간단한 DOCX 파트 콘텐츠 (word/document.xml)
            doc_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                  <w:body>
                    <w:p>
                      <w:r>
                        <w:t>{sec.get("title", f"Section {i+1}")}</w:t>
                      </w:r>
                    </w:p>
                  </w:body>
                </w:document>"""
            zf.writestr(f"word/document_{i+1}_{title}.xml", doc_xml.encode("utf-8"))
        # [콕셋] 핵심 관계 및 설정
        core_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <w:coreProperties xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
              <w:title>{title}</w:title>
            </w:coreProperties>"""
        zf.writestr("[Content_Types].xml", '''<?xml version="1.0" encoding="UTF-8"?>
            <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
              <Default ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document"/>
              <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document"/>
            </Types>''')
        zf.writestr("docProps/core.xml", core_xml.encode("utf-8"))
    buf.seek(0)
    return buf.read()

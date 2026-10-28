"""
REQ-032 · 정부과제 예산 자동편성 엔진(BudgetRuleEngine) & HWPX/DOCX 표준표 출력.

- 법정 규정 준수: 총 사업비 중 [현금 부담금] 10% 이상, 현금/현물 비율.
- 인건비/연구장비비/연구재료비/위탁연구비 자동 배분(비율 기반).
- 위반(현금부담 10% 미만 등) 탐지 → violations.
- 사업계획서 표준 3대 표(요약표/추진일정/연구원편성표)를 HWPX/DOCX 텍스트로 출력.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from src.common.logging_config import get_logger

logger = get_logger("budget_engine")

# 법정 현금부담금 하한(총 사업비 대비 10%)
MIN_CASH_BURDEN_RATIO = 0.10

# 기본 과업비 배분 비율(총 정부과제비 기준, 합계 1.0)
DEFAULT_ALLOCATION = {
    "personnel": 0.40,    # 인건비(보수)
    "equipment": 0.15,    # 연구장비비
    "materials": 0.20,    # 연구재료비
    "subcontract": 0.10,  # 위탁연구비
    "others": 0.15,       # 기타(간접비/출장비 등)
}


class BudgetRuleEngine:
    """정부과제 예산 자동편성 + HWPX/DOCX 표준표 출력."""

    def __init__(self, allocation: Optional[Dict[str, float]] = None,
                 in_kind_ratio: float = 0.0, cash_burden_ratio: Optional[float] = None):
        self.allocation = dict(allocation or DEFAULT_ALLOCATION)
        self.in_kind_ratio = in_kind_ratio
        self.cash_burden_ratio = MIN_CASH_BURDEN_RATIO if cash_burden_ratio is None else cash_burden_ratio

    def allocate(self, total_gov_krw: int, cash_burden_pct: Optional[float] = None,
                 in_kind_pct: Optional[float] = None) -> dict:
        """총 정부과제비로 예산을 편성. 현금부담금 10% 미만은 violation.

        - cash_burden_pct: 현금부담금 비율(기본 10% 법정 하한). None이면 인스턴스 설정값.
        - in_kind_pct: 현물비 비율(기본 0).
        - 반환 {total_budget, government_share, cash_burden, in_kind_burden,
                allocations{...}, violations[], ok}.
        """
        total = int(total_gov_krw)
        violations: List[str] = []

        cb = MIN_CASH_BURDEN_RATIO if cash_burden_pct is None else float(cash_burden_pct)
        ik = self.in_kind_ratio if in_kind_pct is None else float(in_kind_pct)

        # 현금부담금(총 사업비 대비 10% 법정 하한 검증)
        cash_burden = int(math.ceil(total * cb))
        in_kind = int(math.ceil(total * ik))
        if cb < MIN_CASH_BURDEN_RATIO:
            violations.append(
                f"현금부담금 {cb*100:.1f}% < 법정 하한 {MIN_CASH_BURDEN_RATIO*100:.0f}%"
            )

        # 정부과제비 = 총 사업비 - (현금부담금 + 현물비). 정부부담이 음수가 되지 않도록 보정.
        total_burden = cash_burden + in_kind
        if total_burden > total:
            violations.append(f"총 부담금({total_burden})이 총 사업비({total})를 초과")
            government_share = max(0, total - total_burden)
            cash_burden = 0
            in_kind = 0
        else:
            government_share = total - total_burden

        allocations = self._allocate_gov_share(government_share)

        ok = not violations
        return {
            "total_budget": total,
            "government_share": government_share,
            "cash_burden": cash_burden,
            "in_kind_burden": in_kind,
            "cash_burden_ratio": round(cash_burden / total, 4) if total else 0.0,
            "allocations": allocations,
            "violations": violations,
            "ok": ok,
        }

    def _allocate_gov_share(self, government_share: int) -> Dict[str, int]:
        """정부과제비를 기본 비율로 배분(잔여는 기타에 흡수, 합계 보존)."""
        out: Dict[str, int] = {}
        remainder = government_share
        keys = list(self.allocation.keys())
        for i, key in enumerate(keys):
            if i == len(keys) - 1:
                out[key] = max(0, remainder)
            else:
                amt = int(round(government_share * self.allocation[key]))
                out[key] = amt
                remainder -= amt
        # 합계 검증
        if sum(out.values()) != government_share and government_share > 0:
            out[keys[-1]] += government_share - sum(out.values())
        return out

    # ---------- HWPX/DOCX 표준 3대 표 ----------
    def build_summary_table(self, result: dict, project_name: str = "",
                            organization: str = "") -> str:
        """사업비 요약표(Markdown/HWPX 표)."""
        a = result.get("allocations", {})
        lines = [
            "## 사업비 요약표",
            "| 항목 | 액(원) | 비고 |",
            "|---|---:|---|",
            f"| 정부과제비 | {result['government_share']:,} | R&D 직접비 |",
            f"| 인건비(보수) | {a.get('personnel', 0):,} | 인건비 |",
            f"| 연구장비비 | {a.get('equipment', 0):,} | 장비 |",
            f"| 연구재료비 | {a.get('materials', 0):,} | 재료 |",
            f"| 위탁연구비 | {a.get('subcontract', 0):,} | 위탁 |",
            f"| 기타(간접비) | {a.get('others', 0):,} | 간접/출장 |",
            f"| 민간 현금부담금 | {result['cash_burden']:,} | 법정 {MIN_CASH_BURDEN_RATIO*100:.0f}% |",
            f"| 현물비 | {result['in_kind_burden']:,} | |",
            f"| **총 사업비** | **{result['total_budget']:,}** | |",
        ]
        return "\n".join(lines)

    def build_schedule_table(self, total_month: int = 12,
                             milestones: Optional[List[str]] = None) -> str:
        """추진일정표(Markdown)."""
        ms = milestones or ["착수", "1차 산출물", "중간 점검", "2차 산출물", "최종 보고서"]
        lines = ["## 추진일정표", "| 단계 | 목표 |", "|---|---|"]
        span = max(1, total_month // max(1, len(ms)))
        for i, name in enumerate(ms):
            m = min(total_month, (i + 1) * span)
            lines.append(f"| {i + 1} | {name}(Month {m:02d}) |")
        return "\n".join(lines)

    def build_personnel_table(self, researchers: Optional[List[dict]] = None) -> str:
        """연구원편성표(Markdown)."""
        people = researchers or [
            {"name": "대표", "role": "총괄/PM", "ratio": "100%"},
            {"name": "연구원", "role": "R&D", "ratio": "100%"},
        ]
        lines = ["## 연구원편성표", "| 성명 | 직책 | 근무비율 |", "|---|---|---|"]
        for p in people:
            lines.append(f"| {p.get('name','')} | {p.get('role','')} | {p.get('ratio','100%')} |")
        return "\n".join(lines)

    def export_document(self, result: dict, fmt: str = "DOCX",
                       project_name: str = "", organization: str = "",
                       total_month: int = 12, milestones: Optional[List[str]] = None,
                       researchers: Optional[List[dict]] = None) -> str:
        """HWPX/DOCX 표준문서(3대 표)을 텍스트로 출력. fmt=HWPX|DOCX(모두 동일 텍스트 본문)."""
        parts = [
            f"# {project_name or '정부과제 사업계획서'} (조직: {organization or '-'})",
            f"출력 포맷: {fmt.upper()}",
            self.build_summary_table(result, project_name, organization),
            self.build_schedule_table(total_month, milestones),
            self.build_personnel_table(researchers),
        ]
        if result.get("violations"):
            parts.append("## ⚠ 위반 항목\n" + "\n".join(f"- {v}" for v in result["violations"]))
        return "\n\n".join(parts)

"""
REQ-009 · 연도 필터링 (수집/정제 계층) (김도윤/정민재/한지훈 담당)

"2026 전용, 2025 이하 차단" 요구에 따른 정제 게이트다.
- 타겟연도(기본 2026) 기준: 공고가 참조하는 **최신 연도(max)** 가 타겟연도 미만이면 드롭.
  → 2025 사이클 공고(최신연도 2025)는 100% 드롭, 2026 공고(2025를 비교 언급해도)는 유지.
- 연도 미기재 공고는 `allow_no_year`(기본 False=드롭)로 통제(엄격 2026 모드).
- 정제 계층에서 **집중 게이트**로 적용하면 소스 무관한 100% 드롭을 보장한다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ..common.logging_config import get_logger
from ..common.schemas import RawNotice

logger = get_logger("year_filter")

# 서양의연도 4자(19xx/20xx) 탐지
YEAR_REGEX = re.compile(r"(?:19|20)\d{2}")


@dataclass
class YearFilter:
    target_year: int = 2026
    allow_no_year: bool = False
    strict: bool = True  # strict=True: 최신연도 < target 이면 드롭
    drop_expired: bool = False  # 마감 기한 경과 공고 자동 차단 (접수기간 내 과제만 수집)

    @classmethod
    def from_config(cls, cfg: Optional[dict]) -> "YearFilter":
        cfg = cfg or {}
        return cls(
            target_year=int(cfg.get("target_year", 2026)),
            allow_no_year=bool(cfg.get("allow_no_year", False)),
            strict=cfg.get("mode", "strict") == "strict",
            drop_expired=bool(cfg.get("drop_expired", False)),
        )

    # ------------------------------------------------------------------ core
    def detect_years(self, text: str) -> set[int]:
        return {int(y) for y in YEAR_REGEX.findall(text or "")}

    def keep(self, notice: RawNotice) -> Tuple[bool, str]:
        """(keep?, 이유). 최신연도가 타겟연도 이상이면 유지."""
        # 0) 마감 기한 경과 차단 옵션 검사
        if self.drop_expired and notice.deadline:
            from ..common.deadline import calculate_dday
            dday_res = calculate_dday(notice.deadline)
            if dday_res.get("is_expired"):
                return False, f"expired_deadline_dropped(deadline={notice.deadline})"
        haystack = f"{notice.title} {notice.body_text} {notice.deadline}"
        years = self.detect_years(haystack)

        if not years:
            if self.allow_no_year:
                return True, "no_year_allowed"
            return False, f"no_year_dropped(target={self.target_year})"

        latest = max(years)
        if latest < self.target_year:
            return False, f"older_cycle_dropped(latest={latest}<{self.target_year})"

        # 최신연도가 타겟연도를 넘어서면(미래 연도 언급 등)도 허용하지만 로그 경고
        if latest > self.target_year:
            logger.warning("미래 연도 언급(%d>%d), title=%s", latest, self.target_year, notice.title)
        return True, f"kept(latest={latest}>=target={self.target_year})"

    def apply(self, notices: List[RawNotice]) -> List[RawNotice]:
        kept: List[RawNotice] = []
        dropped: List[Tuple[RawNotice, str]] = []
        for n in notices:
            keep, reason = self.keep(n)
            if keep:
                kept.append(n)
            else:
                dropped.append((n, reason))
        self.stats = {
            "collected": len(notices),
            "kept": len(kept),
            "dropped": len(dropped),
            "target_year": self.target_year,
            "dropped_reasons": [r for _, r in dropped],
        }
        if dropped:
            logger.info(
                "연도필터: %d건 중 %d건 드롭(%s)" %
                (len(notices), len(dropped), "; ".join(sorted({r for _, r in dropped}))),
            )
        return kept

    def stats_summary(self) -> dict:
        return getattr(self, "stats", {"collected": 0, "kept": 0, "dropped": 0})

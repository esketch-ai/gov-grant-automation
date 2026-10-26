"""
REQ-019 · 마감일(Deadline) 파싱, D-Day 계산 및 긴급도 분류 유틸리티
(이승엽 / 정민재 / 최은정 담당)

한국 정부 지원사업 포털의 다양한 마감일자 포맷을 표준 datetime으로 파싱하고,
기준일(KST) 대비 D-Day 및 긴급도 상태(EXPIRED, TODAY, CRITICAL, WARNING, NORMAL, OPEN_ENDED)를 산출합니다.
"""
from __future__ import annotations

import re
from datetime import datetime, date, time
from typing import Optional, Dict, Any, List

from .logging_config import get_logger

logger = get_logger("deadline")


def parse_deadline(deadline_str: Optional[str]) -> Optional[datetime]:
    """
    공고 마감일 문자열을 정규화하여 datetime 객체로 변환.
    실패 시 None 반환 (Safe Degrade).
    
    지원 포맷:
    - 2026-12-31 18:00:00 / 2026.12.31 18:00
    - 2026-12-31 / 2026.12.31 / 2026/12/31
    - 2026년 12월 31일 18시 00분
    - 기간형: 2026-01-01 ~ 2026-05-31 18:00 (종료일 우선 추출)
    - 시간 미지정 시 기본 18:00:00 (정부 R&D 통상 마감시간)
    """
    if not deadline_str or not isinstance(deadline_str, str):
        return None

    raw = deadline_str.strip()
    if not raw:
        return None

    # '상시', '소진시' 등 비정형 텍스트 사전 검사
    if any(k in raw for k in ["상시", "소진", "마감시", "별도", "미정", "상시접수"]):
        return None

    # 기간형 (~, - 구분) 처리: 오른쪽 종료일 우선
    if "~" in raw:
        parts = raw.split("~")
        target_str = parts[-1].strip()
    else:
        target_str = raw

    # 1) ISO / 일반 구분자 포맷 + 시간 (YYYY-MM-DD HH:MM:SS or YYYY.MM.DD HH:MM)
    m_time = re.search(
        r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})\s+(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?",
        target_str,
    )
    if m_time:
        try:
            yr = int(m_time.group(1))
            mo = int(m_time.group(2))
            dy = int(m_time.group(3))
            hr = int(m_time.group(4))
            mn = int(m_time.group(5))
            sc = int(m_time.group(6)) if m_time.group(6) else 0
            return datetime(yr, mo, dy, hr, mn, sc)
        except ValueError:
            pass

    # 2) 한글 포맷 (YYYY년 MM월 DD일 HH시 MM분)
    m_kor_time = re.search(
        r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일(?:\s*(\d{1,2})시)?(?:\s*(\d{1,2})분)?",
        target_str,
    )
    if m_kor_time:
        try:
            yr = int(m_kor_time.group(1))
            mo = int(m_kor_time.group(2))
            dy = int(m_kor_time.group(3))
            hr = int(m_kor_time.group(4)) if m_kor_time.group(4) else 18
            mn = int(m_kor_time.group(5)) if m_kor_time.group(5) else 0
            return datetime(yr, mo, dy, hr, mn, 0)
        except ValueError:
            pass

    # 3) 날짜 전용 포맷 (YYYY-MM-DD or YYYY.MM.DD or YYYY/MM/DD)
    m_date = re.search(r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})", target_str)
    if m_date:
        try:
            yr = int(m_date.group(1))
            mo = int(m_date.group(2))
            dy = int(m_date.group(3))
            return datetime(yr, mo, dy, 18, 0, 0)
        except ValueError:
            pass

    return None


def calculate_dday(
    deadline_str: Optional[str],
    ref_datetime: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    공고 마감일 텍스트를 파싱하고 기준일시 대비 D-Day 메타데이터를 산출합니다.
    """
    ref_dt = ref_datetime or datetime.now()
    parsed_dt = parse_deadline(deadline_str)

    if parsed_dt is None:
        return {
            "parsed_datetime": None,
            "formatted_deadline": deadline_str or "상시/미정",
            "d_day": None,
            "status": "OPEN_ENDED",
            "badge_text": "상시/미정",
            "badge_class": "bg-purple-100 text-purple-700 border border-purple-200",
            "is_imminent": False,
            "is_expired": False,
            "days_remaining": None,
        }

    ref_date = ref_dt.date()
    target_date = parsed_dt.date()
    delta_days = (target_date - ref_date).days

    formatted_str = parsed_dt.strftime("%Y-%m-%d %H:%M")

    if delta_days < 0:
        status = "EXPIRED"
        badge_text = f"마감 (D+{abs(delta_days)})"
        badge_class = "bg-slate-200 text-slate-500 line-through"
        is_imminent = False
        is_expired = True
    elif delta_days == 0:
        status = "TODAY"
        badge_text = "D-Day (오늘마감)"
        badge_class = "bg-rose-600 text-white font-extrabold animate-pulse shadow-sm"
        is_imminent = True
        is_expired = False
    elif 1 <= delta_days <= 3:
        status = "CRITICAL"
        badge_text = f"D-{delta_days}"
        badge_class = "bg-rose-500 text-white font-bold shadow-sm"
        is_imminent = True
        is_expired = False
    elif 4 <= delta_days <= 7:
        status = "WARNING"
        badge_text = f"D-{delta_days}"
        badge_class = "bg-amber-500 text-white font-bold shadow-sm"
        is_imminent = True
        is_expired = False
    elif 8 <= delta_days <= 30:
        status = "APPROACHING"
        badge_text = f"D-{delta_days}"
        badge_class = "bg-blue-100 text-blue-800 border border-blue-200 font-semibold"
        is_imminent = False
        is_expired = False
    else:
        status = "NORMAL"
        badge_text = f"D-{delta_days}"
        badge_class = "bg-emerald-100 text-emerald-800 border border-emerald-200 font-medium"
        is_imminent = False
        is_expired = False

    return {
        "parsed_datetime": parsed_dt.isoformat(),
        "formatted_deadline": formatted_str,
        "d_day": delta_days,
        "status": status,
        "badge_text": badge_text,
        "badge_class": badge_class,
        "is_imminent": is_imminent,
        "is_expired": is_expired,
        "days_remaining": delta_days,
    }


def get_dday_statistics(
    announcements: List[Dict[str, Any]],
    ref_datetime: Optional[datetime] = None,
) -> Dict[str, Any]:
    """공고 목록에 대한 D-Day 분포 통계 집계."""
    stats = {
        "total": len(announcements),
        "today_count": 0,
        "critical_count": 0,  # D-1 ~ D-3
        "warning_count": 0,   # D-4 ~ D-7
        "approaching_count": 0,  # D-8 ~ D-30
        "normal_count": 0,    # D-31+
        "expired_count": 0,
        "open_ended_count": 0,
        "imminent_total": 0,  # D-7 이내 긴급
    }

    for ann in announcements:
        deadline_val = ann.get("deadline")
        dday_res = calculate_dday(deadline_val, ref_datetime=ref_datetime)
        st = dday_res["status"]

        if st == "TODAY":
            stats["today_count"] += 1
            stats["imminent_total"] += 1
        elif st == "CRITICAL":
            stats["critical_count"] += 1
            stats["imminent_total"] += 1
        elif st == "WARNING":
            stats["warning_count"] += 1
            stats["imminent_total"] += 1
        elif st == "APPROACHING":
            stats["approaching_count"] += 1
        elif st == "NORMAL":
            stats["normal_count"] += 1
        elif st == "EXPIRED":
            stats["expired_count"] += 1
        elif st == "OPEN_ENDED":
            stats["open_ended_count"] += 1

    return stats

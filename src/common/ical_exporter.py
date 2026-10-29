"""
REQ-019 · iCalendar (RFC 5545) 표준 .ics 생성 모듈
(정민재 / 이승엽 / 최은정 담당)

외부 서드파티 라이브러리 없이 순수 파이썬 표준 라이브러리를 사용하여,
정부 공고 마감 일정을 Google Calendar, Apple Calendar, Outlook 등에서
원클릭 등록 및 구독할 수 있는 .ics 표준 캘린더 파일을 생성합니다.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

from .deadline import parse_deadline
from .logging_config import get_logger

logger = get_logger("ical_exporter")


def escape_ical_text(text: Optional[str]) -> str:
    """RFC 5545 문자열 이스케이프 (백슬래시, 세미콜론, 쉼표, 줄바꿈)."""
    if not text:
        return ""
    s = str(text)
    s = s.replace("\\", "\\\\")
    s = s.replace(";", r"\;")
    s = s.replace(",", r"\,")
    s = s.replace("\r\n", r"\n").replace("\r", r"\n").replace("\n", r"\n")
    return s


def format_ical_dt(dt: datetime) -> str:
    """RFC 5545 일시 포맷 (YYYYMMDDTHHMMSS)."""
    return dt.strftime("%Y%m%dT%H%M%S")


def create_event_block(notice: Dict[str, Any], include_alarms: bool = True) -> Optional[str]:
    """단일 공고 레코드를 VEVENT 블록 문자열로 변환. 마감일 파싱 불가 시 None 반환."""
    deadline_str = notice.get("deadline")
    dt = parse_deadline(deadline_str)
    if dt is None:
        return None

    canonical_id = notice.get("canonical_id", "notice_unknown")
    title = notice.get("title", "제목 없음")
    ministry = notice.get("ministry") or "정부부처"
    org = notice.get("organization") or "전담기관"
    portal = notice.get("source_portal") or "포털"
    official_no = notice.get("official_notice_no") or "-"
    url = notice.get("detail_url") or ""
    now_stamp = format_ical_dt(datetime.now(timezone.utc)) + "Z"

    # 마감일 1시간 전을 시작, 마감 시각을 종료로 설정 (또는 동시각)
    dt_end = dt
    dt_start = dt - timedelta(hours=1)

    desc_lines = [
        f"공고명: {title}",
        f"공고번호: {official_no}",
        f"출처포털: {portal}",
        f"소관부처: {ministry}",
        f"전담기관: {org}",
        f"신청마감: {dt.strftime('%Y-%m-%d %H:%M')}",
    ]
    if url:
        desc_lines.append(f"원문상세: {url}")
    desc_lines.append("시스템: 모두의 창업비서 (SSA : Startup Secretary for All) 2026 정부지원사업 자동화")

    description = escape_ical_text("\n".join(desc_lines))
    summary = escape_ical_text(f"[과제마감] {title}")
    location = escape_ical_text(f"{ministry} / {org}")

    lines = [
        "BEGIN:VEVENT",
        f"UID:{canonical_id}@gov-grant-automation",
        f"DTSTAMP:{now_stamp}",
        f"DTSTART:{format_ical_dt(dt_start)}",
        f"DTEND:{format_ical_dt(dt_end)}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{description}",
        f"LOCATION:{location}",
    ]
    if url:
        lines.append(f"URL:{url}")

    if include_alarms:
        # 1일 전 알림
        lines.extend([
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            "DESCRIPTION:과제 마감 1일 전 알림",
            "TRIGGER:-P1D",
            "END:VALARM",
        ])
        # 3일 전 알림
        lines.extend([
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            "DESCRIPTION:과제 마감 3일 전 알림",
            "TRIGGER:-P3D",
            "END:VALARM",
        ])

    lines.append("END:VEVENT")
    return "\r\n".join(lines)


def export_single_notice_ics(notice: Dict[str, Any]) -> str:
    """단일 공고에 대한 독립 .ics 파일 내용 생성."""
    event_str = create_event_block(notice, include_alarms=True)
    title = notice.get("title", "과제 마감")
    cal_name = escape_ical_text(f"[마감] {title}")

    header = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SSA//Startup Secretary for All 2026//KO",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{cal_name}",
        "X-WR-TIMEZONE:Asia/Seoul",
    ]
    footer = ["END:VCALENDAR"]

    if event_str:
        return "\r\n".join(header) + "\r\n" + event_str + "\r\n" + "\r\n".join(footer) + "\r\n"
    else:
        # 마감일이 없는 경우 기본 더미 캘린더
        return "\r\n".join(header + footer) + "\r\n"


def export_bundle_calendar_ics(
    notices: List[Dict[str, Any]],
    calendar_name: str = "2026 정부지원사업 마감 캘린더",
) -> str:
    """복수 공고들에 대한 번들 iCalendar (.ics) 파일 내용 생성."""
    header = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SSA//Startup Secretary for All 2026//KO",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_ical_text(calendar_name)}",
        "X-WR-TIMEZONE:Asia/Seoul",
    ]
    footer = ["END:VCALENDAR"]

    events: List[str] = []
    for notice in notices:
        evt = create_event_block(notice, include_alarms=True)
        if evt:
            events.append(evt)

    body = "\r\n".join(events) if events else ""
    if body:
        return "\r\n".join(header) + "\r\n" + body + "\r\n" + "\r\n".join(footer) + "\r\n"
    return "\r\n".join(header + footer) + "\r\n"

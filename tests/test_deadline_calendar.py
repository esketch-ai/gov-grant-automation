"""
REQ-019 · 마감일(Deadline) D-Day 산출, 긴급도 분류, iCalendar(.ics) 내보내기 및 웹 API 테스트
"""
import sqlite3
from datetime import datetime
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.common.deadline import parse_deadline, calculate_dday, get_dday_statistics
from src.common.ical_exporter import (
    escape_ical_text,
    format_ical_dt,
    create_event_block,
    export_single_notice_ics,
    export_bundle_calendar_ics,
)
from src.web.app import app


def test_parse_deadline_various_formats():
    # 1) ISO datetime
    dt1 = parse_deadline("2026-10-30 18:00:00")
    assert dt1 == datetime(2026, 10, 30, 18, 0, 0)

    # 2) Dot datetime
    dt2 = parse_deadline("2026.11.15 17:30")
    assert dt2 == datetime(2026, 11, 15, 17, 30, 0)

    # 3) Date only (defaults to 18:00)
    dt3 = parse_deadline("2026-06-30")
    assert dt3 == datetime(2026, 6, 30, 18, 0, 0)

    # 4) Slash date
    dt4 = parse_deadline("2026/04/20")
    assert dt4 == datetime(2026, 4, 20, 18, 0, 0)

    # 5) Korean format
    dt5 = parse_deadline("2026년 08월 15일 14시 30분")
    assert dt5 == datetime(2026, 8, 15, 14, 30, 0)

    # 6) Range format (extracts end date)
    dt6 = parse_deadline("2026-01-01 ~ 2026-05-31 18:00")
    assert dt6 == datetime(2026, 5, 31, 18, 0, 0)

    # 7) Open-ended / Non-date strings
    assert parse_deadline("상시 접수") is None
    assert parse_deadline("예산 소진 시까지") is None
    assert parse_deadline("") is None
    assert parse_deadline(None) is None


def test_calculate_dday_categories():
    ref_dt = datetime(2026, 10, 25, 12, 0, 0)

    # 1) Today (D-Day)
    d_today = calculate_dday("2026-10-25 18:00:00", ref_datetime=ref_dt)
    assert d_today["status"] == "TODAY"
    assert d_today["d_day"] == 0
    assert "D-Day" in d_today["badge_text"]
    assert d_today["is_imminent"] is True
    assert d_today["is_expired"] is False

    # 2) Critical (D-1 ~ D-3)
    d_crit = calculate_dday("2026-10-27 18:00:00", ref_datetime=ref_dt)
    assert d_crit["status"] == "CRITICAL"
    assert d_crit["d_day"] == 2
    assert d_crit["badge_text"] == "D-2"
    assert d_crit["is_imminent"] is True

    # 3) Warning (D-4 ~ D-7)
    d_warn = calculate_dday("2026-10-30 18:00:00", ref_datetime=ref_dt)
    assert d_warn["status"] == "WARNING"
    assert d_warn["d_day"] == 5
    assert d_warn["badge_text"] == "D-5"
    assert d_warn["is_imminent"] is True

    # 4) Approaching (D-8 ~ D-30)
    d_appr = calculate_dday("2026-11-10 18:00:00", ref_datetime=ref_dt)
    assert d_appr["status"] == "APPROACHING"
    assert d_appr["d_day"] == 16
    assert d_appr["is_imminent"] is False

    # 5) Normal (D-31+)
    d_norm = calculate_dday("2026-12-31 18:00:00", ref_datetime=ref_dt)
    assert d_norm["status"] == "NORMAL"
    assert d_norm["d_day"] == 67

    # 6) Expired (< 0)
    d_exp = calculate_dday("2026-10-20 18:00:00", ref_datetime=ref_dt)
    assert d_exp["status"] == "EXPIRED"
    assert d_exp["d_day"] == -5
    assert "마감" in d_exp["badge_text"]
    assert d_exp["is_expired"] is True

    # 7) Open-ended / None
    d_open = calculate_dday("상시 접수", ref_datetime=ref_dt)
    assert d_open["status"] == "OPEN_ENDED"
    assert d_open["badge_text"] == "상시/미정"
    assert d_open["d_day"] is None


def test_get_dday_statistics():
    ref_dt = datetime(2026, 10, 25, 12, 0, 0)
    sample_notices = [
        {"deadline": "2026-10-25 18:00:00"},  # TODAY
        {"deadline": "2026-10-27 18:00:00"},  # CRITICAL (D-2)
        {"deadline": "2026-10-30 18:00:00"},  # WARNING (D-5)
        {"deadline": "2026-11-10 18:00:00"},  # APPROACHING (D-16)
        {"deadline": "2026-12-31 18:00:00"},  # NORMAL (D-67)
        {"deadline": "2026-10-10 18:00:00"},  # EXPIRED
        {"deadline": "상시접수"},              # OPEN_ENDED
    ]
    stats = get_dday_statistics(sample_notices, ref_datetime=ref_dt)
    assert stats["total"] == 7
    assert stats["today_count"] == 1
    assert stats["critical_count"] == 1
    assert stats["warning_count"] == 1
    assert stats["approaching_count"] == 1
    assert stats["normal_count"] == 1
    assert stats["expired_count"] == 1
    assert stats["open_ended_count"] == 1
    assert stats["imminent_total"] == 3


def test_ical_single_and_bundle_export():
    notice1 = {
        "canonical_id": "ntis:test_notice_01",
        "title": "2026년 차세대 모빌리티 R&D 사업",
        "official_notice_no": "MOTIE-2026-001",
        "ministry": "산업통상자원부",
        "organization": "KEIT",
        "source_portal": "ntis",
        "deadline": "2026-11-30 18:00:00",
        "detail_url": "https://example.com/notice/01",
    }
    notice2 = {
        "canonical_id": "g2b:test_notice_02",
        "title": "2026년 탄소중립 DX 플랫폼 구축 조달",
        "official_notice_no": "G2B-2026-999",
        "ministry": "환경부",
        "organization": "조달청",
        "source_portal": "g2b",
        "deadline": "2026-12-15 18:00:00",
        "detail_url": "https://example.com/notice/02",
    }

    # 1) 단일 공고 .ics
    single_ics = export_single_notice_ics(notice1)
    assert "BEGIN:VCALENDAR" in single_ics
    assert "VERSION:2.0" in single_ics
    assert "BEGIN:VEVENT" in single_ics
    assert "UID:ntis:test_notice_01@gov-grant-automation" in single_ics
    assert "SUMMARY:[과제마감] 2026년 차세대 모빌리티 R&D 사업" in single_ics
    assert "LOCATION:산업통상자원부 / KEIT" in single_ics
    assert "BEGIN:VALARM" in single_ics
    assert "TRIGGER:-P1D" in single_ics
    assert "TRIGGER:-P3D" in single_ics
    assert "END:VEVENT" in single_ics
    assert "END:VCALENDAR" in single_ics

    # 2) 번들 캘린더 .ics
    bundle_ics = export_bundle_calendar_ics([notice1, notice2], calendar_name="2026 테스트 캘린더")
    assert "BEGIN:VCALENDAR" in bundle_ics
    assert "X-WR-CALNAME:2026 테스트 캘린더" in bundle_ics
    assert bundle_ics.count("BEGIN:VEVENT") == 2
    assert bundle_ics.count("END:VEVENT") == 2
    assert "END:VCALENDAR" in bundle_ics


def test_web_calendar_and_dday_endpoints():
    client = TestClient(app)

    # 1) 2026 전체 캘린더 피드 (.ics)
    res_cal = client.get("/api/calendar/2026.ics")
    assert res_cal.status_code == 200
    assert "text/calendar" in res_cal.headers["content-type"]
    assert "attachment; filename=\"gov_grants_2026.ics\"" in res_cal.headers["content-disposition"]
    assert "BEGIN:VCALENDAR" in res_cal.text
    assert "END:VCALENDAR" in res_cal.text

    # 2) D-Day 요약 API
    res_dday = client.get("/api/announcements/dday-summary")
    assert res_dday.status_code == 200
    data = res_dday.json()
    assert data["status"] == "success"
    assert "dday_stats" in data
    assert "total" in data["dday_stats"]
    assert "imminent_total" in data["dday_stats"]

    # 3) 개별 공고 캘린더 다운로드
    # 기존 DB에 존재하는 'ntis:test_sim_detail'
    res_single = client.get("/api/announcements/ntis:test_sim_detail/calendar.ics")
    assert res_single.status_code == 200
    assert "text/calendar" in res_single.headers["content-type"]
    assert "BEGIN:VCALENDAR" in res_single.text
    assert "UID:ntis:test_sim_detail@gov-grant-automation" in res_single.text

    # 4) 존재하지 않는 공고 404
    res_404 = client.get("/api/announcements/invalid:none_existing/calendar.ics")
    assert res_404.status_code == 404

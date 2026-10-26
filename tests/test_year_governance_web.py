"""Tests for 2026 Year Governance and Web Admin Management (REQ-016).
"""
import pytest
from fastapi.testclient import TestClient

from src.common.db import GrantDatabase
from src.common.schemas import RawNotice
from src.web.app import app


@pytest.fixture
def populated_db(tmp_path, monkeypatch):
    test_db_path = tmp_path / "grant_test.db"
    db = GrantDatabase(test_db_path)
    db.ensure_schema()

    # Insert 2026 announcements
    n2026_a = RawNotice("ntis", "2026년 첨단 로봇 R&D 과제", "NTIS", "과기정통부", "2026-11-30 18:00", "https://ntis.go.kr/1")
    db.upsert_announcement(n2026_a, canonical_id="ntis:2026:robot", target_year=2026)

    n2026_b = RawNotice("k_startup", "2026년 인공지능 창업 바우처", "K-Startup", "중소벤처기업부", "2026-12-15 18:00", "https://k-startup.go.kr/2")
    db.upsert_announcement(n2026_b, canonical_id="k_startup:2026:ai", target_year=2026)

    # Insert past 2025 announcement (isolated/mocked)
    n2025 = RawNotice("iris", "2025년 바이오 헬스케어 과제", "IRIS", "보건복지부", "2025-12-31", "https://iris.go.kr/3")
    db.upsert_announcement(n2025, canonical_id="iris:2025:bio", target_year=2025)

    # Insert future 2027 announcement
    n2027 = RawNotice("nipa", "2027년 양자컴퓨팅 파일럿", "NIPA", "과기정통부", "2027-02-28", "https://nipa.kr/4")
    db.upsert_announcement(n2027, canonical_id="nipa:2027:quantum", target_year=2027)

    monkeypatch.setattr("src.web.app._get_db", lambda: db)
    return db


def test_announcements_view_default_2026_filter(populated_db):
    client = TestClient(app)
    # Default is year=2026
    resp = client.get("/announcements")
    assert resp.status_code == 200
    assert "2026년 첨단 로봇" in resp.text
    assert "2026년 인공지능 창업 바우처" in resp.text
    # 2025 past should NOT be in the default 2026 view
    assert "2025년 바이오 헬스케어 과제" not in resp.text
    assert "2027년 양자컴퓨팅 파일럿" not in resp.text


def test_announcements_view_all_years_filter(populated_db):
    client = TestClient(app)
    resp = client.get("/announcements?year=all")
    assert resp.status_code == 200
    assert "2026년 첨단 로봇" in resp.text
    assert "2025년 바이오 헬스케어 과제" in resp.text
    assert "2027년 양자컴퓨팅 파일럿" in resp.text


def test_announcements_view_past_filter(populated_db):
    client = TestClient(app)
    resp = client.get("/announcements?year=past")
    assert resp.status_code == 200
    assert "2025년 바이오 헬스케어 과제" in resp.text
    assert "2026년 첨단 로봇 R&D 과제" not in resp.text


def test_api_stats_years_endpoint(populated_db):
    client = TestClient(app)
    resp = client.get("/api/stats/years")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    stats = data["stats"]
    assert stats["total_announcements"] == 4
    assert stats["year_2026_count"] == 2
    assert stats["past_years_count"] == 1
    assert stats["future_years_count"] == 1
    assert stats["compliance_rate_pct"] == 50.0  # 2 out of 4


def test_dashboard_contains_year_governance_kpi(populated_db):
    client = TestClient(app)
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "2026 연도 거버넌스" in resp.text
    assert "준수율" in resp.text

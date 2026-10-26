"""Tests for Announcement Detail API and Match Simulation API in Web Admin.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.common.db import GrantDatabase
from src.common.schemas import RawNotice
from src.web.app import app, PROJECT_ROOT


@pytest.fixture
def client():
    return TestClient(app)


def _seed_announcement(db: GrantDatabase, canonical_id: str, title: str, rfp_content: str = ""):
    notice = RawNotice(
        portal_id="ntis",
        title=title,
        organization="정보통신기획평가원",
        ministry="과학기술정보통신부",
        deadline="2026-11-25 18:00",
        detail_url="https://www.ntis.go.kr/rndgate/eg/un/ra/view.do?roRndUid=1279968",
        body_text=title,
    )
    db.upsert_announcement(notice, canonical_id=canonical_id)
    if rfp_content:
        db.upsert_rfp_chunk(
            rfp_chunk={"rfp_number": "RFP-SIM-01", "rfp_title": title, "content": rfp_content},
            canonical_id=canonical_id,
            rfp_id=f"{canonical_id}#0",
        )


def test_get_announcement_detail_success(client):
    db = GrantDatabase(PROJECT_ROOT / "storage" / "grant_master.db")
    db.ensure_schema()
    c_id = "ntis:test_sim_detail"
    _seed_announcement(db, c_id, "2026년 디지털 트윈 실증 R&D", "디지털 트윈 세부과제")

    res = client.get(f"/api/announcements/{c_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["announcement"]["canonical_id"] == c_id
    assert len(data["rfp_chunks"]) >= 1
    assert "available_items" in data


def test_get_announcement_detail_not_found(client):
    res = client.get("/api/announcements/non_existent_portal:999999")
    assert res.status_code == 404


def test_simulate_match_disqualified_by_prefilter(client):
    db = GrantDatabase(PROJECT_ROOT / "storage" / "grant_master.db")
    db.ensure_schema()
    c_id = "ntis:test_sim_disqualified"
    # Non-matching domain announcement for item_01_carbon_dmrv
    _seed_announcement(db, c_id, "2026년 전통 옹기 및 한과 제조 지원사업", "식품 및 옹기")

    payload = {
        "item_id": "item_01_carbon_dmrv",
        "canonical_id": c_id,
    }
    res = client.post("/api/matcher/simulate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"

    ev = data["evaluation"]
    assert ev["is_eligible"] is False
    assert ev["match_score"] == 0
    assert "사전필터 탈락" in ev["note"] or "핵심 기술 키워드 일치 0건" in ev["note"]


def test_simulate_match_qualified(client):
    db = GrantDatabase(PROJECT_ROOT / "storage" / "grant_master.db")
    db.ensure_schema()
    c_id = "ntis:test_sim_qualified"
    # Highly matching announcement for item_01_carbon_dmrv
    _seed_announcement(
        db,
        c_id,
        "2026년 탄소배출권 디지털 MRV 및 에너지 AX 실증과제",
        "스마트빌딩 및 에너지 탄소배출권 자산 라우팅 기술개발",
    )

    payload = {
        "item_id": "item_01_carbon_dmrv",
        "canonical_id": c_id,
    }
    res = client.post("/api/matcher/simulate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"

    ev = data["evaluation"]
    # Should pass RulePreFilter (checked condition checks)
    assert any(c["status"] == "PASS" for c in ev["condition_checks"])


def test_simulate_match_missing_params(client):
    res = client.post("/api/matcher/simulate", json={})
    assert res.status_code == 400

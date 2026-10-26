"""Tests for dynamic Business Item CRUD and security controls in Web Admin.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.web.app import app, PROJECT_ROOT


@pytest.fixture
def client():
    return TestClient(app)


def test_create_item_success(client):
    test_id = "test_item_qa_automation"
    target_dir = PROJECT_ROOT / "items" / test_id

    # Clean up before test if exists
    if target_dir.exists():
        import shutil
        shutil.rmtree(target_dir)

    payload = {
        "item_id": test_id,
        "name": "QA 자동화 R&D 솔루션",
        "min_score": 80,
        "target_trl": "7",
        "keywords": "QA, 테스팅, 검수, 자동화",
        "recipients": "qa@test.com",
        "proposal_text": "# QA R&D 과제 제안서\n\n자동화 검수 스웜 플랫폼 개발",
    }

    res = client.post("/api/items", json=payload)
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    assert target_dir.exists()
    assert (target_dir / "profile.yaml").exists()
    assert (target_dir / "proposal.md").exists()

    prop_content = (target_dir / "proposal.md").read_text(encoding="utf-8")
    assert "자동화 검수 스웜" in prop_content

    # Clean up
    import shutil
    shutil.rmtree(target_dir)


def test_create_item_invalid_id_path_traversal(client):
    malicious_ids = [
        "../evil_path",
        "sub/folder",
        "item with spaces",
        "item!@#$%",
        "",
    ]
    for bad_id in malicious_ids:
        payload = {
            "item_id": bad_id,
            "name": "공격 시도",
        }
        res = client.post("/api/items", json=payload)
        assert res.status_code == 400
        assert "유효하지 않은 item_id" in res.json().get("message", "")


def test_create_item_duplicate_conflict(client):
    # item_01_carbon_dmrv already exists
    payload = {
        "item_id": "item_01_carbon_dmrv",
        "name": "중복 아이템",
    }
    res = client.post("/api/items", json=payload)
    assert res.status_code == 409


def test_update_item_success(client):
    test_id = "test_item_to_update"
    target_dir = PROJECT_ROOT / "items" / test_id
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "profile.yaml").write_text("item_meta:\n  item_id: test_item_to_update\n  item_name: 이전명칭\n", encoding="utf-8")
    (target_dir / "proposal.md").write_text("이전 제안서 내용", encoding="utf-8")

    try:
        update_payload = {
            "name": "갱신된 명칭",
            "min_score": 88,
            "target_trl": "8",
            "keywords": ["수정키워드1", "수정키워드2"],
            "recipients": ["updated@company.com"],
            "proposal_text": "새로운 제안서 본문 내용",
        }
        res = client.put(f"/api/items/{test_id}", json=update_payload)
        assert res.status_code == 200
        assert res.json()["status"] == "success"

        p_text = (target_dir / "profile.yaml").read_text(encoding="utf-8")
        assert "갱신된 명칭" in p_text
        assert "88" in p_text
        assert (target_dir / "proposal.md").read_text(encoding="utf-8") == "새로운 제안서 본문 내용"
    finally:
        import shutil
        shutil.rmtree(target_dir)


def test_update_item_not_found(client):
    res = client.put("/api/items/non_existent_item_9999", json={"name": "test"})
    assert res.status_code == 404


def test_delete_item_success(client):
    test_id = "test_item_to_delete"
    target_dir = PROJECT_ROOT / "items" / test_id
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "profile.yaml").write_text("data", encoding="utf-8")

    res = client.delete(f"/api/items/{test_id}")
    assert res.status_code == 200
    assert not target_dir.exists()


def test_delete_item_path_traversal(client):
    res = client.delete("/api/items/..%2Fevil")
    assert res.status_code in (400, 404)

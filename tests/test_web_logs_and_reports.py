"""Tests for Web Admin System Logs Viewer and Audit Report Downloads (REQ-017).
"""
import pytest
from fastapi.testclient import TestClient

from src.web.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_logs_view_html(client):
    resp = client.get("/logs")
    assert resp.status_code == 200
    assert "실시간 시스템 실행 로그" in resp.text
    assert "logTerminal" in resp.text


def test_api_logs_json(client):
    resp = client.get("/api/logs?lines=50")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "lines" in data
    assert isinstance(data["lines"], list)
    assert data["count"] == len(data["lines"])


def test_audit_download_markdown(client):
    resp = client.get("/api/audit/download/md")
    assert resp.status_code == 200
    assert "text/markdown" in resp.headers.get("content-type", "")
    assert "다각도 테스트 검수 에이전트(QA Swarm) 종합 감사 보고서" in resp.text


def test_audit_download_json(client):
    resp = client.get("/api/audit/download/json")
    assert resp.status_code == 200
    assert "application/json" in resp.headers.get("content-type", "")
    data = resp.json()
    assert "total_score" in data
    assert "results" in data


def test_audit_download_invalid_format(client):
    resp = client.get("/api/audit/download/invalid_fmt")
    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "error"
    assert "지원하지 않는 포맷" in data["message"]

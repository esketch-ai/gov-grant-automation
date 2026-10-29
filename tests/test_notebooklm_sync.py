"""
tests/test_notebooklm_sync.py
Google NotebookLM 기반 국내외 지원사업 지속 수집 및 포털 동기화 엔진 종합 테스트.
(cab8404e-d364-463e-a5a7-edfd8b3042ab 연동)
"""
import json
import pytest
from fastapi.testclient import TestClient

from src.web.app import app
from src.collector.notebooklm_sync import NotebookLMSyncService
from src.common.db import GrantDatabase
from src.common.global_grant_directory import GlobalGrantsService
from src.common.master_grant_directory import MasterGrantService


@pytest.fixture
def client():
    return TestClient(app)


def test_notebooklm_sync_service_config():
    """NotebookLM 동기화 서비스의 기본 설정 및 노트북 ID/URL 검증."""
    service = NotebookLMSyncService()
    assert service.notebook_id == "cab8404e-d364-463e-a5a7-edfd8b3042ab"
    assert "notebook.google.com/notebook/cab8404e-d364-463e-a5a7-edfd8b3042ab" in service.notebook_url


def test_parse_raw_content_json_list():
    """JSON 리스트 형태의 과제 데이터 파싱 및 정규화 검증."""
    service = NotebookLMSyncService()
    raw = [
        {
            "program_id": "TEST-NL-001",
            "country": "싱가포르",
            "city_hub": "싱가포르",
            "program_name": "싱가포르 AI 혁신 펀드",
            "financial_benefit": "최대 100,000 SGD",
            "visa_benefit": "EntrePass 연계",
            "specialized_fields": ["AI", "딥테크"],
        }
    ]
    parsed = service.parse_raw_content(raw)
    assert len(parsed) == 1
    p = parsed[0]
    assert p["program_id"] == "TEST-NL-001"
    assert p["country"] == "싱가포르"
    assert p["country_code"] == "SG"
    assert p["financial_benefit"] == "최대 100,000 SGD"
    assert "AI" in p["specialized_fields"]


def test_parse_raw_content_markdown_code_fence():
    """마크다운 코드블록(```json ... ```) 형태 파싱 검증."""
    service = NotebookLMSyncService()
    raw_str = """
```json
[
  {
    "country": "독일",
    "program_name": "베를린 딥테크 인큐베이터",
    "financial_benefit": "50,000 EUR",
    "visa_benefit": "스타트업 비자 지원"
  }
]
```
"""
    parsed = service.parse_raw_content(raw_str)
    assert len(parsed) == 1
    assert parsed[0]["country"] == "독일"
    assert parsed[0]["country_code"] == "DE"
    assert "50,000 EUR" in parsed[0]["financial_benefit"]


def test_parse_raw_content_markdown_table():
    """Markdown 표 형태의 과제 데이터 자동 파싱 검증."""
    service = NotebookLMSyncService()
    md_table = """
| 국가 | 과제명 | 주관기관 | 특화분야 | 지원혜택 | 비자특혜 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 스위스 | 취리히 테크 허브 챌린지 | 스위스 혁신청 | 핀테크, AI | 시제품 30,000 CHF 지원 | 상용비자 스폰서십 |
"""
    parsed = service.parse_raw_content(md_table)
    assert len(parsed) == 1
    p = parsed[0]
    assert p["country"] == "스위스"
    assert "취리히" in p["program_name"]
    assert "스위스 혁신청" in p["supervising_entity"]
    assert "30,000 CHF" in p["financial_benefit"]


def test_reconciliation_add_and_update(tmp_path):
    """차분 분석(Reconciliation): 신규 추가(ADD) 후 필드 수정 시 갱신(UPDATE) 검증."""
    test_db_path = tmp_path / "test_grant_master.db"
    db = GrantDatabase(test_db_path)
    db.ensure_schema()
    service = NotebookLMSyncService(db=db)

    # 1. 초기 신규 등록 (ADD)
    item_v1 = {
        "program_id": "RECON-TEST-001",
        "country": "호주",
        "program_name": "퍼스 클린테크 엑셀러레이터",
        "financial_benefit": "초기 지원금 30,000 AUD",
        "visa_benefit": "단기 비자 지원",
        "specialized_fields": ["클린테크", "신재생에너지"],
    }
    res1 = service.reconcile_and_persist([item_v1])
    assert res1["added_count"] == 1
    assert res1["updated_count"] == 0
    assert res1["programs"][0]["_action"] == "ADDED"

    # 2. 내용 수정 후 재동기화 (UPDATE)
    item_v2 = {
        "program_id": "RECON-TEST-001",
        "country": "호주",
        "program_name": "퍼스 클린테크 엑셀러레이터 (확대 개정)",
        "financial_benefit": "확대 지원금 50,000 AUD + 바우처",
        "visa_benefit": "글로벌 탤런트 비자(GTI) 연계",
        "specialized_fields": ["클린테크", "신재생에너지", "CCUS"],
    }
    res2 = service.reconcile_and_persist([item_v2])
    assert res2["added_count"] == 0
    assert res2["updated_count"] == 1
    assert res2["programs"][0]["_action"] == "UPDATED"

    # 3. DB 영속성 및 버전 확인
    with db._connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT program_name, financial_benefit, version FROM dynamic_global_grants WHERE program_id = 'RECON-TEST-001'")
        row = cur.fetchone()
        assert row is not None
        assert "확대 개정" in row[0]
        assert "50,000 AUD" in row[1]
        assert row[2] >= 2

        # 동기화 감사 로그 2건 확인
        cur.execute("SELECT count(*) FROM notebook_sync_logs")
        log_count = cur.fetchone()[0]
        assert log_count == 2


def test_api_notebooklm_status(client):
    """GET /api/portals/notebooklm/status API 검증."""
    resp = client.get("/api/portals/notebooklm/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    sync_status = data["sync_status"]
    assert sync_status["notebook_id"] == "cab8404e-d364-463e-a5a7-edfd8b3042ab"
    assert "notebook_url" in sync_status
    assert "sync_interval_seconds" in sync_status
    assert sync_status["is_enabled"] is True


def test_api_notebooklm_import_success(client):
    """POST /api/portals/notebooklm/import API를 통한 직접 과제 동기화 검증."""
    payload = {
        "notebook_id": "cab8404e-d364-463e-a5a7-edfd8b3042ab",
        "raw_content": [
            {
                "program_id": "API-TEST-SG-2026",
                "country": "싱가포르",
                "city_hub": "싱가포르",
                "program_name": "싱가포르 EnterpriseSG 테스트 과제",
                "financial_benefit": "50,000 SGD",
                "visa_benefit": "EntrePass 지원",
                "specialized_fields": ["AI", "핀테크"],
            }
        ]
    }
    resp = client.post("/api/portals/notebooklm/import", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "동기화 완료" in data["message"]
    result = data["result"]
    assert result["total_count"] >= 1
    assert result["sync_hash"] is not None


def test_api_notebooklm_import_validation_error(client):
    """POST /api/portals/notebooklm/import 유효하지 않은 데이터 전송 시 에러 핸들링 검증."""
    # 1. 빈 데이터
    resp1 = client.post("/api/portals/notebooklm/import", json={})
    assert resp1.status_code == 400

    # 2. 파싱 불가 데이터
    resp2 = client.post("/api/portals/notebooklm/import", json={"raw_content": "단순한 텍스트 줄글입니다"})
    assert resp2.status_code in (400, 422)


def test_api_notebooklm_history(client):
    """GET /api/portals/notebooklm/history API 검증."""
    resp = client.get("/api/portals/notebooklm/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "history" in data
    assert isinstance(data["history"], list)


def test_portals_view_renders_notebooklm_sync_panel(client):
    """GET /portals 화면에 Google NotebookLM 지속 연동 배너와 모달이 정상 렌더링되는지 검증."""
    resp = client.get("/portals")
    assert resp.status_code == 200
    html = resp.text

    # NotebookLM 연동 배너 검증
    assert "Google NotebookLM" in html
    assert "cab8404e-d364-463e-a5a7-edfd8b3042ab" in html
    assert "지속 추가(Add)" in html or "자동 추가" in html
    assert "수정 업데이트(Update)" in html or "수정 갱신" in html

    # 모달 검증
    assert "notebooklmImportModal" in html
    assert "notebooklmRawInput" in html
    assert "submitNotebookLMImport" in html

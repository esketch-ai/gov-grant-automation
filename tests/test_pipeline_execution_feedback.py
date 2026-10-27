"""
파이프라인 수동 실행 가시성 및 DB 공고 매칭 풀 통합 검증 테스트
(tests/test_pipeline_execution_feedback.py)

- 안드레이 카파시 4원칙 (Goal-Driven Execution) 준수
- 외부 수집 0건 상황에서도 DB 2026 공고 풀에 대한 자동 매칭 보장 검증
- POST /api/pipeline/run 응답의 상세 가시성(통계 및 아이템별 매칭 세부 내역) 검증
"""
import pytest
from starlette.testclient import TestClient
from src.web.app import app, PROJECT_ROOT, _get_db


@pytest.fixture
def client():
    return TestClient(app)


def test_pipeline_api_returns_detailed_feedback(client):
    """POST /api/pipeline/run 호출 시 상세 요약 필드(total_items, total_evaluated, detail_items 등) 반환 검증."""
    res = client.post("/api/pipeline/run")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "success"
    assert "total_items" in data
    assert "total_evaluated" in data
    assert "total_matched" in data
    assert "detail_items" in data
    assert "message" in data

    # 아이템이 존재할 경우 평가 공고 수가 0보다 커야 함 (DB 2026 공고 풀 병합)
    if data["total_items"] > 0:
        assert data["total_evaluated"] > 0, "DB에 2026 공고가 있다면 평가 공고 풀이 0보다 커야 합니다."
        assert isinstance(data["detail_items"], list)
        for it in data["detail_items"]:
            assert "item_id" in it
            assert "evaluated" in it
            assert "matched" in it
            assert "matches" in it

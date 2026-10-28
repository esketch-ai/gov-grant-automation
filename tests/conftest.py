"""공용 pytest fixture — 로컬/오프라인 통과 원칙(한지훈 QA 통제)."""
from __future__ import annotations

import pytest

from fastapi.testclient import TestClient

from src.web.app import app as _fastapi_app


@pytest.fixture
def app():
    """FastAPI 앱 인스턴스 제공."""
    return _fastapi_app


@pytest.fixture
def client():
    """TestClient 인스턴스 제공."""
    return TestClient(_fastapi_app)
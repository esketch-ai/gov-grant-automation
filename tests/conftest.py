"""공용 pytest fixture — 로컬/오프라인 통과 원칙(한지훈 QA 통제)."""
from __future__ import annotations

import pytest

from _fakes import sample_notice


@pytest.fixture
def sample_notice_fixture():
    return sample_notice()

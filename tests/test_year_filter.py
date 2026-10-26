"""REQ-009 · 2026 전용 연도 필터 단위 테스트 (100% 2025 드롭 보장)."""
from __future__ import annotations

from src.collector.multi_collector import RawNotice  # 재Export 확인용
from src.collector.year_filter import YearFilter
from src.common.schemas import RawNotice as RN


def _n(title="제목", body="", deadline="상세", portal="ntis"):
    return RN(portal, title, "org", "과기부", deadline, "url", body)


def test_drop_2025_only():
    f = YearFilter(target_year=2026)
    n = _n(title="2025년 정부지원사업 공고", body="2025 회차")
    keep, why = f.keep(n)
    assert keep is False
    assert "older_cycle_dropped" in why


def test_keep_2026():
    f = YearFilter(target_year=2026)
    n = _n(title="2026년 신규과제", body="")
    keep, why = f.keep(n)
    assert keep is True
    assert "kept" in why


def test_keep_2026_that_mentions_2025():
    # 2026 공고가 2025년을 비교 언급해도 최신연도=2026이므로 유지
    f = YearFilter(target_year=2026)
    n = _n(title="2026년 (2025년 대비) 신규", body="")
    keep, why = f.keep(n)
    assert keep is True
    assert "latest=2026" in why


def test_no_year_dropped_by_default():
    f = YearFilter(target_year=2026, allow_no_year=False)
    assert f.keep(_n(title="연도 없는 공고", body="")).__class__ is tuple
    keep, _ = f.keep(_n(title="연도 없는 공고", body="x"))
    assert keep is False


def test_no_year_kept_when_allowed():
    f = YearFilter(target_year=2026, allow_no_year=True)
    keep, _ = f.keep(_n(title="연도 없는 공고", body="y"))
    assert keep is True


def test_batch_100_percent_drop_of_2025():
    f = YearFilter(target_year=2026, allow_no_year=False)
    notices = [_n(title=f"2025 제{i}차 공고") for i in range(5)]
    kept = f.apply(notices)
    assert kept == []
    assert f.stats_summary()["dropped"] == 5
    assert f.stats_summary()["collected"] == 5


def test_mixed_batch_keeps_only_2026():
    f = YearFilter(target_year=2026, allow_no_year=False)
    batch = [
        _n(title="2026 과제 A"),
        _n(title="2025 과제 B"),
        _n(title="2026 과제 C, 2025대비"),
        _n(title="2024 과제 D"),
    ]
    kept = f.apply(batch)
    assert len(kept) == 2  # A, C 만
    assert all("2026" in n.title for n in kept)


def test_from_config():
    f = YearFilter.from_config({"target_year": 2026, "allow_no_year": False, "mode": "strict", "drop_expired": True})
    assert f.target_year == 2026
    assert f.allow_no_year is False
    assert f.strict is True
    assert f.drop_expired is True


def test_drop_expired_deadlines():
    f = YearFilter(target_year=2026, drop_expired=True)
    # Expired notice (e.g. 2026-01-01 when today is late 2026)
    n_exp = _n(title="2026년 상반기 종료 과제", deadline="2026-01-01 18:00")
    keep_exp, why_exp = f.keep(n_exp)
    assert keep_exp is False
    assert "expired_deadline_dropped" in why_exp

    # Active notice (e.g. 2026-12-31)
    n_act = _n(title="2026년 하반기 신규 과제", deadline="2026-12-31 18:00")
    keep_act, why_act = f.keep(n_act)
    assert keep_act is True

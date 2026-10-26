"""REQ-003 + REQ-009 통합 테스트: 연도 게이트 + DB 영속화 + 중복발송 방지 E2E."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

import src.main as mainmod
from src.common.schemas import RawNotice, GrantEvaluationResult
from src.common.logging_config import setup_logging


def _build_root(root: Path, year_cfg_mode="strict"):
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "items" / "it_x").mkdir(parents=True, exist_ok=True)
    (root / "storage").mkdir(exist_ok=True)
    (root / "config" / "master_portals.yaml").write_text("portals: {}", encoding="utf-8")
    (root / "config" / "mail_config.yaml").write_text(
        "smtp:\n  host: x\n  port: 587\n  username: b@x\n  password: p\n"
        "  max_attachment_size_mb: 20\n",
        encoding="utf-8",
    )
    (root / "config" / "year_filter.yaml").write_text(
        f"year_filter:\n  target_year: 2026\n  allow_no_year: false\n  mode: {year_cfg_mode}\n",
        encoding="utf-8",
    )
    (root / "items" / "it_x" / "profile.yaml").write_text(
        "item_meta:\n  item_id: it_x\n  item_name: X\n  recipients: [a@x.com]\n"
        "domain_routing:\n  min_match_score: 75\n",
        encoding="utf-8",
    )
    (root / "items" / "it_x" / "proposal.md").write_text("제안서\n", encoding="utf-8")


class StubCollector:
    def __init__(self, *a, **k):
        self.notices = [
            RawNotice("ntis", "2026년 과제 A", "NTIS", "과기부", "2026-06-30",
                      "https://x/1", body_text="본문 A"),
            RawNotice("ntis", "2025년 과제 B", "NTIS", "과기부", "2025-06-30",
                      "https://x/2", body_text="2025 회차"),
            RawNotice("ntis", "연도 없는 C", "NTIS", "과기부", "상세", "https://x/3", body_text="c"),
        ]

    async def collect_for_item(self, profile, portals):
        return list(self.notices)


class StubMatcher:
    def __init__(self, *a, **k):
        pass

    def evaluate_notice(self, prof, md, title, chunk):
        return GrantEvaluationResult(
            is_eligible=True, match_score=90,
            target_rfp_info=chunk.get("rfp_number", "단일공고"),
            support_scale_and_period="3억/6개월",
            condition_checks=[], owner_inquiries=[],
            proposal_alignment_strategy="전략", note="",
        )


class CaptureNotifier:
    sent = []

    def __init__(self, *a, **k):
        pass

    def send_item_digest(self, profile, matched):
        CaptureNotifier.sent.append(list(matched))


def test_pipeline_year_gate_and_dedup_and_db(tmp_path, monkeypatch):
    setup_logging()
    CaptureNotifier.sent = []
    _build_root(tmp_path)

    monkeypatch.setattr(mainmod, "MultiPortalCollector", StubCollector)
    monkeypatch.setattr(mainmod, "EligibilityMatcher", StubMatcher)
    monkeypatch.setattr(mainmod, "GrantEmailNotifier", CaptureNotifier)

    # ---- 1회차: 2025·년도비 2건은 드롭, 2026 A만 발송+기록
    asyncio.run(mainmod.run_daily_pipeline(tmp_path, llm_client=None))

    sent1 = [list(s) for s in CaptureNotifier.sent]
    assert len(sent1) == 1                     # 한 item에 발송 1바치
    sent_titles = [n.title for (n, r) in sent1[0]]
    assert "2026년 과제 A" in sent_titles        # 2026 유지
    assert "2025년 과제 B" not in sent_titles    # 2025 드롭
    assert "연도 없는 C" not in sent_titles       # 연도비 드롭

    # DB에 1건 기록됨
    db = mainmod.GrantDatabase(tmp_path / "storage" / "grant_master.db")
    assert db.count_dispatched("it_x") == 1

    # 수집된 공고가 DB에 영속화되었는지
    import sqlite3
    conn = sqlite3.connect(str(tmp_path / "storage" / "grant_master.db"))
    anns = conn.execute("SELECT title FROM announcements").fetchall()
    conn.close()
    titles = [r[0] for r in anns]
    assert "2026년 과제 A" in titles
    assert "2025년 과제 B" not in titles         # 연도게이트가 정제로 먼저 드롭 -> 영속화 안 됨
    assert "연도 없는 C" not in titles

    # ---- 2회차: 중복발송 방지 -> 0건 발송
    CaptureNotifier.sent = []
    asyncio.run(mainmod.run_daily_pipeline(tmp_path, llm_client=None))
    assert CaptureNotifier.sent == []           # 이미 발송했으므로 0건
    assert db.count_dispatched("it_x") == 1      # 기록은 그대로 1건(중복 insert 되지 않음)

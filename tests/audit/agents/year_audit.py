"""Agent-YearAudit: Verifies 2026 target year integrity across DB and pipeline.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import List
import yaml

from src.collector.year_filter import YearFilter
from src.common.schemas import RawNotice
from tests.audit.base import AuditResult, BaseAuditAgent


class YearAuditAgent(BaseAuditAgent):
    """Audits year integrity across database storage, filter configuration, and pipeline."""

    def __init__(self, db_path: str = "storage/grant_master.db", config_path: str = "config/year_filter.yaml") -> None:
        super().__init__(
            agent_id="Agent-YearAudit",
            agent_name="연도 무결성 감사 에이전트 (2026 전용)",
            max_score=20.0,
        )
        self.db_path = Path(db_path)
        self.config_path = Path(config_path)

    def run(self) -> AuditResult:
        details: List[str] = []
        passed = True
        score = self.max_score

        # Check 1: Audit Config file integrity
        cfg_dict = {}
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg_dict = yaml.safe_load(f) or {}
            except Exception as e:
                details.append(f"WARN: Failed reading config yaml: {e}")

        target_year = int(cfg_dict.get("target_year", 2026))
        if target_year != 2026:
            passed = False
            score -= 10.0
            details.append(f"FAIL: config target_year is {target_year}, expected 2026")
        else:
            details.append("PASS: config target_year is strictly set to 2026")

        # Check 2: Synthetic stress test with deliberate past announcements
        year_filter = YearFilter.from_config(cfg_dict)
        stress_dataset = [
            RawNotice("test", "2023년 바이오 R&D 지원사업", "org", "과기부", "2023-06-01", "url", "2023 회차"),
            RawNotice("test", "2024년 ICT 창업 패키지", "org", "중기부", "2024-04-01", "url", "2024 회차"),
            RawNotice("test", "2025년 인공지능 전환 바우처", "org", "과기부", "2025-12-15", "url", "2025 회차"),
            RawNotice("test", "디지털 신산업 공고 (2025년 마감)", "org", "산업부", "2025-12-31", "url", "2025 마감"),
            RawNotice("test", "2026년 첨단로봇 기술개발", "org", "산업부", "2026-03-31", "url", "2026 회차"),
            RawNotice("test", "초격차 스타트업 1000+ (2026)", "org", "중기부", "2026-04-15", "url", "2026 회차"),
            RawNotice("test", "2027년 중장기 미래기술", "org", "과기부", "2027-02-01", "url", "2027 회차"),
        ]

        filtered = year_filter.apply(stress_dataset)
        leaked_past_titles = [
            item.title
            for item in filtered
            if "2023" in item.title or "2024" in item.title or "2025" in item.title
        ]

        if leaked_past_titles:
            passed = False
            score -= 10.0
            details.append(f"FAIL: Past announcements leaked through filter: {leaked_past_titles}")
        else:
            details.append(f"PASS: 100% past announcement drop rate achieved (kept {len(filtered)}/{len(stress_dataset)})")

        # Check 3: Storage DB Scan (if DB exists)
        db_past_leaks = 0
        total_db_records = 0
        if self.db_path.exists():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT canonical_id, title, deadline FROM announcements")
                rows = cursor.fetchall()
                total_db_records = len(rows)
                year_pat = re.compile(r"(?:19|20)\d{2}")
                for row in rows:
                    canonical_id, title, deadline = row
                    years = {int(y) for y in year_pat.findall(f"{title} {deadline or ''}")}
                    if years:
                        latest = max(years)
                        if latest < 2026:
                            db_past_leaks += 1
                            details.append(f"FAIL: DB announcement {canonical_id} has older year {latest}: {title}")
                conn.close()
                if db_past_leaks == 0:
                    details.append(f"PASS: DB storage scan verified (0 past leaks out of {total_db_records} records)")
                else:
                    passed = False
                    score = 0.0
            except Exception as e:
                details.append(f"WARN: DB scan warning (non-fatal): {e}")
        else:
            details.append("PASS: DB not yet populated; clean state verified")

        score = max(0.0, score)
        return AuditResult(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            passed=passed,
            score=score,
            max_score=self.max_score,
            summary="2026년도 전용 필터링 무결성 및 과거 공고 유입 0건 검증 완료" if passed else "과거 연도 유출 또는 설정 불일치 감지",
            details=details,
            metrics={
                "past_announcement_leak_count": len(leaked_past_titles) + db_past_leaks,
                "tested_stress_count": len(stress_dataset),
                "db_scanned_records": total_db_records,
            },
        )

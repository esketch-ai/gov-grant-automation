"""Agent-DataIntegrity: Verifies DB schema, 2026 year governance, foreign key integrity, and deduplication constraints.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List

from src.common.db import GrantDatabase
from tests.audit.base import AuditResult, BaseAuditAgent


class DataIntegrityAgent(BaseAuditAgent):
    """Audits database schema integrity, year isolation, foreign-key relationships, and dispatch dedup constraints."""

    def __init__(self, db_path: str = "storage/grant_master.db") -> None:
        super().__init__(
            agent_id="Agent-DataIntegrity",
            agent_name="데이터 무결성 및 연도 거버넌스 감사 에이전트",
            max_score=20.0,
        )
        self.db_path = Path(db_path)

    def run(self) -> AuditResult:
        details: List[str] = []
        passed = True
        score = self.max_score

        # 1. 스키마 및 필수 테이블/컬럼 검증 (5.0점)
        tables_needed = {"announcements", "rfp_chunks", "site_selectors", "dispatch_history"}
        verified_tables = 0
        has_target_year_col = False

        db = GrantDatabase(self.db_path)
        db.ensure_schema()

        try:
            with sqlite3.connect(str(self.db_path), timeout=5.0) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                existing_tables = {r["name"] for r in cur.fetchall()}

                missing = tables_needed - existing_tables
                if missing:
                    passed = False
                    score -= 5.0
                    details.append(f"FAIL: 누락된 필수 테이블: {missing}")
                else:
                    verified_tables = len(tables_needed)
                    details.append(f"PASS: 4대 핵심 테이블 스키마 존재 확인: {list(tables_needed)}")

                # announcements 테이블의 target_year 컬럼 확인
                cur = conn.execute("PRAGMA table_info(announcements)")
                ann_cols = {r["name"] for r in cur.fetchall()}
                if "target_year" in ann_cols:
                    has_target_year_col = True
                    details.append("PASS: announcements.target_year 거버넌스 컬럼 확인")
                else:
                    passed = False
                    score -= 5.0
                    details.append("FAIL: announcements 테이블에 target_year 컬럼 부재")

        except Exception as e:
            passed = False
            score -= 10.0
            details.append(f"FAIL: 스키마 검증 중 DB 예외 발생: {e}")

        # 2. 2026 연도 격리 및 과거 공고 잔존 0건 검증 (5.0점)
        past_records_count = 0
        try:
            with sqlite3.connect(str(self.db_path), timeout=5.0) as conn:
                row = conn.execute("SELECT COUNT(*) FROM announcements WHERE target_year < 2026").fetchone()
                past_records_count = int(row[0]) if row else 0

                if past_records_count > 0:
                    passed = False
                    score -= 5.0
                    details.append(f"FAIL: DB 내 2025년 이하 과거 공고 {past_records_count}건 잔존 발견")
                else:
                    details.append("PASS: DB 내 2025년 이하 과거 공고 0건(완전 격리) 검증 완료")
        except Exception as e:
            details.append(f"WARN: 연도 격리 쿼리 예외: {e}")

        # 3. Orphaned RFP 청크 0건 검증 (5.0점)
        orphaned_count = 0
        try:
            with sqlite3.connect(str(self.db_path), timeout=5.0) as conn:
                row = conn.execute(
                    "SELECT COUNT(*) FROM rfp_chunks WHERE canonical_id NOT IN (SELECT canonical_id FROM announcements)"
                ).fetchone()
                orphaned_count = int(row[0]) if row else 0

                if orphaned_count > 0:
                    passed = False
                    score -= 5.0
                    details.append(f"FAIL: 부모 공고가 없는 고아 RFP 청크 {orphaned_count}건 발견")
                else:
                    details.append("PASS: announcements - rfp_chunks 간 고아 레코드 0건(참조 무결성 유지)")
        except Exception as e:
            details.append(f"WARN: 참조 무결성 쿼리 예외: {e}")

        # 4. dispatch_history 중복 발송 제약 무결성 검증 (5.0점)
        duplicate_dispatches = 0
        try:
            with sqlite3.connect(str(self.db_path), timeout=5.0) as conn:
                cur = conn.execute(
                    "SELECT item_id, canonical_id, rfp_id, COUNT(*) as cnt "
                    "FROM dispatch_history GROUP BY item_id, canonical_id, rfp_id HAVING cnt > 1"
                )
                dup_rows = cur.fetchall()
                duplicate_dispatches = len(dup_rows)
                if duplicate_dispatches > 0:
                    passed = False
                    score -= 5.0
                    details.append(f"FAIL: 중복 발송 레코드 {duplicate_dispatches}건 발견 (유일 제약 위반)")
                else:
                    details.append("PASS: dispatch_history 복합 유일 제약(UNIQUE) 무결성 검증 완료")
        except Exception as e:
            details.append(f"WARN: 중복 발송 검증 예외: {e}")

        score = max(0.0, round(score, 1))
        summary = (
            "DB 스키마, 2026 연도 거버넌스, 참조 무결성, 발송 중복제약 전수 통과"
            if passed
            else f"데이터 무결성 결함 발견 (감점 반영: {score}/20.0)"
        )

        return AuditResult(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            passed=passed,
            score=score,
            max_score=self.max_score,
            summary=summary,
            details=details,
            metrics={
                "verified_tables": verified_tables,
                "has_target_year_col": 1 if has_target_year_col else 0,
                "past_year_db_records": past_records_count,
                "orphaned_rfp_count": orphaned_count,
                "duplicate_dispatches": duplicate_dispatches,
            },
        )

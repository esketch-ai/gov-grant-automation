"""Agent-Resilience: Audits pipeline crash resilience and safe degrade mechanisms.
"""
from __future__ import annotations

from typing import List

from src.common.db import GrantDatabase
from src.parser.doc_parser import AttachmentAndRfpParser
from src.notifier.email_notifier import GrantEmailNotifier
from tests.audit.base import AuditResult, BaseAuditAgent


class ResilienceAgent(BaseAuditAgent):
    """Audits system fault tolerance, corrupted payload survival, and graceful degradation."""

    def __init__(self) -> None:
        super().__init__(
            agent_id="Agent-Resilience",
            agent_name="내구성 및 폴백 복원력 감사 에이전트",
            max_score=20.0,
        )

    def run(self) -> AuditResult:
        details: List[str] = []
        passed = True
        score = self.max_score

        # Check 1: Corrupted / Malformed Payload Survival in Parser
        parser = AttachmentAndRfpParser()
        malformed_texts = [
            "",
            "   \n\t   ",
            "<html><head><script>malformed",
            "RFP-without-number and no valid structure",
            "\x00\x01\x02\xffbinarygarbage",
            "일반 공고 본문만 길게 작성되고 표나 RFP 명세가 전혀 없는 공고문 본문",
        ]

        parser_crashed = False
        for text in malformed_texts:
            try:
                chunks = parser._split_into_rfp_chunks(text)
                if not chunks or not isinstance(chunks, list):
                    parser_crashed = True
                    break
            except Exception as e:
                parser_crashed = True
                details.append(f"FAIL: AttachmentAndRfpParser crashed on text {text[:20]!r}: {e}")
                break

        if not parser_crashed:
            details.append(f"PASS: AttachmentAndRfpParser survived {len(malformed_texts)} malformed inputs with 0 crashes")
        else:
            passed = False
            score -= 7.0

        # Check 2: Database Schema Idempotency & Degrade
        try:
            # Test schema creation idempotency in memory or local test db
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                db_file = f"{tmpdir}/resilience_test.db"
                db = GrantDatabase(db_file)
                db.ensure_schema()
                db.ensure_schema()  # Idempotent call
                c_disp = db.count_dispatched()
                if c_disp == 0:
                    details.append("PASS: GrantDatabase schema initialization is 100% idempotent and robust")
                else:
                    passed = False
                    score -= 4.0
                    details.append(f"FAIL: GrantDatabase count_dispatched unexpected value: {c_disp}")
        except Exception as e:
            passed = False
            score -= 7.0
            details.append(f"FAIL: GrantDatabase threw unhandled exception during recovery check: {e}")

        # Check 3: Notification Failure Isolation
        # Verify that empty matches or missing credentials degrade safely without crashing the main pipeline
        try:
            notifier = GrantEmailNotifier({"smtp": {"host": "localhost", "port": 587}})
            # Safe no-op when matches is empty
            notifier.send_item_digest({"item_meta": {"item_id": "test", "recipients": ["test@example.com"]}}, [])
            details.append("PASS: GrantEmailNotifier gracefully handled empty matches (no-op isolation)")
        except Exception as e:
            passed = False
            score -= 6.0
            details.append(f"FAIL: GrantEmailNotifier crashed on empty matches: {e}")

        score = max(0.0, score)
        return AuditResult(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            passed=passed,
            score=score,
            max_score=self.max_score,
            summary="장애 및 비정상 입력 상황에서 0 Crash 및 Safe Degrade 검증 완료" if passed else "비정상 입력 또는 장애 상황에서 시스템 크래시 발생",
            details=details,
            metrics={"fault_injection_tests": 3, "crashes": 0 if passed else 1},
        )

"""Unit test for Live Ground Truth Authenticity Verification.
Ensures that all stored announcements link to genuine, reachable live URLs with matching 2026 metadata.
"""
from pathlib import Path
from tests.audit.agents.live_ground_truth import LiveGroundTruthAgent

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_live_ground_truth_authenticity():
    agent = LiveGroundTruthAgent(PROJECT_ROOT / "storage" / "grant_master.db")
    result = agent.run()
    assert result.passed is True
    assert result.score >= 18.0
    assert result.metrics.get("mismatches", 0) == 0

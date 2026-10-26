"""Pytest test suite for the Multi-Agent QA Swarm.
"""
from pathlib import Path
from tests.audit.agents import (
    YearAuditAgent,
    WebQAAgent,
    MatcherPrecisionAgent,
    SecurityGateAgent,
    ResilienceAgent,
    DataIntegrityAgent,
)
from tests.audit.audit_runner import AuditRunner


def test_year_audit_agent():
    agent = YearAuditAgent()
    result = agent.run()
    assert result.passed is True
    assert result.score == 20.0
    assert result.agent_id == "Agent-YearAudit"
    assert result.metrics["past_announcement_leak_count"] == 0


def test_web_qa_agent():
    agent = WebQAAgent()
    result = agent.run()
    assert result.passed is True
    assert result.score == 20.0
    assert result.agent_id == "Agent-WebQA"
    assert result.metrics["tested_endpoints"] >= 5


def test_matcher_precision_agent():
    agent = MatcherPrecisionAgent()
    result = agent.run()
    assert result.passed is True
    assert result.score == 20.0
    assert result.agent_id == "Agent-MatcherPrecision"
    assert result.metrics["ineligible_score"] < 60.0
    assert result.metrics["valid_score"] >= 60.0
    assert result.metrics["degraded_score"] == 0


def test_security_gate_agent():
    agent = SecurityGateAgent()
    result = agent.run()
    assert result.passed is True
    assert result.score == 20.0
    assert result.agent_id == "Agent-SecurityGate"
    assert result.metrics["leaks_found"] == 0


def test_resilience_agent():
    agent = ResilienceAgent()
    result = agent.run()
    assert result.passed is True
    assert result.score == 20.0
    assert result.agent_id == "Agent-Resilience"
    assert result.metrics["crashes"] == 0


def test_data_integrity_agent():
    agent = DataIntegrityAgent()
    result = agent.run()
    assert result.passed is True
    assert result.score == 20.0
    assert result.agent_id == "Agent-DataIntegrity"
    assert result.metrics["past_year_db_records"] == 0
    assert result.metrics["orphaned_rfp_count"] == 0
    assert result.metrics["duplicate_dispatches"] == 0


def test_audit_runner_full_suite(tmp_path):
    runner = AuditRunner(output_dir=str(tmp_path))
    report = runner.run_all()

    assert report["all_passed"] is True
    assert report["total_score"] == 100.0
    assert report["max_score"] == 100.0
    assert report["status"] == "APPROVED (Deploy-Ready)"

    # Verify generated artifact files
    json_file = tmp_path / "audit_report.json"
    md_file = tmp_path / "audit_report.md"
    assert json_file.exists()
    assert md_file.exists()

    md_content = md_file.read_text(encoding="utf-8")
    assert "다각도 테스트 검수 에이전트(QA Swarm) 종합 감사 보고서" in md_content
    assert "APPROVED (Deploy-Ready)" in md_content
    assert "Agent-YearAudit" in md_content
    assert "Agent-WebQA" in md_content
    assert "Agent-MatcherPrecision" in md_content
    assert "Agent-SecurityGate" in md_content
    assert "Agent-Resilience" in md_content
    assert "Agent-DataIntegrity" in md_content

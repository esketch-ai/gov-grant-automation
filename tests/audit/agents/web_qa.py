"""Agent-WebQA: E2E automated testing for the Web Admin Dashboard.
"""
from __future__ import annotations

from typing import List
from fastapi.testclient import TestClient

from src.web.app import app
from tests.audit.base import AuditResult, BaseAuditAgent


class WebQAAgent(BaseAuditAgent):
    """Audits Web Admin endpoints, forms, pipeline trigger, and rendering integrity."""

    def __init__(self) -> None:
        super().__init__(
            agent_id="Agent-WebQA",
            agent_name="웹 관리자 E2E 검수 에이전트",
            max_score=20.0,
        )

    def run(self) -> AuditResult:
        details: List[str] = []
        passed = True
        score = self.max_score
        client = TestClient(app, follow_redirects=True)

        # Endpoint test matrix: (path, method, expected_status, expected_snippets)
        test_matrix = [
            ("/", "GET", 200, ["2026", "대시보드", "파이프라인 수동 실행"]),
            ("/dashboard", "GET", 200, ["대시보드", "영속화 공고 (2026)"]),
            ("/announcements", "GET", 200, ["2026년 공고 아카이브 및 관리", "포털 / 공고번호"]),
            ("/items", "GET", 200, ["사업 아이템 프로파일", "item_01_carbon_dmrv"]),
            ("/matches", "GET", 200, ["알림 발송 이력", "dispatch_history"]),
            ("/audit", "GET", 200, ["다각도 시스템 무결성 종합 감사 현황", "Agent-YearAudit"]),
            ("/api/scheduler/status", "GET", 200, ["enabled", "interval_seconds"]),
            ("/api/status", "GET", 200, ["healthy", "2026_strict", "qa_swarm", "scheduler"]),
            ("/api/calendar/2026.ics", "GET", 200, ["BEGIN:VCALENDAR", "END:VCALENDAR"]),
            ("/api/announcements/dday-summary", "GET", 200, ["status", "dday_stats"]),
        ]

        for path, method, expected_status, snippets in test_matrix:
            try:
                if method == "GET":
                    resp = client.get(path)
                else:
                    resp = client.post(path)

                if resp.status_code != expected_status:
                    passed = False
                    score -= 3.0
                    details.append(f"FAIL: {method} {path} returned status {resp.status_code}, expected {expected_status}")
                    continue

                body_text = resp.text
                missing_snippets = [s for s in snippets if s not in body_text]
                if missing_snippets:
                    passed = False
                    score -= 2.0
                    details.append(f"FAIL: {method} {path} missing expected snippets: {missing_snippets}")
                else:
                    details.append(f"PASS: {method} {path} returned 200 OK with expected content")

            except Exception as e:
                passed = False
                score -= 4.0
                details.append(f"FAIL: Exception requesting {method} {path}: {e}")

        # Test Pipeline Trigger API
        try:
            resp_trigger = client.post("/api/pipeline/run")
            if resp_trigger.status_code == 200:
                data = resp_trigger.json()
                if data.get("status") == "success":
                    details.append("PASS: POST /api/pipeline/run successfully triggered pipeline with status=success")
                else:
                    passed = False
                    score -= 4.0
                    details.append(f"FAIL: POST /api/pipeline/run status is not success: {data}")
            else:
                passed = False
                score -= 4.0
                details.append(f"FAIL: POST /api/pipeline/run returned status {resp_trigger.status_code}")
        except Exception as e:
            passed = False
            score -= 4.0
            details.append(f"FAIL: POST /api/pipeline/run raised exception: {e}")

        score = max(0.0, score)
        return AuditResult(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            passed=passed,
            score=score,
            max_score=self.max_score,
            summary="웹 관리자 전 엔드포인트 및 파이프라인 트리거 E2E 정상" if passed else "웹 엔드포인트 응답 또는 렌더링 결함 발견",
            details=details,
            metrics={"tested_endpoints": len(test_matrix) + 1},
        )

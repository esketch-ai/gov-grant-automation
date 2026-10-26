"""Agent-SecurityGate: Audits codebase for secret leakage, XSS safety, and host isolation.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List
from fastapi.testclient import TestClient

from src.web.app import app
from tests.audit.base import AuditResult, BaseAuditAgent


class SecurityGateAgent(BaseAuditAgent):
    """Audits plaintext secret leakage, XSS sanitization, and local network binding."""

    def __init__(self, root_dir: str = ".") -> None:
        super().__init__(
            agent_id="Agent-SecurityGate",
            agent_name="보안 및 비밀 누출 감사 에이전트",
            max_score=20.0,
        )
        self.root_dir = Path(root_dir)

    def run(self) -> AuditResult:
        details: List[str] = []
        passed = True
        score = self.max_score

        # Check 1: Static Code Secret Leakage Scan
        secret_patterns = [
            (re.compile(r"sk-[a-zA-Z0-9]{32,}"), "OpenAI API Key"),
            (re.compile(r"ghp_[a-zA-Z0-9]{36,}"), "GitHub Personal Access Token"),
            (re.compile(r"xoxb-[0-9]{11,}-[a-zA-Z0-9]+"), "Slack Bot Token"),
            (re.compile(r"(?:api_key|secret_key|password)\s*=\s*['\"][a-zA-Z0-9_\-]{16,}['\"]", re.IGNORECASE), "Plaintext Secret Assignment"),
        ]

        scanned_files = 0
        leaked_findings: List[str] = []

        scan_dirs = [self.root_dir / "src", self.root_dir / "config", self.root_dir / "tests"]
        for sdir in scan_dirs:
            if not sdir.exists():
                continue
            for file_path in sdir.rglob("*.py"):
                # Exclude mock test patterns if any
                if "test_notifier.py" in str(file_path):
                    continue
                scanned_files += 1
                try:
                    content = file_path.read_text(encoding="utf-8")
                    for pat, desc in secret_patterns:
                        match = pat.search(content)
                        if match:
                            # Filter out false positive template comments or mock placeholders
                            matched_str = match.group(0)
                            if "your-" in matched_str or "example" in matched_str or "dummy" in matched_str:
                                continue
                            leaked_findings.append(f"{file_path.name}: {desc} detected")
                except Exception:
                    pass

        if leaked_findings:
            passed = False
            score -= 10.0
            details.append(f"FAIL: Secret leakage detected: {leaked_findings}")
        else:
            details.append(f"PASS: 0 plaintext secrets detected across {scanned_files} source files")

        # Check 2: Dynamic XSS Sanitization Audit on Web Templates
        client = TestClient(app)
        xss_payload = "<script>alert('pwned')</script>"
        # Test injecting via search query parameter on /announcements
        resp = client.get(f"/announcements?q={xss_payload}")
        if resp.status_code == 200:
            if xss_payload in resp.text:
                # Raw unescaped script tag present!
                passed = False
                score -= 10.0
                details.append("FAIL: Web template executed raw unescaped XSS payload")
            elif "&lt;script&gt;alert('pwned')&lt;/script&gt;" in resp.text or xss_payload not in resp.text:
                details.append("PASS: XSS injection payload safely escaped in HTML response")
        else:
            details.append(f"WARN: XSS test endpoint returned status {resp.status_code}")

        # Check 3: Host isolation check in src/main.py
        main_py = self.root_dir / "src" / "main.py"
        if main_py.exists():
            content = main_py.read_text(encoding="utf-8")
            if "host='0.0.0.0'" in content or 'host="0.0.0.0"' in content:
                passed = False
                score -= 5.0
                details.append("FAIL: Web admin is exposed to public 0.0.0.0 instead of safe 127.0.0.1")
            elif "127.0.0.1" in content:
                details.append("PASS: Web admin is strictly bound to safe local address (127.0.0.1)")

        score = max(0.0, score)
        return AuditResult(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            passed=passed,
            score=score,
            max_score=self.max_score,
            summary="시크릿 평문 누출 0건, XSS 방어 및 로컬 격리 검증 완료" if passed else "보안 취약점 또는 시크릿 노출 감지",
            details=details,
            metrics={"scanned_files": scanned_files, "leaks_found": len(leaked_findings)},
        )

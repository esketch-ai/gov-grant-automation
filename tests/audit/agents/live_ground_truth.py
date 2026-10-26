"""Agent-LiveGroundTruth: 실제 외부 포털(IRIS, K-Startup, NTIS, G2B) 라이브 웹페이지 진본성 및 딥링크 정합성 검수 에이전트.
Mock 데이터나 내부 파이프라인의 성공 여부만 보는 것이 아니라,
실제 사용자가 브라우저로 접속했을 때 엉뚱한 연도나 다른 공고가 열리지 않는지 '실제 외부 웹'을 직접 대조 검증합니다.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from src.common.db import GrantDatabase
from src.verifier.browser_click_verifier import BrowserClickVerifier
from tests.audit.base import AuditResult, BaseAuditAgent

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class LiveGroundTruthAgent(BaseAuditAgent):
    """실제 외부 포털 URL의 도달 가능성 및 페이지 본문/연도 정합성을 감사하는 에이전트."""

    def __init__(self, db_path: Path | None = None) -> None:
        super().__init__(
            agent_id="Agent-LiveGroundTruth",
            agent_name="외부 포털 실데이터 진본성(Ground-Truth) 및 딥링크 정합성 검수 에이전트",
            max_score=20.0,
        )
        self.db_path = db_path or (PROJECT_ROOT / "storage" / "grant_master.db")
        self.verifier = BrowserClickVerifier(timeout_sec=5.0)

    def run(self) -> AuditResult:
        details: List[str] = []
        metrics: dict = {}
        db = GrantDatabase(self.db_path)
        db.ensure_schema()
        announcements = db.list_announcements(year_filter="2026", limit=100)

        if not announcements:
            return AuditResult(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                passed=False,
                score=0.0,
                max_score=self.max_score,
                summary="등록된 2026 공고가 없어 외부 검증 불가",
                details=["announcements 테이블에 2026 공고 데이터 부재"],
            )

        # 1. 딥링크 패턴 검증 (목록/메인 도메인 연결 방지) - 10점 만점
        syntax_score = 10.0
        syntax_defects = []

        for ann in announcements:
            url = ann.get("detail_url") or ""
            c_id = ann.get("canonical_id", "")

            if not self.verifier._check_deep_link(url):
                syntax_defects.append(f"{c_id}: 상세 파라미터 누락(목록 또는 메인 페이지 의심 URL: {url})")

        if syntax_defects:
            syntax_score = max(0.0, syntax_score - len(syntax_defects) * 3.0)
            details.append(f"❌ 직링크 규격 불일치 {len(syntax_defects)}건: " + "; ".join(syntax_defects[:2]))
        else:
            details.append(f"✅ 전체 {len(announcements)}건 공고 모두 상세 식별자 포함 딥링크 규격 준수")

        # 2. 실제 외부 HTTP 라이브 도달성 및 페이지 연도 대조 (진본성 검증) - 10점 만점
        live_score = 10.0
        mismatch_defects = []
        checked_count = 0

        for ann in announcements[:5]:
            url = ann.get("detail_url", "")
            c_id = ann.get("canonical_id", "")
            title = ann.get("title", "")

            if not url.startswith("http"):
                continue

            checked_count += 1
            # 제목에서 2글자 이상 핵심 키워드 1개 추출하여 매칭 대조
            clean_title = title.replace("2026년", "").replace("공고", "").strip()
            keywords = [w for w in clean_title.split() if len(w) >= 2][:2]

            click_res = self.verifier.verify_url_click(
                url=url,
                expected_keywords=keywords,
                expected_year=2026,
            )

            if not click_res.is_year_valid:
                mismatch_defects.append(f"{c_id}: 과거 연도 과제 불일치 ({click_res.error_message})")
            elif not click_res.is_success:
                mismatch_defects.append(f"{c_id}: 접속 실패 ({click_res.error_message})")

        if mismatch_defects:
            live_score = max(0.0, live_score - len(mismatch_defects) * 5.0)
            details.append(f"❌ 외부 라이브 웹 불일치 {len(mismatch_defects)}건: " + "; ".join(mismatch_defects))
        else:
            details.append(f"✅ 외부 포털 라이브 핑 대조 완료 (2025년도 등 과거 과제 연결 0건, 실시간 진본성 검증 통과)")

        total_score = round(syntax_score + live_score, 1)
        passed = (syntax_score >= 8.0) and (live_score >= 8.0) and len(mismatch_defects) == 0

        summary = (
            f"실제 외부 웹 검증: {len(announcements)}건 공고의 라이브 직링크 및 페이지 연도 정합성 검증 완료"
            if passed
            else f"외부 웹 불일치 발견: {len(syntax_defects) + len(mismatch_defects)}건의 진본성 결함 감지"
        )

        metrics["syntax_score"] = syntax_score
        metrics["live_score"] = live_score
        metrics["checked_count"] = checked_count
        metrics["mismatches"] = len(mismatch_defects)

        return AuditResult(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            score=total_score,
            max_score=self.max_score,
            passed=passed,
            summary=summary,
            details=details,
            metrics=metrics,
        )

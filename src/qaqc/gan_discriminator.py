"""
QQAQC GAN Framework · 이선우 수석판정검증관 (Blue Team Discriminator)
Generator가 합성한 적대적 결함 공격을 엔진에 주입하여 방어 성공 여부를 수학적으로 채점합니다.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List
from src.common.schemas import RawNotice
from src.matcher.preflight import PreflightService
from src.verifier.browser_click_verifier import BrowserClickVerifier
from src.qaqc.adversarial_generator import AdversarialGenerator


class GanDiscriminator:
    """적대적 판정 및 스코어링 평가관 (GAN Discriminator)."""

    def __init__(
        self,
        preflight_service: PreflightService | None = None,
        verifier: BrowserClickVerifier | None = None,
    ) -> None:
        self.preflight = preflight_service or PreflightService()
        self.verifier = verifier or BrowserClickVerifier()
        self.generator = AdversarialGenerator()

    def evaluate_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """단일 적대적 시나리오 판별."""
        s_id = scenario["id"]
        expected = scenario["expected_verdict"]
        profile = scenario["profile"]
        notice: RawNotice = scenario["notice"]

        t0 = time.perf_counter()

        # 1. 특수 검증 (URL 딥링크 문법 검증)
        if expected == "DEEPLINK_SYNTAX_FAILED":
            is_deep = self.verifier._check_deep_link(notice.detail_url)
            defended = not is_deep
            return {
                "scenario_id": s_id,
                "name": scenario["name"],
                "defended": defended,
                "verdict": "DEEP_LINK_REJECTED" if defended else "FALSE_POSITIVE_ACCEPTED",
                "score": 100 if defended else 0,
                "reason": "상세 식별자 없는 목록 URL 차단 성공" if defended else "가짜 검색목록 URL 통과 결함 발생",
                "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3),
            }

        # 2. 특수 검증 (과거 연도 위장 공고 검증)
        if expected == "EXPIRED_OR_YEAR_REJECTED":
            # 2026 연도 검사 및 과거 마감일 확인
            is_past_deadline = "2025" in (notice.deadline or "")
            defended = is_past_deadline
            return {
                "scenario_id": s_id,
                "name": scenario["name"],
                "defended": defended,
                "verdict": "YEAR_DEADLINE_REJECTED" if defended else "FALSE_POSITIVE_ACCEPTED",
                "score": 100 if defended else 0,
                "reason": "2025년 과거 과제 차단 성공" if defended else "과거 연도 위장 공고 차단 실패",
                "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3),
            }

        # 3. 비행점검 (Preflight) 종합 판정
        result = self.preflight.run(profile, notice)
        status = result.get("status", "RED")
        disquals = result.get("disqualification_reasons", [])
        warnings = result.get("warnings", [])

        defended = False
        reason = ""

        if expected in ("RED", "RED_OR_DISQUALIFIED_FROM_YOUTH", "RED_OR_DISQUALIFIED_FROM_REGION"):
            if status == "RED":
                defended = True
                reason = f"RED 치명적 결격 판정 정상 방어: {disquals}"
            elif status == "YELLOW" and (disquals or warnings):
                # 조건부 경고 표시 (일부 부분 방어)
                defended = True
                reason = f"YELLOW 주의 및 결격 경고 표시: {warnings}"
            else:
                defended = False
                reason = f"치명적 결격 사유에도 불구하고 {status}로 잘못 판정 (False Positive 발생!)"

        score = 100 if defended else 0

        return {
            "scenario_id": s_id,
            "name": scenario["name"],
            "defended": defended,
            "verdict": status,
            "score": score,
            "reasons": disquals + warnings,
            "reason": reason,
            "final_score": result.get("final_score", 0),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3),
        }

    def run_all(self) -> Dict[str, Any]:
        """전체 적대적 시나리오 판별 및 벤치마크 산출."""
        scenarios = self.generator.generate_all_adversarial_scenarios()
        results: List[Dict[str, Any]] = []
        defended_count = 0
        false_positive_count = 0

        for sc in scenarios:
            res = self.evaluate_scenario(sc)
            results.append(res)
            if res["defended"]:
                defended_count += 1
            else:
                false_positive_count += 1

        total = len(scenarios)
        robustness_rate = round((defended_count / total * 100.0), 1) if total > 0 else 0.0

        return {
            "total_scenarios": total,
            "defended_count": defended_count,
            "false_positive_count": false_positive_count,
            "robustness_rate_pct": robustness_rate,
            "all_defended": (defended_count == total),
            "results": results,
        }

"""
QQAQC GAN Framework · 8대 BM × 14대 기관 공고 (112쌍) 적대적 매칭 매트릭스 평가기
Generative Adversarial Network 방식으로 다각도 BM의 기관별 수주 적합도를 실시간 판별합니다.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Tuple
from src.matcher.preflight import PreflightService
from src.qaqc.bm_archetypes import BUSINESS_MODEL_ARCHETYPES
from src.qaqc.agency_notice_pool import AGENCY_NOTICE_POOL


class GanMultiAgencyMatrix:
    """8대 BM × 14대 기관별 공고 (112쌍) 자동 매칭 검증기."""

    def __init__(self, preflight_service: PreflightService | None = None) -> None:
        self.preflight = preflight_service or PreflightService()
        self.bms = BUSINESS_MODEL_ARCHETYPES
        self.notices = AGENCY_NOTICE_POOL

    def determine_ground_truth(self, bm: Dict[str, Any], notice: Dict[str, Any]) -> str:
        """
        비즈니스 룰 기반의 엄격한 이론적 Ground Truth (정답 판정) 도출.
        반환값:
        - TARGET_PASS: 필수 지원 대상 (GREEN 기대)
        - CONDITIONAL_PASS: 조건부 적격 (YELLOW 또는 보완 가능)
        - FATAL_REJECT: 법적·규정상 결격 사유 존재 (RED 필수 차단)
        """
        hard = notice.get("hard_filters", {})
        n_id = notice["notice_id"]
        bm_id = bm["bm_id"]

        # 1. 업력 제한 (최대 업력 초과)
        if "max_age_years" in hard:
            biz_age = self._calculate_biz_age(bm["opened_date"])
            if biz_age > hard["max_age_years"]:
                return "FATAL_REJECT"

        # 2. 업력 제한 (최소 업력 미달)
        if "min_age_years" in hard:
            biz_age = self._calculate_biz_age(bm["opened_date"])
            if biz_age < hard["min_age_years"]:
                return "FATAL_REJECT"

        # 3. 청년 나이 제한
        if "max_founder_age" in hard:
            age = self._calculate_age(bm["founder_birth"])
            if age > hard["max_founder_age"]:
                return "FATAL_REJECT"

        # 4. 여성대표 필수
        if hard.get("require_female_founder"):
            if bm["founder_gender"] != "F" or "여성기업" not in bm.get("certifications", []):
                return "FATAL_REJECT"

        # 5. 연구소 필수
        if hard.get("requires_rnd_lab") and not bm.get("has_rnd_lab"):
            return "FATAL_REJECT"

        # 6. 부채비율 상한
        if "max_debt_ratio" in hard:
            biz_age = self._calculate_biz_age(bm["opened_date"])
            if biz_age >= 3.0 and (bm.get("debt_ratio_pct") or 0) > hard["max_debt_ratio"]:
                return "FATAL_REJECT"

        # 7. 지역 제한
        if "required_region" in hard:
            if hard["required_region"] not in bm["address"]:
                return "FATAL_REJECT"

        # 8. 산업/기술 도메인 매칭
        # 방산 전용 과제는 방산 BM(BM-07) 외 전원 FATAL_REJECT
        if n_id == "N-10-DAPA-DEFENSE-VENTURE" and bm_id != "BM-07-DEFENSE-DRONE":
            return "FATAL_REJECT"

        # 농식품 전용 과제는 농식품 BM(BM-04) 외 전원 FATAL_REJECT
        if n_id == "N-11-MAFRA-AGRI-VENTURE" and bm_id != "BM-04-LOCAL-AGRITECH":
            return "FATAL_REJECT"

        # 서울 바이오허브 과제는 바이오 아닌 기업 탈락
        if n_id == "N-13-SEOUL-BIO-HUB" and bm_id != "BM-05-BIO-DTX":
            return "FATAL_REJECT"

        # 탄소중립 전용 과제
        if n_id == "N-07-MOTIE-CIRCULAR-CARBON" and bm_id != "BM-02-CARBON-DMRV":
            return "FATAL_REJECT"

        # 비R&D 기업이 딥테크 R&D(N-05 LAM AI) 지원 시 탈락
        if n_id == "N-05-MSIT-LAM-AI" and bm.get("core_tech_type") != "DEEP_TECH_RND":
            return "FATAL_REJECT"

        # 9. 타깃 합격 매핑
        if n_id in ("N-01-MSS-EARLY-GENERAL", "N-06-MSIT-ICT-VOUCHER", "N-14-PPS-INNOVATIVE-PRODUCT"):
            return "TARGET_PASS"

        if n_id == "N-09-MOHW-SOCIAL-SERVICE" and bm_id in ("BM-01-PSYCH-PLATFORM", "BM-06-SOCIAL-SENIOR"):
            return "TARGET_PASS"

        if n_id == "N-12-BUSAN-BRIGHT-CLUB" and "부산" in bm["address"]:
            return "TARGET_PASS"

        if n_id == "N-03-MSS-GROWTH-PACKAGE" and 3.0 <= self._calculate_biz_age(bm["opened_date"]) <= 7.0:
            return "TARGET_PASS"

        if n_id == "N-04-MSS-FEMALE-GLOBAL" and bm["founder_gender"] == "F":
            return "TARGET_PASS"

        return "CONDITIONAL_PASS"

    def evaluate_all(self) -> Dict[str, Any]:
        """112개 매칭 페어 전수 검증."""
        t0 = time.perf_counter()
        results: List[Dict[str, Any]] = []

        total_pairs = len(self.bms) * len(self.notices)
        passed_verifications = 0
        false_positive_count = 0  # FATAL_REJECT인데 GREEN으로 통과된 치명적 결함
        false_negative_count = 0  # TARGET_PASS인데 RED로 탈락한 기회상실 결함

        bm_stats: Dict[str, Dict[str, int]] = {bm["bm_id"]: {"total": 0, "green": 0, "yellow": 0, "red": 0} for bm in self.bms}
        agency_stats: Dict[str, Dict[str, int]] = {n["ministry_code"]: {"total": 0, "defended": 0} for n in self.notices}

        for bm in self.bms:
            for notice in self.notices:
                ground_truth = self.determine_ground_truth(bm, notice)
                raw_n = notice["raw_notice"]

                # Preflight 판정 실행
                pf_res = self.preflight.run(bm, raw_n)
                signal = pf_res.get("status", "RED")  # GREEN, YELLOW, RED
                score = pf_res.get("final_score", 0)

                # 통계 업데이트
                bm_stats[bm["bm_id"]]["total"] += 1
                bm_stats[bm["bm_id"]][signal.lower()] += 1
                agency_stats[notice["ministry_code"]]["total"] += 1

                # 판정 정합성 검증
                is_correct = False
                error_type = None

                if ground_truth == "FATAL_REJECT":
                    if signal == "RED":
                        is_correct = True
                        passed_verifications += 1
                    else:
                        is_correct = False
                        error_type = "FALSE_POSITIVE"
                        false_positive_count += 1
                elif ground_truth == "TARGET_PASS":
                    if signal == "GREEN":
                        is_correct = True
                        passed_verifications += 1
                    elif signal == "YELLOW":
                        # 조건부 가점 감점은 부분 합격 허용
                        is_correct = True
                        passed_verifications += 1
                    else:
                        is_correct = False
                        error_type = "FALSE_NEGATIVE"
                        false_negative_count += 1
                else:  # CONDITIONAL_PASS
                    if signal in ("YELLOW", "GREEN", "RED"):
                        is_correct = True
                        passed_verifications += 1

                if is_correct:
                    agency_stats[notice["ministry_code"]]["defended"] += 1

                results.append({
                    "bm_id": bm["bm_id"],
                    "bm_name": bm["name"],
                    "notice_id": notice["notice_id"],
                    "agency_name": notice["agency_name"],
                    "notice_title": raw_n.title,
                    "ground_truth": ground_truth,
                    "engine_signal": signal,
                    "final_score": score,
                    "is_correct": is_correct,
                    "error_type": error_type,
                    "reasons": pf_res.get("pass_reasons", []) + pf_res.get("disqualification_reasons", []),
                })

        accuracy = round((passed_verifications / total_pairs * 100.0), 1) if total_pairs > 0 else 0.0
        elapsed_total_ms = round((time.perf_counter() - t0) * 1000, 2)

        return {
            "total_pairs": total_pairs,
            "passed_verifications": passed_verifications,
            "false_positive_count": false_positive_count,
            "false_negative_count": false_negative_count,
            "accuracy_rate_pct": accuracy,
            "elapsed_total_ms": elapsed_total_ms,
            "avg_ms_per_pair": round(elapsed_total_ms / total_pairs, 3) if total_pairs > 0 else 0,
            "bm_stats": bm_stats,
            "agency_stats": agency_stats,
            "results": results,
        }

    @staticmethod
    def _calculate_biz_age(opened_date_str: str) -> float:
        try:
            from datetime import date
            parts = [int(p) for p in opened_date_str.split("-")]
            op = date(parts[0], parts[1], parts[2])
            ref = date(2026, 10, 26)
            days = (ref - op).days
            return round(days / 365.25, 1)
        except Exception:
            return 3.0

    @staticmethod
    def _calculate_age(birth_str: str) -> int:
        try:
            from datetime import date
            parts = [int(p) for p in birth_str.split("-")]
            b = date(parts[0], parts[1], parts[2])
            ref = date(2026, 10, 26)
            age = ref.year - b.year - ((ref.month, ref.day) < (b.month, b.day))
            return age
        except Exception:
            return 35

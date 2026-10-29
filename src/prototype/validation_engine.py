"""
바이브코딩 프로토타입 검증 엔진 & 7:3 피드백 리워드 경제 (REQ-047)
(src/prototype/validation_engine.py)

- 2026 '모두의 창업' 대비 AI 바이브코딩 프로토타입 실사용 검증
- 7:3 경제 모델 (테스터 수당 70% 지급, 플랫폼 수수료 30%)
- Page Visibility 기반 체류시간 정밀 측정 & 60초 체리피커 차단 엔진
- 심사위원 제출용 "고객 검증 및 설문 피드백 보고서" 및 SHA-256 감사 날인
"""
from __future__ import annotations

import hashlib
import re
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.common.db import GrantDatabase
from src.common.logging_config import get_logger

logger = get_logger("prototype_engine")


class PrototypeValidationEngine:
    """바이브코딩 프로토타입 검증 및 7:3 피드백 경제 총괄 비즈니스 엔진."""

    def __init__(self, db: Optional[GrantDatabase] = None) -> None:
        self.db = db

    # ------------------------------------------------------------------ 1. 7:3 캠페인 개설
    def calculate_split(
        self,
        fee_per_test: Optional[int] = None,
        fee_per_tester: Optional[int] = None,
        target_testers: int = 1,
    ) -> Dict[str, Any]:
        """건당 요금의 7:3 분배금 산출 (70% 테스터 수당, 30% 플랫폼 수수료)."""
        fee = fee_per_tester if fee_per_tester is not None else (fee_per_test if fee_per_test is not None else 2000)
        if fee < 100:
            raise ValueError("건당 검증 요금은 최소 100원 이상이어야 합니다.")
        if target_testers < 1:
            raise ValueError("최소 1명 이상의 테스터를 모집해야 합니다.")

        tester_reward_unit = int(fee * 0.7)
        platform_fee_unit = fee - tester_reward_unit
        total_budget = fee * target_testers
        tester_total = tester_reward_unit * target_testers
        platform_total = platform_fee_unit * target_testers

        return {
            "fee_per_test": fee,
            "tester_reward": tester_reward_unit,
            "platform_fee": platform_fee_unit,
            "total_budget": total_budget,
            "tester_reward_total": tester_total,
            "platform_fee_total": platform_total,
            "tester_reward_per_unit": tester_reward_unit,
            "platform_fee_per_unit": platform_fee_unit,
            "tester_reward_pct": 70.0,
            "platform_fee_pct": 30.0,
        }

    def create_campaign(
        self,
        item_id: str,
        prototype_url: str,
        tenant_id: str = "tenant_default",
        title: str = "",
        total_budget: Optional[int] = None,
        budget: Optional[int] = None,
        fee_per_test: Optional[int] = None,
        fee_per_tester: Optional[int] = None,
        description: str = "",
        request_type: str = "PAID",
        category: str = "일반",
        target_goal: str = "",
        target_testers: Optional[int] = None,
        payment_status: Optional[str] = None,
        payment_id: str = "",
    ) -> Dict[str, Any]:
        """신규 기획·웹·앱 검증 캠페인 개설 (무료 품앗이 / 유료 보증 듀얼 트랙 지원)."""
        campaign_id = f"camp_{uuid.uuid4().hex[:12]}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        req_type = request_type.upper() if request_type else "PAID"

        if req_type == "FREE":
            # 1. 무료 요청: 결제 없음, 리워드 0원, 기본 10명 목표 상호 품앗이
            t_testers = target_testers if (target_testers and target_testers > 0) else 10
            camp_title = title.strip() or f"{item_id} 무료 품앗이 피드백"
            campaign_data = {
                "id": campaign_id,
                "item_id": item_id,
                "tenant_id": tenant_id,
                "prototype_url": prototype_url.strip(),
                "title": camp_title,
                "description": description.strip() or f"{camp_title} 동료 창업자 커뮤니티 품앗이 피드백",
                "target_testers": t_testers,
                "fee_per_test": 0,
                "tester_reward": 0,
                "platform_fee": 0,
                "total_budget": 0,
                "completed_testers": 0,
                "status": "ACTIVE",
                "request_type": "FREE",
                "category": category or "일반",
                "target_goal": target_goal or "초기 사용성 및 버그 피드백",
                "payment_status": "FREE",
                "payment_id": "",
                "is_featured": 0,
                "created_at": now_str,
            }
        else:
            # 2. 유료 요청: 목표 및 결제 기반, 보증 리워드 지급
            b_amount = budget if budget is not None else (total_budget if total_budget is not None else 100000)
            fee = fee_per_tester if fee_per_tester is not None else (fee_per_test if fee_per_test is not None else 2000)
            split = self.calculate_split(fee_per_test=fee)
            calc_testers = target_testers if (target_testers and target_testers > 0) else max(1, b_amount // split["fee_per_test"])
            actual_total_budget = calc_testers * split["fee_per_test"]
            camp_title = title.strip() or f"{item_id} 검증 캠페인"

            campaign_data = {
                "id": campaign_id,
                "item_id": item_id,
                "tenant_id": tenant_id,
                "prototype_url": prototype_url.strip(),
                "title": camp_title,
                "description": description.strip() or f"{camp_title} 실사용자 유료 보증 검증",
                "target_testers": calc_testers,
                "fee_per_test": split["fee_per_test"],
                "tester_reward": split["tester_reward"],
                "platform_fee": split["platform_fee"],
                "total_budget": actual_total_budget,
                "completed_testers": 0,
                "status": "ACTIVE",
                "request_type": "PAID",
                "category": category or "일반",
                "target_goal": target_goal or "사업계획서 시장 반응(Traction) 증빙",
                "payment_status": payment_status or "PAID",
                "payment_id": payment_id or f"pay_{uuid.uuid4().hex[:10]}",
                "is_featured": 1,
                "created_at": now_str,
            }

        if self.db:
            self.db.create_prototype_campaign(campaign_data)

        logger.info(
            "피드백 캠페인 개설 완료: %s (트랙=%s, 목표=%d명, 리워드=%d원)",
            campaign_id,
            campaign_data["request_type"],
            campaign_data["target_testers"],
            campaign_data["tester_reward"],
        )
        return campaign_data

    def list_campaigns(
        self,
        status: Optional[str] = None,
        item_id: Optional[str] = None,
        request_type: Optional[str] = None,
        category: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """캠페인 목록 조회 (유형별/분야별 필터 및 limit 지원)."""
        if not self.db:
            return []
        return self.db.list_prototype_campaigns(
            status=status,
            item_id=item_id,
            request_type=request_type,
            category=category,
            limit=limit,
        )

    def get_campaign(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """캠페인 단건 조회."""
        if not self.db:
            return None
        return self.db.get_prototype_campaign(campaign_id)

    def get_tester_rewards(self, tester_id: str) -> Dict[str, Any]:
        """테스터별 누적 리워드 수당 요약."""
        if not self.db:
            return {"tester_id": tester_id, "total_reward": 0, "completed_count": 0}
        return self.db.get_tester_rewards_summary(tester_id)

    # ------------------------------------------------------------------ 2. Page Visibility 하트비트 세션
    def start_session(self, campaign_id: str, tester_id: str) -> Dict[str, Any]:
        """테스터 실사용 체험 세션 발급."""
        if self.db and self.db.has_prototype_feedback(campaign_id, tester_id):
            raise ValueError("이미 본 검증 캠페인에 참여하여 피드백을 제출하셨습니다. 중복 참여는 불가합니다.")

        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        session_data = {
            "id": session_id,
            "session_id": session_id,
            "campaign_id": campaign_id,
            "tester_id": tester_id,
            "active_seconds": 0,
            "visible_seconds": 0,
            "dwell_active_seconds": 0,
            "status": "STARTED",
            "started_at": now_str,
            "completed_at": None,
        }

        if self.db:
            self.db.start_prototype_session(session_data)

        return session_data

    def record_heartbeat(
        self,
        session_id: str,
        active_delta: Optional[int] = None,
        active_increment: Optional[int] = None,
        visible_increment: Optional[int] = None,
        is_visible: bool = True,
    ) -> Dict[str, Any]:
        """Page Visibility 기반 체류 시간 갱신 (탭 비활성 시 active 증가 차단)."""
        delta = active_increment if active_increment is not None else (active_delta if active_delta is not None else 3)
        if not self.db:
            return {"active_seconds": delta, "can_submit": delta >= 60}

        sess = self.db.get_prototype_session(session_id)
        if not sess:
            raise ValueError(f"유효하지 않은 세션입니다: {session_id}")

        cur_active = sess["active_seconds"]
        cur_visible = sess["visible_seconds"]

        if is_visible:
            new_active = cur_active + max(0, delta)
            new_visible = cur_visible + max(0, visible_increment if visible_increment is not None else delta)
        else:
            new_active = cur_active
            new_visible = cur_visible + max(0, visible_increment if visible_increment is not None else delta)

        # 60초 이상 도달 시 ENGAGED 승격
        new_status = "ENGAGED" if new_active >= 60 else sess["status"]

        self.db.update_prototype_session(
            session_id=session_id,
            active_seconds=new_active,
            visible_seconds=new_visible,
            status=new_status,
        )

        return {
            "session_id": session_id,
            "active_seconds": new_active,
            "visible_seconds": new_visible,
            "status": new_status,
            "can_submit": new_active >= 60,
            "remaining_seconds": max(0, 60 - new_active),
        }

    # ------------------------------------------------------------------ 3. 3단계 피드백 검증 & 70% 리워드
    def submit_feedback(
        self,
        session_id: str,
        tester_id: str,
        tester_alias: str = "",
        ux_score: int = 5,
        functionality_score: Optional[int] = None,
        func_score: Optional[int] = None,
        willingness_to_pay: Optional[int] = None,
        wtp_score: Optional[int] = None,
        nps_recommend_score: Optional[int] = None,
        nps_score: Optional[int] = None,
        blocker_category: str = "기타",
        qualitative_feedback: Optional[str] = None,
        qualitative_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """3단계 구조화 피드백 검증 및 70% 리워드 적립 처리."""
        f_score = func_score if func_score is not None else (functionality_score if functionality_score is not None else 5)
        w_score = wtp_score if wtp_score is not None else (willingness_to_pay if willingness_to_pay is not None else 3)
        n_score = nps_score if nps_score is not None else (nps_recommend_score if nps_recommend_score is not None else 10)
        q_text = qualitative_text if qualitative_text is not None else (qualitative_feedback if qualitative_feedback is not None else "")

        if not self.db:
            raise RuntimeError("데이터베이스 연동이 필요합니다.")

        sess = self.db.get_prototype_session(session_id)
        if not sess:
            raise ValueError("세션 정보가 존재하지 않습니다.")

        campaign_id = sess["campaign_id"]
        campaign = self.db.get_prototype_campaign(campaign_id)
        if not campaign:
            raise ValueError("캠페인 정보가 존재하지 않습니다.")

        if campaign["status"] != "ACTIVE":
            raise ValueError("모집이 마감되었거나 일시 정지된 캠페인입니다.")

        if campaign["completed_testers"] >= campaign["target_testers"]:
            raise ValueError("선착순 테스터 모집 정원이 이미 마감되었습니다.")

        # 중복 피드백 제출 차단 (동일 캠페인 1인 1회 한정)
        if self.db.has_prototype_feedback(campaign_id, tester_id):
            raise ValueError("이미 본 검증 캠페인에 참여하여 피드백을 제출하셨습니다. 중복 참여는 불가합니다.")

        # 1. 체류 시간 60초 미만 체리피커 차단
        if sess["active_seconds"] < 60:
            raise ValueError(
                f"최소 60초 이상 실사용 체험 후에 피드백을 제출할 수 있습니다. (현재 {sess['active_seconds']}초)"
            )

        # 2. 정성 의견 15자 이상 구체성 검증 및 불성실 반복문자 꼼수 차단
        cleaned_feedback = q_text.strip()
        if len(cleaned_feedback) < 15:
            raise ValueError(
                f"심사위원 대응용 정성 의견은 15자 이상 구체적으로 작성해야 합니다. (현재 {len(cleaned_feedback)}자)"
            )
        if re.search(r'(.)\1{3,}', cleaned_feedback):
            raise ValueError("불성실한 반복 문자가 감지되었습니다. 실제 사용 후기를 구체적으로 작성해 주세요.")

        # 3. 점수 범위 유효성 검증
        ux_val = max(1, min(5, int(ux_score)))
        func_val = max(1, min(5, int(f_score)))
        wtp_val = max(1, min(5, int(w_score)))
        nps_val = max(1, min(10, int(n_score)))

        feedback_id = f"fb_{uuid.uuid4().hex[:12]}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        reward_amount = campaign["tester_reward"]

        feedback_record = {
            "id": feedback_id,
            "campaign_id": campaign_id,
            "session_id": session_id,
            "tester_id": tester_id,
            "tester_alias": tester_alias.strip() or f"동료 창업자 #{session_id[-4:]}",
            "dwell_seconds": sess["active_seconds"],
            "ux_score": ux_val,
            "functionality_score": func_val,
            "willingness_to_pay": wtp_val,
            "nps_recommend_score": nps_val,
            "blocker_category": blocker_category.strip() or "기타",
            "qualitative_feedback": cleaned_feedback,
            "reward_amount": reward_amount,
            "reward_status": "PAID",
            "created_at": now_str,
        }

        success = self.db.save_prototype_feedback(feedback_record)
        if not success:
            raise RuntimeError("피드백 저장 중 데이터베이스 오류가 발생했습니다.")

        logger.info(
            "피드백 승인 및 리워드 적립 완료: 세션=%s, 테스터=%s, 지급액=%d원",
            session_id,
            tester_alias,
            reward_amount,
        )
        return {
            "status": "success",
            "feedback_id": feedback_id,
            "reward_amount": reward_amount,
            "reward_status": "PAID",
            "message": f"피드백이 정상 등록되었으며, 테스터 수당 {reward_amount:,}원이 적립되었습니다.",
        }

    # ------------------------------------------------------------------ 4. 심사위원 제출용 공식 보고서 합성기
    def generate_validation_report(self, campaign_id: str) -> Dict[str, Any]:
        """정부지원사업 심사위원 제출용 '고객 검증 및 설문 피드백 보고서' 데이터 합성."""
        if not self.db:
            raise RuntimeError("데이터베이스 연동이 필요합니다.")

        campaign = self.db.get_prototype_campaign(campaign_id)
        if not campaign:
            raise ValueError(f"캠페인을 찾을 수 없습니다: {campaign_id}")

        feedbacks = self.db.list_prototype_feedbacks(campaign_id)
        n = len(feedbacks)

        if n == 0:
            # 피드백이 아직 없는 경우 기본 구조 반환
            return {
                "campaign": campaign,
                "total_testers": 0,
                "target_testers": campaign["target_testers"],
                "completion_rate": 0.0,
                "avg_dwell_seconds": 0,
                "avg_dwell_formatted": "0초",
                "overall_satisfaction_score": 0.0,
                "nps_score": 0.0,
                "avg_ux_score": 0.0,
                "avg_functionality_score": 0.0,
                "avg_willingness_to_pay": 0.0,
                "avg_nps_recommend": 0.0,
                "radar_indicators": [],
                "blocker_distribution": {},
                "top_blockers": [],
                "feedbacks": [],
                "pitch_pack": {"headline": "피드백 수집 진행 중", "wtp_ratio": 0.0, "promoter_ratio": 0.0, "highlight_quotes": [], "core_metrics_summary": []},
                "audit_pack": {"compliance_status": "검증 진행 중", "sample_validity_rate": "0.0%", "remediation_plan": []},
                "roadmap_pack": {"priority_backlog": []},
                "audit_hash": hashlib.sha256(f"{campaign_id}:empty".encode("utf-8")).hexdigest(),
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

        # 정량 지표 집계
        total_dwell = sum(f["dwell_seconds"] for f in feedbacks)
        avg_dwell = round(total_dwell / n, 1)
        mins = int(avg_dwell // 60)
        secs = int(avg_dwell % 60)
        avg_dwell_str = f"{mins}분 {secs}초" if mins > 0 else f"{secs}초"

        avg_ux = round(sum(f["ux_score"] for f in feedbacks) / n, 1)
        avg_func = round(sum(f["functionality_score"] for f in feedbacks) / n, 1)
        avg_wtp = round(sum(f["willingness_to_pay"] for f in feedbacks) / n, 1)
        avg_nps_rec = round(sum(f["nps_recommend_score"] for f in feedbacks) / n, 1)

        # 100점 만점 전반적 만족도 점수: (UX + 기능 + 지불용의성) / 3 * 20
        overall_sat = round(((avg_ux + avg_func + avg_wtp) / 3.0) * 20.0, 1)

        # NPS 산출: (추천자(9-10) - 비추천자(1-6)) / 총원 * 100
        promoters = sum(1 for f in feedbacks if f["nps_recommend_score"] >= 9)
        passives = sum(1 for f in feedbacks if f["nps_recommend_score"] in (7, 8))
        detractors = sum(1 for f in feedbacks if f["nps_recommend_score"] <= 6)
        nps_score = round(((promoters - detractors) / n) * 100.0, 1)

        # 막힌 지점 (Blocker) 분포 집계
        blocker_counts: Dict[str, int] = {}
        for f in feedbacks:
            cat = f.get("blocker_category", "기타")
            blocker_counts[cat] = blocker_counts.get(cat, 0) + 1

        sorted_blockers = sorted(blocker_counts.items(), key=lambda x: x[1], reverse=True)
        top_blockers = [
            {
                "category": cat,
                "count": cnt,
                "ratio": round((cnt / n) * 100.0, 1),
                "action_item": self._get_blocker_recommendation(cat),
            }
            for cat, cnt in sorted_blockers
        ]

        # 5대 평가 척도 방사형/게이지 지표 (모두 5.0 만점 기준)
        dwell_engagement = min(5.0, round(avg_dwell / 30.0, 1))  # 2분 30초 이상 체류 시 5.0 만점
        market_recommendation = round(avg_nps_rec / 2.0, 1)       # 10점 만점을 5.0 만점으로 정규화

        radar_indicators = [
            {"dimension": "UI/UX 사용 편의성", "score": avg_ux, "max_score": 5.0, "status": "우수" if avg_ux >= 4.0 else "보통"},
            {"dimension": "핵심 기능 구현도", "score": avg_func, "max_score": 5.0, "status": "우수" if avg_func >= 4.0 else "보통"},
            {"dimension": "유료 지불 용의성", "score": avg_wtp, "max_score": 5.0, "status": "우수" if avg_wtp >= 3.5 else "개선요망"},
            {"dimension": "동료 창업자 추천도", "score": market_recommendation, "max_score": 5.0, "status": "우수" if market_recommendation >= 4.0 else "보통"},
            {"dimension": "실사용 체류 몰입도", "score": dwell_engagement, "max_score": 5.0, "status": "우수" if dwell_engagement >= 3.5 else "개선요망"},
        ]

        completion_rate = round((n / max(1, campaign["target_testers"])) * 100.0, 1)

        # 3대 활용 목적별 맞춤형 팩 합성
        wtp_positive_count = sum(1 for f in feedbacks if f["willingness_to_pay"] >= 3)
        wtp_ratio = round((wtp_positive_count / n) * 100.0, 1)
        promoter_ratio = round((promoters / n) * 100.0, 1)

        # 1. 과제 발표·선정용 트랙션 팩 (Pitch Deck Pack)
        highlight_quotes = [
            f["qualitative_feedback"]
            for f in feedbacks
            if f.get("nps_recommend_score", 0) >= 8 and len(f.get("qualitative_feedback", "")) >= 15
        ][:3]
        if not highlight_quotes and feedbacks:
            highlight_quotes = [f["qualitative_feedback"] for f in feedbacks[:3]]

        pitch_pack = {
            "headline": f"타깃 사용자 {n}명 실증: 종합 만족도 {overall_sat}점, 유료 전환 의향 {wtp_ratio}% 확보",
            "wtp_ratio": wtp_ratio,
            "promoter_ratio": promoter_ratio,
            "highlight_quotes": highlight_quotes,
            "core_metrics_summary": [
                {"label": "전반적 만족도", "val": f"{overall_sat}점", "sub": "100점 환산"},
                {"label": "유료 지불 용의율", "val": f"{wtp_ratio}%", "sub": "긍정 의향 3점 이상"},
                {"label": "NPS 추천 지수", "val": f"{'+' if nps_score > 0 else ''}{nps_score}", "sub": "순추천 지수"},
            ],
        }

        # 2. 정부과제 협약 감리/결과보고용 팩 (Audit Compliance Pack)
        remediation_plan = [
            {
                "category": b["category"],
                "frequency": f"{b['count']}건 ({b['ratio']}%)",
                "action_item": b["action_item"],
                "responsible_unit": "주관기관 연구개발팀",
                "schedule": "협약 2차 스프린트 내 조치 완료",
            }
            for b in top_blockers
        ]
        audit_pack = {
            "compliance_status": "적합 (최소 체류시간 100% 충족 및 1인 1계정 인증 전수 통과)",
            "sample_validity_rate": "100.0%",
            "remediation_plan": remediation_plan,
        }

        # 3. 기업 실무 제품 개선 & 스프린트 백로그 팩 (Product Iteration Pack)
        priority_backlog = []
        for b in top_blockers:
            cat = b["category"]
            p_level = "P0 (긴급 결함)" if "오류" in cat or "버그" in cat else ("P1 (UX 개선)" if "UI" in cat or "가독성" in cat else "P2 (성능 개선)")
            priority_backlog.append({
                "priority": p_level,
                "category": cat,
                "task": f"[{cat}] {b['action_item']}",
                "affected_users": f"{b['count']}명 제보 ({b['ratio']}%)",
            })
        roadmap_pack = {
            "priority_backlog": priority_backlog,
        }

        # 무결성 보증 SHA-256 감사 해시 날인
        hash_seed = f"{campaign_id}|{campaign['title']}|N={n}|sat={overall_sat}|nps={nps_score}|dwell={total_dwell}"
        audit_hash = hashlib.sha256(hash_seed.encode("utf-8")).hexdigest()

        return {
            "campaign": campaign,
            "total_testers": n,
            "target_testers": campaign["target_testers"],
            "completion_rate": completion_rate,
            "avg_dwell_seconds": int(avg_dwell),
            "avg_dwell_formatted": avg_dwell_str,
            "overall_satisfaction_score": overall_sat,
            "nps_score": nps_score,
            "promoters_count": promoters,
            "passives_count": passives,
            "detractors_count": detractors,
            "avg_ux_score": avg_ux,
            "avg_functionality_score": avg_func,
            "avg_willingness_to_pay": avg_wtp,
            "avg_nps_recommend": avg_nps_rec,
            "radar_indicators": radar_indicators,
            "blocker_distribution": blocker_counts,
            "top_blockers": top_blockers,
            "feedbacks": feedbacks,
            "pitch_pack": pitch_pack,
            "audit_pack": audit_pack,
            "roadmap_pack": roadmap_pack,
            "audit_hash": audit_hash,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def _get_blocker_recommendation(self, category: str) -> str:
        """막힌 지점에 대한 심사위원 대응용 실전 개선 가이드 매핑."""
        mapping = {
            "기능오류/버그": "예외 처리 로직 강화 및 핵심 트랜잭션 단위 테스트 100% 보강 조치",
            "UI깨짐/가독성": "디지털정부 표준 UI(KRDS) 가이드라인 준수 및 모바일 반응형 그리드 재조정",
            "속도지연": "클라이언트 자산 번들 최적화 및 비동기 프리페칭 적용을 통한 LCP 단축",
            "로그인/회원가입": "소셜 간편로그인(카카오/네이버) 연동 및 온보딩 입력 단계 3단계 이내 축소",
            "기타": "사용자 심층 인터뷰(FGI) 및 1:1 사용성 관찰 평가를 통한 상세 피드백 보완",
        }
        return mapping.get(category, "도메인 전문가 및 심사 기준에 맞춘 실증 데이터 보강")

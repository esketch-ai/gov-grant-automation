"""Tests for Native Vibe-Coding Validation Engine and 7:3 Feedback Reward Economy (REQ-047)."""

import pytest
from fastapi.testclient import TestClient
from src.prototype.validation_engine import PrototypeValidationEngine
from src.common.db import GrantDatabase
from src.web.app import app


@pytest.fixture
def temp_db(tmp_path):
    """Isolated temporary SQLite database."""
    db_file = tmp_path / "test_prototype.db"
    db = GrantDatabase(str(db_file))
    db.ensure_schema()
    return db


@pytest.fixture
def engine(temp_db):
    """Validation engine instance with isolated temp db."""
    return PrototypeValidationEngine(db=temp_db)


@pytest.fixture
def client():
    """FastAPI TestClient with subscriber cookies."""
    return TestClient(app, cookies={"sshai_role": "subscriber"})


class TestPrototypeValidationEngine:
    def test_70_30_economic_split_calculation(self, engine):
        """Verify exact 70% tester reward and 30% platform fee calculation."""
        split_2000 = engine.calculate_split(fee_per_tester=2000, target_testers=50)
        assert split_2000["total_budget"] == 100000
        assert split_2000["tester_reward_total"] == 70000
        assert split_2000["platform_fee_total"] == 30000
        assert split_2000["tester_reward_per_unit"] == 1400
        assert split_2000["platform_fee_per_unit"] == 600
        assert split_2000["tester_reward_pct"] == 70.0
        assert split_2000["platform_fee_pct"] == 30.0

        # Custom unit test
        split_5000 = engine.calculate_split(fee_per_tester=5000, target_testers=10)
        assert split_5000["total_budget"] == 50000
        assert split_5000["tester_reward_total"] == 35000
        assert split_5000["platform_fee_total"] == 15000
        assert split_5000["tester_reward_per_unit"] == 3500
        assert split_5000["platform_fee_per_unit"] == 1500

    def test_split_calculation_invalid_params(self, engine):
        """Verify validation errors on negative or too low fee/testers."""
        with pytest.raises(ValueError, match="100원 이상"):
            engine.calculate_split(fee_per_tester=50, target_testers=10)

        with pytest.raises(ValueError, match="최소 1명 이상"):
            engine.calculate_split(fee_per_tester=2000, target_testers=0)

    def test_campaign_lifecycle_and_creation(self, engine):
        """Verify campaign creation, budget validation, and listing."""
        camp = engine.create_campaign(
            item_id="item_bio_sensor",
            prototype_url="https://bio-sensor.preview.app",
            budget=100000,
            fee_per_tester=2000,
        )
        assert camp["id"].startswith("camp_")
        assert camp["item_id"] == "item_bio_sensor"
        assert camp["target_testers"] == 50
        assert camp["tester_reward"] == 1400
        assert camp["platform_fee"] == 600
        assert camp["status"] == "ACTIVE"

        # List campaigns
        active_list = engine.list_campaigns(status="ACTIVE")
        assert any(c["id"] == camp["id"] for c in active_list)

    def test_dwell_telemetry_and_cherry_picker_defense(self, engine):
        """Verify Page Visibility dwell tracking and 60-second threshold defense."""
        camp = engine.create_campaign(
            item_id="item_robotics",
            prototype_url="https://robotics.preview.app",
            budget=60000,
            fee_per_tester=2000,
        )

        # 1. Start session
        sess = engine.start_session(camp["id"], tester_id="tester_user_a")
        sess_id = sess["session_id"]
        assert sess_id.startswith("sess_")
        assert sess["dwell_active_seconds"] == 0

        # 2. Heartbeat below 60s
        hb1 = engine.record_heartbeat(sess_id, active_increment=25, visible_increment=25)
        assert hb1["active_seconds"] == 25
        assert hb1["status"] == "STARTED"

        # 3. Submit feedback before 60s -> Must be rejected by cherry-picker defense
        with pytest.raises(ValueError, match="최소 60초 이상"):
            engine.submit_feedback(
                session_id=sess_id,
                tester_id="tester_user_a",
                tester_alias="체리피커_방지_검증",
                ux_score=5,
                functionality_score=5,
                willingness_to_pay=4,
                nps_recommend_score=9,
                blocker_category="NONE",
                qualitative_feedback="초간단 테스트 피드백입니다. 60초 미만 차단 검증.",
            )

        # 4. Heartbeat reaching 65s (>= 60s threshold)
        hb2 = engine.record_heartbeat(sess_id, active_increment=40, visible_increment=40)
        assert hb2["active_seconds"] == 65
        assert hb2["status"] == "ENGAGED"

        # 5. Submit feedback with <15 chars -> Must be rejected
        with pytest.raises(ValueError, match="15자 이상"):
            engine.submit_feedback(
                session_id=sess_id,
                tester_id="tester_user_a",
                tester_alias="짧은리뷰어",
                ux_score=5,
                functionality_score=5,
                willingness_to_pay=4,
                nps_recommend_score=9,
                blocker_category="NONE",
                qualitative_feedback="너무좋아요!",
            )

        # 5-1. Submit feedback with repetitive spam characters -> Must be rejected
        with pytest.raises(ValueError, match="불성실한 반복 문자"):
            engine.submit_feedback(
                session_id=sess_id,
                tester_id="tester_user_a",
                tester_alias="도배러",
                ux_score=5,
                functionality_score=5,
                willingness_to_pay=4,
                nps_recommend_score=9,
                blocker_category="NONE",
                qualitative_feedback="정말최고네요ㅋㅋㅋㅋㅋㅋ이거좋아요!",
            )

        # 6. Submit valid feedback >= 60s and >= 15 chars -> Approved!
        res = engine.submit_feedback(
            session_id=sess_id,
            tester_id="tester_user_a",
            tester_alias="진성_창업자_테스터",
            ux_score=5,
            functionality_score=4,
            willingness_to_pay=4,
            nps_recommend_score=9,
            blocker_category="NONE",
            qualitative_feedback="온디바이스 환경에서 매우 직관적으로 반응하며 핵심 인터페이스가 훌륭합니다.",
        )
        assert res["status"] == "success"
        assert res["reward_amount"] == 1400
        assert res["reward_status"] == "PAID"

        # 7. Check tester reward summary
        rewards = engine.get_tester_rewards("tester_user_a")
        assert rewards["total_reward"] == 1400
        assert rewards["completed_count"] == 1

    def test_validation_report_generation_and_sha256_seal(self, engine):
        """Verify report calculation with NPS, 5 indicators, and SHA-256 seal."""
        camp = engine.create_campaign(
            item_id="item_report_test",
            prototype_url="https://report-test.preview.app",
            budget=200000,
            fee_per_tester=2000,
        )
        camp_id = camp["id"]

        # Insert 3 structured feedbacks
        for i, (score, blocker) in enumerate([(9, "기능오류/버그"), (10, "NONE"), (6, "UI깨짐/가독성")]):
            sess = engine.start_session(camp_id, tester_id=f"tester_{i}")
            engine.record_heartbeat(sess["session_id"], active_increment=75, visible_increment=75)
            engine.submit_feedback(
                session_id=sess["session_id"],
                tester_id=f"tester_{i}",
                tester_alias=f"테스터_{i}",
                ux_score=4,
                functionality_score=4,
                willingness_to_pay=3,
                nps_recommend_score=score,
                blocker_category=blocker,
                qualitative_feedback=f"프로토타입 검증 데이터 {i}번째 상세 정성 사용성 피드백 의견입니다.",
            )

        report = engine.generate_validation_report(camp_id)
        assert report["total_testers"] == 3
        assert report["target_testers"] == 100
        assert report["avg_dwell_seconds"] == 75
        assert report["avg_dwell_formatted"] == "1분 15초"
        assert len(report["radar_indicators"]) == 5
        assert len(report["top_blockers"]) >= 2

        # NPS check: 2 promoters (9, 10), 0 passives, 1 detractor (6) -> (2 - 1) / 3 * 100 = 33.3%
        assert report["promoters_count"] == 2
        assert report["detractors_count"] == 1
        assert report["nps_score"] == pytest.approx(33.3, abs=0.2)

        # Audit hash check: valid 64-char hex string
        assert len(report["audit_hash"]) == 64
        int(report["audit_hash"], 16)  # must not raise ValueError

        # Verify 3 systematized report packs (REQ: 과제 발표, 협약 감리, 실무 고도화)
        assert "pitch_pack" in report
        assert "headline" in report["pitch_pack"]
        assert report["pitch_pack"]["wtp_ratio"] > 0
        assert len(report["pitch_pack"]["highlight_quotes"]) >= 1
        assert len(report["pitch_pack"]["core_metrics_summary"]) == 3

        assert "audit_pack" in report
        assert "적합" in report["audit_pack"]["compliance_status"]
        assert report["audit_pack"]["sample_validity_rate"] == "100.0%"
        assert len(report["audit_pack"]["remediation_plan"]) >= 2

        assert "roadmap_pack" in report
        assert len(report["roadmap_pack"]["priority_backlog"]) >= 2
        assert any("P0" in b["priority"] or "P1" in b["priority"] for b in report["roadmap_pack"]["priority_backlog"])


class TestPrototypeWebAPIs:
    def test_api_create_campaign(self, client):
        """POST /api/prototype/campaigns creates campaign and returns JSON."""
        payload = {
            "item_id": "item_api_test",
            "prototype_url": "https://api-test.vibecoding.app",
            "budget": 100000,
            "fee_per_tester": 2000,
        }
        res = client.post("/api/prototype/campaigns", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "campaign" in data
        assert data["campaign"]["target_testers"] == 50
        assert data["campaign"]["tester_reward"] == 1400

    def test_api_list_campaigns(self, client):
        """GET /api/prototype/campaigns lists active campaigns."""
        res = client.get("/api/prototype/campaigns")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert isinstance(data["campaigns"], list)

    def test_api_session_and_dwell_lifecycle(self, client):
        """POST session start, heartbeat, and feedback submission via REST API."""
        # Create campaign first
        c_res = client.post(
            "/api/prototype/campaigns",
            json={
                "item_id": "item_flow_test",
                "prototype_url": "https://flow-test.vibecoding.app",
                "budget": 60000,
            },
        )
        assert c_res.status_code == 200
        camp_id = c_res.json()["campaign"]["id"]

        # 1. Start session
        s_res = client.post(
            "/api/prototype/sessions/start",
            json={"campaign_id": camp_id, "tester_id": "api_tester_01"},
        )
        assert s_res.status_code == 200
        sess_id = s_res.json()["session_id"]

        # 2. Premature feedback (<60s) -> 400 Bad Request
        fb_fail = client.post(
            "/api/prototype/feedback/submit",
            json={
                "campaign_id": camp_id,
                "session_id": sess_id,
                "tester_id": "api_tester_01",
                "ux_score": 4,
                "func_score": 4,
                "wtp_score": 3,
                "nps_score": 9,
                "qualitative_text": "아직 60초가 안 지났는데 제출을 시도합니다.",
                "blocker_category": "NONE",
            },
        )
        assert fb_fail.status_code == 400
        assert "최소 60초 이상" in fb_fail.json()["message"]

        # 3. Heartbeat to 65s
        hb_res = client.post(
            "/api/prototype/sessions/heartbeat",
            json={"session_id": sess_id, "active_increment": 65, "visible_increment": 65},
        )
        assert hb_res.status_code == 200
        assert hb_res.json()["active_seconds"] == 65

        # 4. Valid feedback submission
        fb_ok = client.post(
            "/api/prototype/feedback/submit",
            json={
                "campaign_id": camp_id,
                "session_id": sess_id,
                "tester_id": "api_tester_01",
                "ux_score": 5,
                "func_score": 5,
                "wtp_score": 4,
                "nps_score": 10,
                "qualitative_text": "실제 서비스처럼 반응 속도가 매우 우수하고 UI 구성이 매력적입니다.",
                "blocker_category": "NONE",
            },
        )
        assert fb_ok.status_code == 200
        assert fb_ok.json()["status"] == "success"

        # 5. Fetch report JSON
        rep_res = client.get(f"/api/prototype/reports/{camp_id}")
        assert rep_res.status_code == 200
        rep_data = rep_res.json()["report"]
        assert rep_data["total_testers"] == 1
        assert rep_data["nps_score"] == 100.0
        assert len(rep_data["audit_hash"]) == 64

        # 6. Fetch HTML report view
        html_res = client.get(f"/prototype/report/{camp_id}")
        assert html_res.status_code == 200
        assert "기획·웹·앱 실사용자 피드백 &amp; 설문 검증 보고서" in html_res.text
        assert "SHA-256 SEAL" in html_res.text
        assert "kh-page-hero" in html_res.text
        assert "모드 1: 과제 발표·선정용" in html_res.text
        assert "모드 2: 협약 감리·결과보고용" in html_res.text
        assert "모드 3: 실무 제품 개선 로드맵" in html_res.text
        assert "전수 데이터 CSV" in html_res.text
        assert "발표 요약 복사" in html_res.text

    def test_intro_page_includes_public_prototype_lounge(self, client):
        """GET /intro renders the public prototype lounge and tester modal for all visitors."""
        res = client.get("/intro")
        assert res.status_code == 200
        assert "prototype-lounge" in res.text
        assert "동료 창업자 기획·웹·앱 체험 &amp; 피드백 라운지" in res.text
        assert "피드백" in res.text
        assert "testerModal" in res.text
        assert "나의 테스터 수당 현황" in res.text
        assert "참여 테스터 리워드 지급" in res.text

    def test_biz_dashboard_includes_prototype_lounge(self, client):
        """GET /dashboard/biz renders the business prototype validation card and link to feedback lounge."""
        res = client.get("/dashboard/biz")
        assert res.status_code == 200
        assert "내 기획·웹·앱 실사용자 피드백 & 설문 보고서" in res.text
        assert "/feedback-lounge" in res.text
        assert "/items" in res.text

    def test_items_page_includes_prototype_url_and_campaign_modal(self, client):
        """GET /items renders prototype URL inputs and campaign creation modal."""
        res = client.get("/items")
        assert res.status_code == 200
        assert "기획안 / 웹 / 앱 프로토타입 URL" in res.text
        assert "campaignModal" in res.text
        assert "참여 테스터 리워드 정산 체계" in res.text

    def test_standalone_feedback_lounge_page(self, client):
        """GET /feedback-lounge renders the standalone menu service with dual track filters."""
        res = client.get("/feedback-lounge")
        assert res.status_code == 200
        assert "동료 창업자 기획·웹·앱 체험 &amp; 피드백 라운지" in res.text
        assert "유료 보증 검증" in res.text
        assert "무료 커뮤니티 품앗이" in res.text
        assert "registrationModal" in res.text
        assert "testerModal" in res.text

    def test_free_vs_paid_campaign_dual_track_creation(self, client):
        """POST /api/prototype/campaigns supports both FREE and PAID registration tracks."""
        # 1. Free track: 0 budget, 0 fee, immediate registration
        free_res = client.post(
            "/api/prototype/campaigns",
            json={
                "item_id": "free_track_test",
                "prototype_url": "https://figma.com/demo-free",
                "title": "무료 커뮤니티 품앗이 기획안",
                "request_type": "FREE",
                "category": "로컬/F&B",
                "target_testers": 10,
            },
        )
        assert free_res.status_code == 200
        free_camp = free_res.json()["campaign"]
        assert free_camp["request_type"] == "FREE"
        assert free_camp["total_budget"] == 0
        assert free_camp["tester_reward"] == 0
        assert free_camp["target_testers"] == 10
        assert free_camp["status"] == "ACTIVE"

        # 2. Paid track: target testers, budget calculation, guaranteed reward
        paid_res = client.post(
            "/api/prototype/campaigns",
            json={
                "item_id": "paid_track_test",
                "prototype_url": "https://paid-app.com",
                "title": "유료 보증 검증 앱",
                "request_type": "PAID",
                "category": "AI/딥테크",
                "budget": 100000,
            },
        )
        assert paid_res.status_code == 200
        paid_camp = paid_res.json()["campaign"]
        assert paid_camp["request_type"] == "PAID"
        assert paid_camp["total_budget"] == 100000
        assert paid_camp["tester_reward"] == 1400
        assert paid_camp["target_testers"] == 50
        assert paid_camp["status"] == "ACTIVE"

    def test_anti_duplicate_validation_enforcement(self, client):
        """동일 인증 사용자의 동일 캠페인 중복 참여 원천 차단 검증."""
        # 1. 새 캠페인 생성
        c_res = client.post(
            "/api/prototype/campaigns",
            json={
                "item_id": "dup_test_item",
                "prototype_url": "https://dup-test.app",
                "title": "중복 방지 테스트 캠페인",
                "request_type": "PAID",
                "budget": 60000,
            },
        )
        assert c_res.status_code == 200
        camp_id = c_res.json()["campaign"]["id"]

        # 2. 테스터 1차 정상 참여
        tester_id = "kakao_user_unique_999"
        s1 = client.post(
            "/api/prototype/sessions/start",
            json={"campaign_id": camp_id, "tester_id": tester_id},
        )
        assert s1.status_code == 200
        sess1_id = s1.json()["session_id"]

        client.post(
            "/api/prototype/sessions/heartbeat",
            json={"session_id": sess1_id, "active_increment": 65, "visible_increment": 65},
        )

        fb1 = client.post(
            "/api/prototype/feedback/submit",
            json={
                "campaign_id": camp_id,
                "session_id": sess1_id,
                "tester_id": tester_id,
                "ux_score": 5,
                "func_score": 5,
                "wtp_score": 4,
                "nps_score": 10,
                "qualitative_text": "첫 번째 정상적인 피드백 제출입니다. 매우 훌륭합니다.",
                "blocker_category": "NONE",
            },
        )
        assert fb1.status_code == 200
        assert fb1.json()["status"] == "success"

        # 3. 동일 테스터가 재참여(세션 시작) 시도 시 즉시 차단
        s2 = client.post(
            "/api/prototype/sessions/start",
            json={"campaign_id": camp_id, "tester_id": tester_id},
        )
        assert s2.status_code == 400
        assert "중복 참여는 불가" in s2.json()["message"]

        # 4. 다른 테스터는 정상 참여 가능
        diff_tester = "naver_user_diff_888"
        s_diff = client.post(
            "/api/prototype/sessions/start",
            json={"campaign_id": camp_id, "tester_id": diff_tester},
        )
        assert s_diff.status_code == 200

    def test_feedback_lounge_phase1_smart_search_and_pagination_ui(self, client):
        """Phase 1: 피드백 라운지 실시간 키워드 검색, 카테고리 퀵 칩, 점진적 로딩(+18개) UI 검증."""
        res = client.get("/feedback-lounge")
        assert res.status_code == 200
        # 실시간 검색창 및 칩
        assert "loungeSearchInput" in res.text
        assert "handleLoungeSearch" in res.text
        assert "clearLoungeSearch" in res.text
        assert "filteredCountBadge" in res.text
        assert "category-chip" in res.text
        assert "AI·딥테크" in res.text or "AI/딥테크" in res.text
        # 점진적 로딩(+18) 및 완료 뱃지
        assert "loadMoreContainer" in res.text
        assert "btnLoadMoreLounge" in res.text
        assert "loadMoreLoungeCards" in res.text
        assert "testedBadge-" in res.text

    def test_feedback_lounge_phase2_pulse_indicator_and_toast_ui(self, client):
        """Phase 2: 체험 모달 3단계 가이드, 실시간 펄스 인디케이터, 활동 프로그레스 바, 토스트 알림 검증."""
        res = client.get("/feedback-lounge")
        assert res.status_code == 200
        assert "stepGuide1" in res.text
        assert "stepGuide2" in res.text
        assert "stepGuide3" in res.text
        assert "dwellPulseRing" in res.text
        assert "dwellProgressBar" in res.text
        assert "loungeToast" in res.text
        assert "showLoungeToast" in res.text

    def test_biz_dashboard_phase3_25_point_preflight_modal_and_print(self, client):
        """Phase 3: 사업자 대시보드 25대 법정 결격사유 사전 자격 진단 명세서 모달 및 인쇄/PDF 검증."""
        res = client.get("/dashboard/biz")
        assert res.status_code == 200
        # 25대 신호등 트리거 버튼
        assert "openPreflightModal" in res.text
        assert "25대 지원 결격 사유 0건" in res.text
        # 모달 및 전수 25개 항목
        assert "preflightModal" in res.text
        assert "2026 정부지원사업 25대 법정 결격사유 사전 자격 진단 명세서" in res.text
        assert "SSA Gov-Preflight Engine" in res.text
        assert "국세 기본법 제29조" in res.text
        assert "지방세 징수법 제30조" in res.text
        assert "4대 사회보험료" in res.text
        assert "전국은행연합회 신용정보관리규약" in res.text
        assert "국가연구개발혁신법 제32조" in res.text
        assert "3책 5공 규정" in res.text
        assert "중소기업기본법 제2조" in res.text
        assert "printPreflightReport" in res.text
        assert "@media print" in res.text

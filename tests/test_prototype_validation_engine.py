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
        assert "고객 검증 및 실사용 피드백 보고서" in html_res.text
        assert "SHA-256 SEAL" in html_res.text
        assert "kh-page-hero" in html_res.text

    def test_intro_page_includes_public_prototype_lounge(self, client):
        """GET /intro renders the public prototype lounge and tester modal for all visitors."""
        res = client.get("/intro")
        assert res.status_code == 200
        assert "prototype-lounge" in res.text
        assert "동료 창업자 바이브코딩 프로토타입 체험" in res.text
        assert "7:3 피드백 리워드 라운지" in res.text
        assert "testerModal" in res.text
        assert "나의 테스터 수당 현황" in res.text
        assert "건당 70% 리워드 즉시 정산" in res.text

    def test_biz_dashboard_includes_prototype_lounge(self, client):
        """GET /dashboard/biz renders the business prototype validation card and link to intro lounge."""
        res = client.get("/dashboard/biz")
        assert res.status_code == 200
        assert "AI 바이브코딩 프로토타입 고객 실증 및 심사위원 검증" in res.text
        assert "/intro#prototype-lounge" in res.text
        assert "/items" in res.text

    def test_items_page_includes_prototype_url_and_campaign_modal(self, client):
        """GET /items renders prototype URL inputs and campaign creation modal."""
        res = client.get("/items")
        assert res.status_code == 200
        assert "AI 바이브코딩 프로토타입 URL" in res.text
        assert "campaignModal" in res.text
        assert "7:3 피드백 리워드 정산 체계" in res.text

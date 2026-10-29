"""
tests/test_feedback_lounge_dual_track.py
REQ-050: 동료 창업자 피드백 라운지 독립 메뉴 서비스화, 무료/유료 듀얼 트랙,
소셜 계정 연계 리워드 지급 및 3대 목적별 결과 보고서 체계화 검증 스위트.
"""
import pytest
from fastapi.testclient import TestClient

from src.common.db import GrantDatabase
from src.prototype.validation_engine import PrototypeValidationEngine
from src.web.app import app


@pytest.fixture
def temp_db(tmp_path):
    """Isolated temporary SQLite database."""
    db_file = tmp_path / "test_req050_lounge.db"
    db = GrantDatabase(str(db_file))
    db.ensure_schema()
    return db


@pytest.fixture
def engine(temp_db):
    """PrototypeValidationEngine with isolated temp db."""
    return PrototypeValidationEngine(db=temp_db)


@pytest.fixture
def client():
    """FastAPI TestClient with subscriber cookies."""
    return TestClient(app, cookies={"sshai_role": "subscriber"})


def test_feedback_lounge_rendering_and_tabs(client):
    """REQ-050 1. 독립 피드백 라운지 화면 렌더링, 4대 통계 카드 및 듀얼 트랙 탭 검증."""
    res = client.get("/feedback-lounge")
    assert res.status_code == 200
    assert "kh-page-hero" in res.text
    assert "동료 창업자 기획·웹·앱 체험 &amp; 피드백 라운지" in res.text
    assert "유료 보증 검증" in res.text
    assert "무료 커뮤니티 품앗이" in res.text
    assert "registrationModal" in res.text
    assert "testerModal" in res.text
    assert "참여 테스터 리워드" in res.text


def test_dual_track_campaign_filtration_api(client):
    """REQ-050 2. 유료(PAID) vs 무료(FREE) 듀얼 트랙 캠페인 개설 및 필터링 API 검증."""
    # 1. 무료 품앗이 캠페인 생성
    res_free = client.post(
        "/api/prototype/campaigns",
        json={
            "item_id": "item_dual_free",
            "prototype_url": "https://free-proto.test",
            "title": "무료 품앗이 UI 시안",
            "request_type": "FREE",
            "target_testers": 15,
        },
    )
    assert res_free.status_code == 200
    camp_free = res_free.json()["campaign"]
    assert camp_free["request_type"] == "FREE"
    assert camp_free["total_budget"] == 0
    assert camp_free["tester_reward"] == 0

    # 2. 유료 보증 검증 캠페인 생성
    res_paid = client.post(
        "/api/prototype/campaigns",
        json={
            "item_id": "item_dual_paid",
            "prototype_url": "https://paid-proto.test",
            "title": "유료 보증 검증 실증 앱",
            "request_type": "PAID",
            "budget": 100000,
        },
    )
    assert res_paid.status_code == 200
    camp_paid = res_paid.json()["campaign"]
    assert camp_paid["request_type"] == "PAID"
    assert camp_paid["tester_reward"] == 1400

    # 3. 트랙별 목록 조회
    list_res = client.get("/api/prototype/campaigns")
    assert list_res.status_code == 200
    all_camps = list_res.json()["campaigns"]
    assert any(c["id"] == camp_free["id"] and c["request_type"] == "FREE" for c in all_camps)
    assert any(c["id"] == camp_paid["id"] and c["request_type"] == "PAID" for c in all_camps)


def test_validation_engine_3packs_synthesis(engine):
    """REQ-050 3. 3대 목적별 보고서 팩(pitch_pack, audit_pack, roadmap_pack) 데이터 합성 엔진 검증."""
    camp = engine.create_campaign(
        item_id="item_pack_test",
        prototype_url="https://pack-test.preview",
        title="3대 팩 검증 프로젝트",
        budget=100000,
    )
    camp_id = camp["id"]

    # 3건의 구조화 피드백 주입
    for i, (score, blocker) in enumerate([(9, "기능오류/버그"), (10, "NONE"), (5, "속도지연")]):
        s = engine.start_session(camp_id, tester_id=f"tester_pack_{i}")
        engine.record_heartbeat(s["session_id"], active_increment=70, visible_increment=70)
        engine.submit_feedback(
            session_id=s["session_id"],
            tester_id=f"tester_pack_{i}",
            tester_alias=f"테스터_{i}",
            ux_score=4,
            functionality_score=4,
            willingness_to_pay=4,
            nps_recommend_score=score,
            blocker_category=blocker,
            qualitative_feedback=f"피드백 라운지 3대 목적별 리포트 팩 합성 테스트 의견 {i}번째입니다.",
        )

    report = engine.generate_validation_report(camp_id)

    # 1) pitch_pack: 발표·선정용
    assert "pitch_pack" in report
    p_pack = report["pitch_pack"]
    assert "headline" in p_pack
    assert p_pack["wtp_ratio"] > 0
    assert len(p_pack["highlight_quotes"]) >= 1
    assert len(p_pack["core_metrics_summary"]) == 3

    # 2) audit_pack: 협약 감리·결과보고용
    assert "audit_pack" in report
    a_pack = report["audit_pack"]
    assert "적합" in a_pack["compliance_status"]
    assert a_pack["sample_validity_rate"] == "100.0%"
    assert len(a_pack["remediation_plan"]) >= 2
    for rem in a_pack["remediation_plan"]:
        assert "responsible_unit" in rem
        assert "schedule" in rem

    # 3) roadmap_pack: 실무 로드맵
    assert "roadmap_pack" in report
    r_pack = report["roadmap_pack"]
    assert len(r_pack["priority_backlog"]) >= 2
    assert any("P0" in b["priority"] or "P1" in b["priority"] for b in r_pack["priority_backlog"])


def test_anti_duplicate_and_unique_constraint(engine):
    """REQ-050 4. DB 수준 1인 1검증 중복 차단 및 UNIQUE 제약 무결성 검증."""
    camp = engine.create_campaign(
        item_id="item_dup_guard",
        prototype_url="https://dup-guard.preview",
        title="중복 방지 캠페인",
        budget=60000,
    )
    camp_id = camp["id"]
    tester_id = "oauth_kakao_123456"

    # 1. 최초 참여 전에는 중복 아님
    assert not engine.db.has_prototype_feedback(camp_id, tester_id)

    # 2. 첫 세션 및 피드백 완료
    s1 = engine.start_session(camp_id, tester_id=tester_id)
    engine.record_heartbeat(s1["session_id"], active_increment=65, visible_increment=65)
    res = engine.submit_feedback(
        session_id=s1["session_id"],
        tester_id=tester_id,
        tester_alias="정직한_테스터",
        ux_score=5,
        functionality_score=5,
        willingness_to_pay=4,
        nps_recommend_score=10,
        blocker_category="NONE",
        qualitative_feedback="정상적인 실사용 평가 피드백입니다. 중복 방지 제약 검증용.",
    )
    assert res["status"] == "success"

    # 3. 제출 후에는 중복으로 판정
    assert engine.db.has_prototype_feedback(camp_id, tester_id)

    # 4. 동일 테스터가 재참여 세션 시도 시 거절
    with pytest.raises(ValueError, match="중복 참여는 불가"):
        engine.start_session(camp_id, tester_id=tester_id)


def test_social_oauth_and_free_reward_handling(engine):
    """REQ-050 5. 무료 캠페인 0원 리워드 vs 유료 캠페인 수당 정산 및 소셜 계정 연계 검증."""
    # 1. 무료 캠페인
    c_free = engine.create_campaign(
        item_id="item_free_reward",
        prototype_url="https://free-share.preview",
        title="무료 품앗이 캠페인",
        budget=0,
        request_type="FREE",
    )
    s_free = engine.start_session(c_free["id"], tester_id="tester_free_user")
    engine.record_heartbeat(s_free["session_id"], active_increment=65, visible_increment=65)
    f_free = engine.submit_feedback(
        session_id=s_free["session_id"],
        tester_id="tester_free_user",
        tester_alias="품앗이_동료",
        ux_score=4,
        functionality_score=4,
        willingness_to_pay=3,
        nps_recommend_score=8,
        blocker_category="NONE",
        qualitative_feedback="커뮤니티 품앗이 피드백입니다. 리워드 0원과 품앗이 기여도 확인.",
    )
    assert f_free["status"] == "success"
    assert f_free["reward_amount"] == 0

    # 2. 유료 캠페인
    c_paid = engine.create_campaign(
        item_id="item_paid_reward",
        prototype_url="https://paid-guarantee.preview",
        title="유료 보증 캠페인",
        budget=100000,
        request_type="PAID",
    )
    s_paid = engine.start_session(c_paid["id"], tester_id="tester_paid_user")
    engine.record_heartbeat(s_paid["session_id"], active_increment=65, visible_increment=65)
    f_paid = engine.submit_feedback(
        session_id=s_paid["session_id"],
        tester_id="tester_paid_user",
        tester_alias="유료_검증단",
        ux_score=5,
        functionality_score=5,
        willingness_to_pay=5,
        nps_recommend_score=10,
        blocker_category="NONE",
        qualitative_feedback="보증 검증 실사용 피드백입니다. 1,400원 수당 정산 확인.",
    )
    assert f_paid["status"] == "success"
    assert f_paid["reward_amount"] == 1400

    # 3. 테스터별 리워드 정산 요약 확인
    summary_free = engine.get_tester_rewards("tester_free_user")
    assert summary_free["total_reward"] == 0
    assert summary_free["completed_count"] == 1

    summary_paid = engine.get_tester_rewards("tester_paid_user")
    assert summary_paid["total_reward"] == 1400
    assert summary_paid["completed_count"] == 1

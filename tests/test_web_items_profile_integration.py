"""
REQ-021 (사업 아이템 ↔ 기업 프로필 통합 및 상속) &
REQ-022 (사업계획서 파일 업로드 기반 AI 분석 및 Auto-fill) 웹 통합 테스트
"""
import io
import pytest
from starlette.testclient import TestClient
from src.web.app import app, PROJECT_ROOT, _get_db


@pytest.fixture
def client():
    return TestClient(app)


SAMPLE_PROPOSAL = """
[2026년도 농식품 스마트팜 육성지원사업 계획서]
과제명: AI 기반 지능형 스마트팜 온실 환경제어 시스템
기업명: (주)그린애그리
사업자등록번호: 312-85-12345
설립일: 2024년 05월 10일
대표자: 최민영
생년월일: 1996년 04월 12일
성별: 여성기업 인증
소재지: 전라남도 나주시 배향로 50
기업부설연구소: 보유 (제2024-4321호)
부채비율: 95.0%
등록특허: 2건
인증: 여성기업, 벤처기업
기술성숙도: TRL 6단계
개발 개요: IoT 센서와 강화학습 AI를 결합하여 온실 내 온도, 습도, CO2 농도를 자율 최적화하는 스마트팜 솔루션.
"""


def test_analyze_proposal_endpoint(client):
    """REQ-022: /api/items/analyze-proposal 파일 업로드 분석 검증."""
    file_bytes = SAMPLE_PROPOSAL.encode("utf-8")
    files = {"file": ("proposal_smartfarm.txt", io.BytesIO(file_bytes), "text/plain")}

    resp = client.post("/api/items/analyze-proposal", files=files)
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "success"
    assert data["filename"] == "proposal_smartfarm.txt"

    extracted = data["data"]
    item = extracted["item"]
    specs = extracted["company_specs"]

    assert "스마트팜" in item["name"] or "온실" in item["name"]
    assert item["trl"] == 6
    assert specs["company_name"] == "(주)그린애그리"
    assert specs["biz_reg_no"] == "312-85-12345"
    assert specs["founder_gender"] == "F"
    assert specs["has_rnd_lab"] is True
    assert specs["debt_ratio_pct"] == 95.0
    assert specs["registered_patents_count"] >= 2
    assert "여성기업" in specs["certifications"]
    assert "전라남도" in specs["address"] or "나주시" in specs["address"]


def test_items_crud_with_company_specs(client):
    """REQ-021: company_specs를 포함한 아이템 등록, 조회 및 수정 검증."""
    item_id = "test-item-smartfarm-ai"
    item_dir = PROJECT_ROOT / "items" / item_id

    # 사전 정리
    if item_dir.exists():
        import shutil
        shutil.rmtree(item_dir)

    payload = {
        "item_id": item_id,
        "name": "지능형 스마트팜 온실 제어기",
        "min_score": 80,
        "target_trl": "6",
        "keywords": "스마트팜, IoT, 인공지능, 온실",
        "recipients": "agri@greentech.kr",
        "proposal_text": "# 스마트팜 제안서\n\n지능형 환경제어 솔루션",
        "company_specs": {
            "company_name": "(주)그린애그리",
            "biz_reg_no": "312-85-12345",
            "opened_date": "2024-05-10",
            "founder_birth": "1996-04-12",
            "founder_gender": "F",
            "address": "전라남도 나주시 배향로 50",
            "debt_ratio_pct": 95.0,
            "has_rnd_lab": True,
            "registered_patents_count": 2,
            "certifications": ["여성기업", "벤처기업"],
        },
    }

    try:
        # 1. 생성
        res = client.post("/api/items", json=payload)
        assert res.status_code == 200
        assert res.json()["status"] == "success"

        # 디렉터리 및 파일 존재 확인
        assert item_dir.exists()
        assert (item_dir / "profile.yaml").exists()
        assert (item_dir / "proposal.md").exists()

        # 2. 목록 조회 시 배지 및 qualification 태그 정상 반영 확인
        get_res = client.get("/items")
        assert get_res.status_code == 200
        assert "지능형 스마트팜 온실 제어기" in get_res.text
        assert "여성기업" in get_res.text
        assert "만 39세 청년" in get_res.text
        assert "기업부설연구소" in get_res.text

        # 3. 수정
        payload["name"] = "지능형 스마트팜 온실 제어기 (고도화)"
        payload["company_specs"]["debt_ratio_pct"] = 80.0
        put_res = client.put(f"/api/items/{item_id}", json=payload)
        assert put_res.status_code == 200

    finally:
        # 사후 정리
        if item_dir.exists():
            import shutil
            shutil.rmtree(item_dir)


def test_simulate_match_api_includes_preflight(client):
    """REQ-021: 시뮬레이션 API 호출 시 Preflight additive 신호등 탑재 검증."""
    db = _get_db()
    db.ensure_schema()
    test_cid = "k_startup:sim_test_notice_01"

    # DB에 테스트용 2026 공고 1건 확보 (Ground Truth 유효한 딥링크 사용)
    with db._connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO announcements (canonical_id, source_portal, title, ministry, organization, deadline, detail_url, target_year) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (test_cid, "k_startup", "2026년도 여성특화 창업패키지 지원사업", "중소벤처기업부", "창업진흥원", "2026-11-30", "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=175783", 2026),
        )
        conn.commit()

    try:
        # 기존 아이템 하나 선택 (예: item_01)
        sim_payload = {
            "item_id": "item_01_carbon_dmrv",
            "canonical_id": test_cid,
        }
        resp = client.post("/api/matcher/simulate", json=sim_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"

        eval_data = data["evaluation"]
        assert "preflight" in eval_data, "evaluation에 preflight 신호등 진단 결과가 포함되어야 합니다."
        pf = eval_data["preflight"]
        assert "status" in pf  # GREEN / YELLOW / RED
        assert "final_score" in pf
    finally:
        with db._connect() as conn:
            conn.execute("DELETE FROM announcements WHERE canonical_id=?", (test_cid,))
            conn.commit()

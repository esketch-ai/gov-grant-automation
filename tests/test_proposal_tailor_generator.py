"""
tests/test_proposal_tailor_generator.py
DocuMorph AI - 과제별 사업계획서 맞춤 변환 및 코파일럿 생성 엔진 검증.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.generator.template_schemas import (
    ProposalTemplate,
    detect_template_for_announcement,
    get_all_templates,
    get_template,
)
from src.generator.gap_analyzer import ProposalGapAnalyzer
from src.generator.doc_morpher import DocMorpher
from src.web.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_template_schemas_registry():
    """PSST 및 R&D 표준 템플릿 등록 및 공고별 자동 감지 검증."""
    psst = get_template("PSST")
    assert psst.template_id == "PSST"
    assert len(psst.sections) == 8
    assert psst.sections[0].section_id == "1-1"
    assert len(psst.sections[0].guiding_questions) >= 2

    rnd = get_template("RND_SMTECH")
    assert rnd.template_id == "RND_SMTECH"
    assert len(rnd.sections) == 8
    assert any("KPI" in s.title or "성능" in s.title for s in rnd.sections)

    all_tpls = get_all_templates()
    assert len(all_tpls) >= 2

    # 공고명 기반 템플릿 자동 감지
    det_rnd = detect_template_for_announcement("2026년 중소기업 디딤돌 R&D 신규과제", "중소벤처기업부")
    assert det_rnd.template_id == "RND_SMTECH"

    det_psst = detect_template_for_announcement("2026년 예비창업패키지 창업기업 모집", "창업진흥원")
    assert det_psst.template_id == "PSST"


def test_gap_analyzer_logic():
    """마스터 계획서와 템플릿 간 갭 분석 및 준비도 산출 검증."""
    analyzer = ProposalGapAnalyzer()
    sample_item = {
        "id": "test_item",
        "name": "AI 기반 자동 통역 솔루션",
        "summary": "다국어 실시간 음성 번역 및 노이즈 캔슬링 딥러닝 모델",
        "keywords": ["인공지능", "실시간통역", "딥러닝", "음성인식"],
        "trl": 4,
        "company_specs": {
            "company_name": "(주)글로벌보이스",
            "rep_name": "홍길동",
            "opened_date": "2024-05-01",
            "employee_count": 3,
        },
        "proposal_text": "본 과제는 해외 바이어와의 실시간 회의 시 언어 장벽을 해결하기 위한 배경에서 출발하였습니다.",
    }

    psst = get_template("PSST")
    result = analyzer.analyze(sample_item, psst)

    assert result["template_id"] == "PSST"
    assert result["total_sections"] == 8
    assert result["readiness_score"] >= 30
    assert len(result["sections"]) == 8

    # 1-1 문항은 요약과 제안서 텍스트가 있으므로 DIRECT_FIT 또는 ADAPT_FIT
    sec_1_1 = next(s for s in result["sections"] if s["section_id"] == "1-1")
    assert sec_1_1["status"] in ["DIRECT_FIT", "ADAPT_FIT"]
    assert len(sec_1_1["guiding_questions"]) >= 1


def test_doc_morpher_section_generation_and_assembly():
    """코파일럿 팩트 기반 섹션 초안 합성 및 전체 문서 조립 검증."""
    morpher = DocMorpher()
    psst = get_template("PSST")
    sec_1_1 = psst.sections[0]

    sample_meta = {
        "name": "스마트 AI 진단기",
        "summary": "온디바이스 딥러닝 헬스케어 기기",
        "company_specs": {"company_name": "(주)스마트헬스", "rep_name": "김대표"},
    }

    user_facts = {
        "기존 시장 제품의 가장 치명적인 문제점은 무엇인가요?": "검사 결과 도출까지 3일이 소요되고 비용이 20만원으로 매우 비쌈",
    }

    draft = morpher.generate_section_draft_sync(
        section=sec_1_1,
        template=psst,
        master_context="마스터 계획서 원문 내용",
        user_facts=user_facts,
        item_meta=sample_meta,
    )

    assert "스마트 AI 진단기" in draft or "개발 배경" in draft
    assert "비용이 20만원" in draft or "페인포인트" in draft

    # 전체 계획서 문서 조립 검증
    full_doc = morpher.assemble_full_document(
        item_meta=sample_meta,
        template=psst,
        section_drafts={"1-1": draft},
    )
    assert "# K-Startup PSST 표준 창업사업계획서" in full_doc
    assert "(주)스마트헬스" in full_doc
    assert "### 1-1. 창업아이템의 개발 배경 및 필요성" in full_doc


def test_web_tailor_view_and_apis(client):
    """웹 화면(/proposals/tailor) 및 관련 API E2E 검증."""
    # 1. 화면 렌더링 검증
    resp = client.get("/proposals/tailor")
    assert resp.status_code == 200
    html = resp.text
    assert "사업계획서 맞춤 변환 & 코파일럿 스튜디오" in html
    assert "DocuMorph AI" in html
    assert "양식 준비도" in html
    assert "맞춤 초안 생성하기" in html

    # 2. 템플릿 목록 조회 API
    resp_tpl = client.get("/api/proposals/templates")
    assert resp_tpl.status_code == 200
    tpl_data = resp_tpl.json()
    assert tpl_data["status"] == "success"
    assert len(tpl_data["templates"]) >= 2

    # 3. 갭 분석 API
    resp_gap = client.post(
        "/api/proposals/gap-analysis",
        json={"item_id": "item_01_carbon_dmrv", "template_id": "PSST"},
    )
    assert resp_gap.status_code == 200
    gap_json = resp_gap.json()
    assert gap_json["status"] == "success"
    assert "readiness_score" in gap_json["gap_analysis"]

    # 4. 섹션 초안 생성 API
    resp_gen = client.post(
        "/api/proposals/generate-section",
        json={
            "item_id": "item_01_carbon_dmrv",
            "template_id": "PSST",
            "section_id": "1-1",
            "user_facts": {"질문1": "기존 탄소배출권 인증 비용이 건당 5,000만원으로 과다함"},
        },
    )
    assert resp_gen.status_code == 200
    gen_json = resp_gen.json()
    assert gen_json["status"] == "success"
    assert gen_json["section_id"] == "1-1"
    assert len(gen_json["draft"]) >= 50

    # 5. 전체 문서 내보내기 API
    resp_exp = client.post(
        "/api/proposals/export",
        json={
            "item_id": "item_01_carbon_dmrv",
            "template_id": "PSST",
            "section_drafts": {"1-1": gen_json["draft"]},
        },
    )
    assert resp_exp.status_code == 200
    exp_json = resp_exp.json()
    assert exp_json["status"] == "success"
    assert "사업계획서.md" in exp_json["filename"]
    assert "K-Startup PSST 표준" in exp_json["content"]

"""
사업계획서 파서(ProposalParser) 및 AI 추출기(ProposalExtractor) 단위 테스트
"""
import pytest
from src.parser.proposal_parser import ProposalParser
from src.parser.proposal_extractor import ProposalExtractor


SAMPLE_PROPOSAL_TEXT = """
[2026년도 초기창업패키지 사업계획서]
과제명: 온디바이스 초저지연 음성합성 및 AI 비서 플랫폼
기업명: (주)보이스인사이트
사업자등록번호: 123-45-67890
설립일: 2024년 03월 15일
대표자: 김지수
생년월일: 1995년 08월 20일
성별: 여성기업 인증 보유
소재지: 서울특별시 강남구 테헤란로 427 위워크타워 10층
기업부설연구소 보유: 유 (2024년 제1234호 인정)
부채비율: 120.5%
등록특허: 3건 보유
인증: 벤처기업, 여성기업
과거수혜: 2024년 예비창업패키지
기술성숙도: TRL 5단계
개발 개요: 본 과제는 경량화된 온디바이스 AI 음성합성 엔진을 개발하여 사물인터넷 및 스마트홈 기기에 탑재하는 사업입니다.
"""


def test_proposal_parser_plain_text():
    """텍스트 바이트 파싱 검증."""
    raw_bytes = SAMPLE_PROPOSAL_TEXT.encode("utf-8")
    extracted = ProposalParser.extract_text(raw_bytes, "proposal.txt")
    assert "온디바이스 초저지연 음성합성" in extracted
    assert "(주)보이스인사이트" in extracted


def test_proposal_parser_empty_or_corrupt_safe_degrade():
    """빈 바이트나 손상 파일 시 크래시 없이 빈 문자열 안전 반환 검증."""
    assert ProposalParser.extract_text(b"", "empty.pdf") == ""
    assert ProposalParser.extract_text(b"corrupt header", "test.hwpx") == ""


def test_proposal_extractor_rule_based():
    """정규식 기반 스펙 추출 정확도 검증."""
    extractor = ProposalExtractor()
    res = extractor.extract_sync(SAMPLE_PROPOSAL_TEXT)

    item = res["item"]
    specs = res["company_specs"]

    # 아이템 정보
    assert "온디바이스" in item["name"]
    assert item["trl"] == 5
    assert "인공지능" in item["keywords"] or "온디바이스 AI" in item["keywords"] or "AI" in item["keywords"]
    assert item["id"] != ""

    # 기업/대표자 스펙
    assert "(주)보이스인사이트" in specs["company_name"]
    assert specs["biz_reg_no"] == "123-45-67890"
    assert specs["opened_date"] == "2024-03-15"
    assert specs["founder_birth"] == "1995-08-20"
    assert specs["founder_gender"] == "F"
    assert "서울특별시" in specs["address"] or "강남구" in specs["address"]
    assert specs["has_rnd_lab"] is True
    assert specs["debt_ratio_pct"] == 120.5
    assert specs["registered_patents_count"] >= 3
    assert "벤처기업" in specs["certifications"]
    assert "여성기업" in specs["certifications"]
    assert "예비창업패키지" in specs["prior_grant_history"]


@pytest.mark.asyncio
async def test_proposal_extractor_async_flow():
    """비동기 extract 메서드 플로우 검증."""
    extractor = ProposalExtractor()
    res = await extractor.extract(SAMPLE_PROPOSAL_TEXT)
    assert res["item"]["name"] != ""
    assert res["company_specs"]["biz_reg_no"] == "123-45-67890"
    assert "## 사업계획서 본문 발췌" in res["extracted_proposal_md"]

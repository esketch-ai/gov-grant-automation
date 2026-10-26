"""RFP 분할 파서 단위 테스트 (정민재 파핑 계층)."""
from __future__ import annotations

from src.parser.doc_parser import AttachmentAndRfpParser, RFP_HEADER_REGEX


def test_split_into_two_chunks():
    parser = AttachmentAndRfpParser()
    text = (
        "RFP-01\n과제1: 음성분리 실증. \n"
        "상세 내용1 ...\n\n"
        "RFP-02\n과제2: 화자검증 실증. \n"
        "상세 내용2 ..."
    )
    chunks = parser._split_into_rfp_chunks(text)
    assert len(chunks) == 2
    assert "RFP-01" in chunks[0]["rfp_number"]
    assert "과제1" in chunks[0]["content"]
    assert "RFP-02" in chunks[1]["rfp_number"]
    assert "과제2" in chunks[1]["content"]


def test_single_chunk_when_no_rfp_header():
    parser = AttachmentAndRfpParser()
    chunks = parser._split_into_rfp_chunks("단일 공고 본문만 있음. RFP 없음.")
    assert len(chunks) == 1
    assert chunks[0]["rfp_number"] == "단일공고"


def test_extract_empty_when_no_files():
    parser = AttachmentAndRfpParser()
    assert parser.extract_and_split_rfps([]) == []


def test_extract_from_plain_text_file(tmp_path):
    import textwrap
    parser = AttachmentAndRfpParser()
    p = tmp_path / "notice.txt"
    p.write_text(
        textwrap.dedent(
            """\
            [RFP-01]
            과제1 내용
            [RFP-02]
            과제2 내용
            """
        ),
        encoding="utf-8",
    )
    # .txt는 파서에서 처리 안 하므로 본문 폴백은 main 에서 발생.
    # 여기서는 _split 로직만 직접 검증.
    chunks = parser._split_into_rfp_chunks(p.read_text())
    assert len(chunks) == 2


def test_rfp_regex_variants():
    assert RFP_HEADER_REGEX.search("RFP-15")
    assert RFP_HEADER_REGEX.search("과제제안요구서(RFP)")
    assert RFP_HEADER_REGEX.search("품목번호: 12345")

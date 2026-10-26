"""Tests for pure Python HWPX text extraction and self-healing site selectors.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

from src.common.db import GrantDatabase
from src.parser.doc_parser import AttachmentAndRfpParser
from src.parser.hwpx_extractor import HwpxExtractor


def _create_mock_hwpx_bytes(text_content: str) -> bytes:
    """Creates an in-memory valid HWPX file with section0.xml."""
    buf = io.BytesIO()
    xml_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
    <hp:p>
        <hp:run>
            <hp:t>{text_content}</hp:t>
        </hp:run>
    </hp:p>
</hs:sec>
"""
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("Contents/section0.xml", xml_content)
        zf.writestr("mimetype", "application/hwp+zip")
    return buf.getvalue()


def test_hwpx_extractor_valid_zip(tmp_path):
    sample_text = "2026년 첨단 인공지능 지원사업 RFP 과업지시서 세부요강"
    hwpx_bytes = _create_mock_hwpx_bytes(sample_text)

    hwpx_file = tmp_path / "announcement.hwpx"
    hwpx_file.write_bytes(hwpx_bytes)

    extracted = HwpxExtractor.extract_text(hwpx_file)
    assert sample_text in extracted
    assert len(extracted) > 10


def test_hwpx_extractor_corrupted_payload(tmp_path):
    bad_file = tmp_path / "corrupted.hwpx"
    bad_file.write_bytes(b"\x00\x01\x02\x03notazipfilegarbage")

    # Should safely return empty string without raising exception
    res = HwpxExtractor.extract_text(bad_file)
    assert res == ""

    # Test non-existent file
    res_none = HwpxExtractor.extract_text(tmp_path / "non_existent.hwpx")
    assert res_none == ""


def test_attachment_parser_with_hwpx(tmp_path):
    body = (
        "[RFP-01] 2026 차세대 AI 코칭 솔루션 실증\n지원규모: 5억원\n\n"
        "[RFP-02] 2026 디지털 헬스케어 디바이스 개발\n지원규모: 3억원"
    )
    hwpx_bytes = _create_mock_hwpx_bytes(body)
    hwpx_file = tmp_path / "multi_rfp.hwpx"
    hwpx_file.write_bytes(hwpx_bytes)

    parser = AttachmentAndRfpParser()
    chunks = parser.extract_and_split_rfps([hwpx_file])

    assert len(chunks) == 2
    assert "RFP-01" in chunks[0]["rfp_number"]
    assert "RFP-02" in chunks[1]["rfp_number"]


def test_site_selectors_crud_and_healing(tmp_path):
    db_file = tmp_path / "test_selectors.db"
    db = GrantDatabase(db_file)
    db.ensure_schema()

    # Initial check
    assert db.get_site_selector("ntis.go.kr") is None
    assert db.list_site_selectors() == []

    # Upsert self-healed selector
    ok = db.upsert_site_selector(
        domain="ntis.go.kr",
        row_selector="table.board_list tr.notice_row",
        title_selector="td.title a",
        date_selector="td.date",
        link_selector="td.title a[href]",
    )
    assert ok is True

    # Retrieve and verify
    selector = db.get_site_selector("ntis.go.kr")
    assert selector is not None
    assert selector["domain"] == "ntis.go.kr"
    assert selector["row_selector"] == "table.board_list tr.notice_row"
    assert selector["title_selector"] == "td.title a"

    # Idempotent update (Self-healing adjustment)
    ok_update = db.upsert_site_selector(
        domain="ntis.go.kr",
        row_selector="table.new_board tr",
        title_selector="a.tit",
        date_selector="span.regdate",
        link_selector="a.tit[href]",
    )
    assert ok_update is True
    updated = db.get_site_selector("ntis.go.kr")
    assert updated["row_selector"] == "table.new_board tr"

    # List all
    all_selectors = db.list_site_selectors()
    assert len(all_selectors) == 1

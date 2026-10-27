"""사업계획서 다중 포맷 텍스트 추출기 (Pure Python 지원)
지원 포맷: HWPX, HWP, PDF, DOCX, TXT, MD
(src/parser/proposal_parser.py)
"""
from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
import zipfile
import zlib
from pathlib import Path
from typing import Optional, Union

from src.common.logging_config import get_logger
from src.parser.hwpx_extractor import HwpxExtractor

logger = get_logger("proposal_parser")


class ProposalParser:
    """사업계획서 첨부파일로부터 순수 텍스트를 고속 추출하는 통합 파서."""

    @classmethod
    def extract_text(cls, source: Union[bytes, str, Path], filename: str = "") -> str:
        """
        source: 파일의 bytes 또는 파일 경로(str, Path)
        filename: 확장자 판별용 파일명 (source가 Path인 경우 생략 가능)
        """
        try:
            if isinstance(source, (str, Path)):
                p = Path(source)
                if not p.exists():
                    logger.warning("파일이 존재하지 않음: %s", p)
                    return ""
                filename = filename or p.name
                with open(p, "rb") as f:
                    file_bytes = f.read()
            elif isinstance(source, bytes):
                file_bytes = source
            else:
                logger.warning("지원되지 않는 소스 타입: %s", type(source))
                return ""

            if not file_bytes:
                return ""

            ext = (Path(filename).suffix.lower() if filename else "").strip()
            if not ext:
                # 매직 넘버 기반 판별
                if file_bytes.startswith(b"PK\x03\x04"):
                    # ZIP 기반 (HWPX or DOCX)
                    ext = ".hwpx"
                elif file_bytes.startswith(b"%PDF"):
                    ext = ".pdf"
                elif file_bytes.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
                    ext = ".hwp"
                else:
                    ext = ".txt"

            if ext == ".hwpx":
                return cls._extract_hwpx(file_bytes)
            elif ext == ".hwp":
                return cls._extract_hwp(file_bytes)
            elif ext == ".pdf":
                return cls._extract_pdf(file_bytes)
            elif ext == ".docx":
                return cls._extract_docx(file_bytes)
            elif ext in (".txt", ".md", ".json", ".csv"):
                return cls._extract_plain_text(file_bytes)
            else:
                # 알 수 없는 확장자는 텍스트 디코딩 시도 후 ZIP 검사
                if file_bytes.startswith(b"PK\x03\x04"):
                    res = cls._extract_hwpx(file_bytes)
                    if res:
                        return res
                    return cls._extract_docx(file_bytes)
                return cls._extract_plain_text(file_bytes)

        except Exception as e:
            logger.warning("사업계획서 텍스트 추출 중 오류(safe degrade): %s", e)
            return ""

    @classmethod
    def _extract_hwpx(cls, data: bytes) -> str:
        """HWPX 추출 (HwpxExtractor 활용)."""
        return HwpxExtractor.extract_text(data)

    @classmethod
    def _extract_hwp(cls, data: bytes) -> str:
        """
        HWP 5.0 OLE 파일 순수 파이썬 파싱 (olefile + zlib).
        외부 뷰어나 CLI 도구 없이 BodyText 스트림에서 텍스트를 복원합니다.
        """
        texts = []
        try:
            import olefile
            if olefile.isOleFile(io.BytesIO(data)):
                ole = olefile.OleFileIO(io.BytesIO(data))
                # BodyText/Section0, Section1 ... 순회
                sections = [e for e in ole.listdir() if len(e) >= 2 and e[0] == "BodyText"]
                # Section 번호순 정렬
                sections.sort(key=lambda s: s[1])

                for sec in sections:
                    stream = ole.openstream(sec).read()
                    try:
                        # HWP 5.0 스트림은 보통 raw deflate 압축 (-15)
                        decompressed = zlib.decompress(stream, -15)
                    except Exception:
                        decompressed = stream

                    # HWP 내부 텍스트는 UTF-16LE 인코딩
                    try:
                        decoded = decompressed.decode("utf-16-le", errors="ignore")
                        # HWP 제어문자 필터링 (널문자, 포맷팅 태그 등 정리)
                        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", decoded)
                        cleaned = re.sub(r"\s+", " ", cleaned).strip()
                        if cleaned:
                            texts.append(cleaned)
                    except Exception as e:
                        logger.warning("HWP 섹션 디코딩 실패: %s", e)
                ole.close()
        except Exception as e:
            logger.warning("olefile HWP 파싱 실패: %s", e)

        if texts:
            return "\n\n".join(texts)

        # 폴백: 바이너리에서 한국어/영문 문자열 정규식 발췌
        return cls._extract_plain_text(data)

    @classmethod
    def _extract_pdf(cls, data: bytes) -> str:
        """PDF 추출 (pypdf 또는 fitz 활용)."""
        # 1차: fitz(PyMuPDF) 시도
        try:
            import fitz
            doc = fitz.open(stream=data, filetype="pdf")
            pages = []
            for page in doc:
                text = page.get_text("text").strip()
                if text:
                    pages.append(text)
            doc.close()
            if pages:
                return "\n\n".join(pages)
        except Exception:
            pass

        # 2차: pypdf 시도
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(data))
            pages = []
            for page in reader.pages:
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(text.strip())
            if pages:
                return "\n\n".join(pages)
        except Exception as e:
            logger.warning("PDF 파싱 실패: %s", e)

        return ""

    @classmethod
    def _extract_docx(cls, data: bytes) -> str:
        """DOCX 추출 (zipfile + XML 파싱)."""
        try:
            with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
                if "word/document.xml" in zf.namelist():
                    xml_content = zf.read("word/document.xml")
                    tree = ET.fromstring(xml_content)
                    paragraphs = []
                    # w:p 노드 순회
                    for p in tree.iter():
                        if p.tag.endswith("}p"):
                            texts = [node.text for node in p.iter() if node.text and node.tag.endswith("}t")]
                            p_text = "".join(texts).strip()
                            if p_text:
                                paragraphs.append(p_text)
                    return "\n\n".join(paragraphs)
        except Exception as e:
            logger.warning("DOCX 파싱 실패: %s", e)
        return ""

    @classmethod
    def _extract_plain_text(cls, data: bytes) -> str:
        """순수 텍스트 디코딩 (UTF-8, CP949 순차 시도)."""
        for enc in ("utf-8", "cp949", "euc-kr", "utf-16-le"):
            try:
                decoded = data.decode(enc)
                if len(decoded.strip()) > 0:
                    return decoded.strip()
            except UnicodeDecodeError:
                continue
        # 마지막 수단: ASCII/가독 문자 위주 발췌
        return data.decode("utf-8", errors="ignore").strip()

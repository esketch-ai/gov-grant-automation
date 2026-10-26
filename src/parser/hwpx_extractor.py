"""Pure Python HWPX text extractor without external binary dependencies.
(src/parser/hwpx_extractor.py)
"""
from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Optional, Union

from ..common.logging_config import get_logger

logger = get_logger("hwpx_extractor")


class HwpxExtractor:
    """Extracts raw text and paragraphs from .hwpx files using pure standard library."""

    @classmethod
    def extract_text(cls, source: Union[str, Path, bytes]) -> str:
        """
        Extracts all paragraph texts from an HWPX file or byte buffer.
        Returns empty string on any corrupted format without raising unhandled exceptions.
        """
        try:
            if isinstance(source, (str, Path)):
                p = Path(source)
                if not p.exists() or not p.is_file():
                    logger.warning("HWPX 파일 미존재: %s", source)
                    return ""
                with open(p, "rb") as f:
                    file_bytes = f.read()
            elif isinstance(source, bytes):
                file_bytes = source
            else:
                logger.warning("지원되지 않는 HWPX 소스 타입: %s", type(source))
                return ""

            if not file_bytes:
                return ""

            # Check ZIP header magic
            if not file_bytes.startswith(b"PK\x03\x04"):
                logger.warning("유효하지 않은 HWPX(ZIP) 매직 넘버")
                return ""

            texts = []
            with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as zf:
                # Find all section XML files under Contents/
                section_files = [
                    name for name in zf.namelist()
                    if "section" in name.lower() and name.endswith(".xml")
                ]
                # If no explicit section files, inspect all XML files in Contents/
                if not section_files:
                    section_files = [
                        name for name in zf.namelist()
                        if name.startswith("Contents/") and name.endswith(".xml")
                    ]

                for sec_name in sorted(section_files):
                    try:
                        xml_bytes = zf.read(sec_name)
                        tree = ET.fromstring(xml_bytes)
                        # Extract all text inside paragraph tags or text elements
                        sec_text = "".join(tree.itertext()).strip()
                        if sec_text:
                            texts.append(sec_text)
                    except Exception as e:
                        logger.warning("HWPX 섹션 XML(%s) 파싱 오류(무시하고 계속): %s", sec_name, e)

            extracted = "\n\n".join(texts).strip()
            logger.info("HWPX 파싱 완료: %d자 추출됨", len(extracted))
            return extracted

        except zipfile.BadZipFile as e:
            logger.warning("손상된 HWPX 압축 파일(safe degrade): %s", e)
            return ""
        except Exception as e:
            logger.exception("HWPX 텍스트 추출 중 예기치 않은 오류(safe degrade): %s", e)
            return ""

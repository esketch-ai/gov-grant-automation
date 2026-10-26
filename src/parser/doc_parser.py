"""
첨부 문서(HWP/PDF/HWPX/ZIP) 파서 및 통합공고 RFP 분할기
(src/parser/doc_parser.py)

- ZIP -> 압축해제 후 하위 pdf/hwp 파싱
- PDF -> PyMuPDF(fitz) 표(Table) 추출 + 텍스트 -> Markdown
- HWP/HWPX -> 로컬 변환기(hwp5txt/LibreOffice/pyhwpx) 폴백 순으로 원문 추출
- 통합공고 본문에서 RFP_HEADER_REGEX 로 개별 RFP 청크 분할

통제 포인트(정민재/박준호):
- 페이지 단위 스트림 처리 + 청크 상한(15000자)으로 메모리 방어.
- 표 추출 실패/지원불가 파일은 degrade(크래시 방지) 후 원본참조 문구 반환.
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import List, Dict, Any

from ..common.logging_config import get_logger
from ..common.schemas import RawNotice
from .hwpx_extractor import HwpxExtractor

logger = get_logger(__name__)

# RFP/과제제안요구서/품목번호 헤더 탐지 정규식
RFP_HEADER_REGEX = re.compile(
    r"(\[?RFP\s*[-_:]?\s*\d+\]?|과제제안요구서\s*\(?RFP\)?|품목번호\s*[:：]?\s*\d+)"
)

_SINGE_RFP_CONTENT_LIMIT = 15000  # 청크 상한(메모리 방어)
_CHUNK_LIMIT = 12000              # 개별 RFP 본문 상한


class AttachmentAndRfpParser:
    def extract_and_split_rfps(self, attachment_paths: List[Path]) -> List[Dict[str, str]]:
        """
        attachment_paths: List[Path] (pdf/hwp/zip 등)
        return: List[dict(rfp_number, rfp_title, content)]
        - 첨부가 없으면 빈 리스트(상위 main이 본문 폴백을 담당)
        """
        if not attachment_paths:
            return []

        full_markdown_docs: List[str] = []
        for file_path in attachment_paths:
            if not file_path or not file_path.exists():
                logger.warning("존재하지 않는 첨부 건너뜀: %s", file_path)
                continue
            try:
                if file_path.suffix.lower() == ".zip":
                    for ef in self._unzip_files(file_path):
                        full_markdown_docs.append(self._parse_single_file(ef))
                else:
                    full_markdown_docs.append(self._parse_single_file(file_path))
            except Exception as e:
                # 단일 파일 파싱 실패가 전체 파이프라인을 멈추지 않도록
                logger.exception("첨부 파싱 실패[%s]: %s", file_path.name, e)

        if not full_markdown_docs:
            return []

        combined_text = "\n\n---\n\n".join(d for d in full_markdown_docs if d)
        return self._split_into_rfp_chunks(combined_text)

    # ------------------------------------------------------------------ helpers
    def _unzip_files(self, zip_path: Path) -> List[Path]:
        extract_dir = zip_path.parent / zip_path.stem
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            # zip bomb 방어: 압축 비율/개수 상한
            if len(names) > 5000:
                raise ValueError(f"ZIP 압축개수 초과(보안): {len(names)}개")
            zf.extractall(extract_dir)
        out: List[Path] = []
        for p in extract_dir.rglob("*"):
            if p.is_file() and p.suffix.lower() in (".pdf", ".hwp", ".hwpx"):
                out.append(p)
        return out

    def _parse_single_file(self, path: Path) -> str:
        ext = path.suffix.lower()
        try:
            if ext == ".hwpx":
                extracted = HwpxExtractor.extract_text(path)
                if extracted:
                    return extracted
                # If pure extraction yields empty, degrade gracefully
                return f"[HWPX 본문 빈 파일 또는 파싱 예외: {path.name}]"
            if ext == ".pdf":
                return self._parse_pdf_with_tables(path)
            if ext == ".hwp":
                return self._parse_hwp_with_tables(path)
        except Exception as e:
            logger.warning("단일 파일 파싱 degrade[%s]: %s", path.name, e)
        return f"[첨부파일 원문 참조 요망: {path.name}]"

    def _parse_pdf_with_tables(self, pdf_path: Path) -> str:
        try:
            import fitz  # PyMuPDF
        except Exception:
            logger.warning("PyMuPDF 미설치 -> PDF 파싱 건너뜀(%s)", pdf_path.name)
            return f"[PyMuPDF 미설치: {pdf_path.name} 원문 참조]"

        doc = fitz.open(pdf_path)
        pages_md: List[str] = []
        try:
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text("text")
                table_md_list: List[str] = []
                try:
                    for tab in page.find_tables() or []:
                        rows = tab.extract()
                        if not rows:
                            continue
                        header = "| " + " | ".join(_clean(c) for c in rows[0]) + " |"
                        sep = "| " + " | ".join("---" for _ in rows[0]) + " |"
                        body = "\n".join(
                            "| " + " | ".join(_clean(c) for c in r) + " |"
                            for r in rows[1:]
                        )
                        table_md_list.append(f"{header}\n{sep}\n{body}")
                except Exception as e:
                    logger.warning("PDF 표 추출 degrade(p.%d): %s", page_num, e)
                tables_joined = "\n\n".join(table_md_list)
                pages_md.append(f"[페이지 {page_num}]\n{text}\n{tables_joined}")
        finally:
            doc.close()
        return "\n\n".join(pages_md)

    def _parse_hwp_with_tables(self, hwp_path: Path) -> str:
        import shutil
        import subprocess

        # 1) hwp5txt CLI(Windows/Linux)
        if shutil.which("hwp5txt"):
            try:
                res = subprocess.run(["hwp5txt", str(hwp_path)], capture_output=True, text=True,
                                     check=False, timeout=60)
                if res.stdout:
                    return res.stdout
            except Exception as e:
                logger.warning("hwp5txt 실패: %s", e)

        # 2) LibreOffice headless 변환 (macOS/로컬)
        if shutil.which("libreoffice") or shutil.which("soffice"):
            try:
                cmd = ["libreoffice"] if shutil.which("libreoffice") else ["soffice"]
                res = subprocess.run(
                    cmd + ["--headless", "--convert-to", "txt", str(hwp_path)],
                    capture_output=True, text=True, check=False, timeout=120,
                )
                txt = hwp_path.with_suffix(".txt")
                if txt.exists():
                    return txt.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                logger.warning("LibreOffice HWP 변환 실패: %s", e)

        # 3) 원본참조 폴백
        return f"[첨부파일 원문 참조 요망: {hwp_path.name}]"

    def _split_into_rfp_chunks(self, text: str) -> List[Dict[str, str]]:
        matches = list(RFP_HEADER_REGEX.finditer(text or ""))
        if len(matches) <= 1:
            # 통합공고가 아니면 '본문 전체' 1개 청크(상한 적용)
            return [
                {
                    "rfp_number": "단일공고",
                    "rfp_title": "본문 전체",
                    "content": (text or "")[:_SINGE_RFP_CONTENT_LIMIT],
                }
            ]

        chunks: List[Dict[str, str]] = []
        for idx, match in enumerate(matches):
            start_pos = match.start()
            end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            segment = text[start_pos:end_pos].strip()
            first_line = segment.split("\n")[0][:80]
            chunks.append(
                {
                    "rfp_number": match.group(0),
                    "rfp_title": first_line,
                    "content": segment[:_CHUNK_LIMIT],  # 대용량 방어
                }
            )
        return chunks


def _clean(cell: Any) -> str:
    return str(cell or "").replace("\n", " ").strip()

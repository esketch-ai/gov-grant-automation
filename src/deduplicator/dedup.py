"""
다기관 중복 제거기 (src/deduplicator/dedup.py)

NTIS/IRIS/전문기관에 중복 게시된 공고를 행정공고번호 기준(canonical_id)으로 병합한다.
공고번호 부재 시 fuzzy(SequenceMatcher>=0.90)로 병합, 그것도 없으면 md5 해시로 canonical.

통제 포인트(정민재/박준호):
- 첨부파일이 더 많은 전문기관(Tier2: NIPA/KEIT 등) 데이터를 우선 보존.
- SequenceMatcher 비용은 O(n^2) 인데 n이 커지면 느리므로 1차 해시 인덱스로 축소.
"""
from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher
from typing import List, Dict, Any

from ..common.logging_config import get_logger
from ..common.schemas import RawNotice

logger = get_logger(__name__)

# '제 2024 - 1234 호' 형태로의 정규식 (공백 유동 허용)
NOTICE_NO_REGEX = re.compile(r"(제\s*\d{4}\s*-\s*\d+\s*호)")

FUZZY_THRESHOLD = 0.90


class CrossPortalDeduplicator:
    """
    notices: List[RawNotice]
    return : List[RawNotice]  (canonical_id 로 통합)
    """

    def __init__(self, fuzzy_threshold: float = FUZZY_THRESHOLD):
        self.fuzzy_threshold = fuzzy_threshold

    def deduplicate(self, notices: List[RawNotice]) -> List[RawNotice]:
        if not notices:
            return []

        merged_map: Dict[str, RawNotice] = {}
        # 1차 인덱스: 정규식 공고번호 -> canonical
        norm_index: Dict[str, str] = {}
        # 2차 인덱스: 청정한 title md5 -> canonical (fuzzy 대안 축소)
        hash_index: Dict[str, str] = {}

        fuzzy_fallbacks = 0
        for notice in notices:
            match = NOTICE_NO_REGEX.search((notice.title or "") + " " + (notice.body_text or ""))
            if match:
                norm_no = re.sub(r"\s+", "", match.group(1))
                canonical_key = "NOTICE_" + norm_no
            else:
                canonical_key = self._find_fuzzy_key(
                    notice.title or "", norm_index, hash_index, merged_map
                )
                fuzzy_fallbacks += 1

            if canonical_key in merged_map:
                existing = merged_map[canonical_key]
                # 첨부파일이 더 많은 전문기관 데이터를 우선 보존(Tier 2 우선)
                if len(notice.downloaded_files) > len(existing.downloaded_files):
                    merged_map[canonical_key] = notice
                    self._reindex(canonical_key, notice, norm_index, hash_index)
            else:
                merged_map[canonical_key] = notice
                self._record_index(canonical_key, notice, norm_index, hash_index)

        if fuzzy_fallbacks:
            logger.info("공고번호 매칭 실패하여 fuzzy 병합: %d건", fuzzy_fallbacks)
        logger.info("중복 제거 완료: %d -> %d 건", len(notices), len(merged_map.values()))
        return list(merged_map.values())

    # --------------------------------------------------------------- helpers
    def _record_index(self, key, notice, norm_index, hash_index) -> None:
        clean = self._normalize_title(notice.title or "")
        if clean:
            hash_index.setdefault(clean, key)

    def _reindex(self, key, notice, norm_index, hash_index) -> None:
        clean = self._normalize_title(notice.title or "")
        if clean:
            hash_index[clean] = key

    def _find_fuzzy_key(
        self,
        title: str,
        norm_index: Dict[str, str],
        hash_index: Dict[str, str],
        merged_map: Dict[str, RawNotice],
    ) -> str:
        clean = self._normalize_title(title)
        # 1) 동일 hash 로직으로 즉시 병합(성능 최적화)
        if clean and clean in hash_index:
            return hash_index[clean]

        # 2) SequenceMatcher 로 fuzzy (해시 미일치 시만)
        for key, item in merged_map.items():
            existing_clean = self._normalize_title(item.title or "")
            if not clean or not existing_clean:
                continue
            if SequenceMatcher(None, clean, existing_clean).ratio() >= self.fuzzy_threshold:
                if clean not in hash_index:
                    hash_index[clean] = key
                return key

        digest = hashlib.md5(clean.encode("utf-8")).hexdigest()[:12]
        return f"HASH_{digest}"

    @staticmethod
    def _normalize_title(title: str) -> str:
        """'[ ]/()/공백'을 제거한 청정한 title(대칭 비교용)."""
        return re.sub(r"\[.*?\]|\(.*?\)|\s+", "", title or "")

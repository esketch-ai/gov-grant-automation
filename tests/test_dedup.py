"""중복 제거기 단위 테스트 (정민재 파싱 계층)."""
from __future__ import annotations

from src.common.schemas import RawNotice
from src.deduplicator.dedup import CrossPortalDeduplicator, NOTICE_NO_REGEX


def test_notice_no_regex():
    assert NOTICE_NO_REGEX.search("제 2024 - 11 호")
    assert NOTICE_NO_REGEX.search("제2024-11호")
    assert NOTICE_NO_REGEX.search("제  2024  -  11   호")


def test_merge_by_same_notice_number():
    dedup = CrossPortalDeduplicator()
    n1 = RawNotice("ntis", "A", "NTIS", "과기부", "상세", "url1",
                   body_text="제 2024 - 11 호", downloaded_files=[])
    n2 = RawNotice("iris", "A (IRIS)", "IRIS", "과기부", "상세", "url2",
                   body_text="제2024-11호", downloaded_files=["file.pdf"])
    result = dedup.deduplicate([n1, n2])
    assert len(result) == 1
    # 첨부가 더 많은 것(n2)을 우선 보존
    assert result[0].portal_id == "iris"
    assert result[0].downloaded_files == ["file.pdf"]


def test_fuzzy_merge_no_notice_number():
    dedup = CrossPortalDeduplicator()
    n1 = RawNotice("k", "AI 음성분리", "K", "기타", "x", "u1", body_text="")
    n2 = RawNotice("k", "AI  음성분리", "K", "기타", "x", "u2", body_text="")
    result = dedup.deduplicate([n1, n2])
    assert len(result) == 1  # 공백만 다른 title은 동일 canonical


def test_distinct_titles_not_merged():
    dedup = CrossPortalDeduplicator(fuzzy_threshold=0.95)
    n1 = RawNotice("k", "탄소배출권 플랫폼", "K", "기타", "x", "u1")
    n2 = RawNotice("k", "전통시장 소상공인 지원", "K", "기타", "x", "u2")
    result = dedup.deduplicate([n1, n2])
    assert len(result) == 2


def test_empty_input():
    assert CrossPortalDeduplicator().deduplicate([]) == []

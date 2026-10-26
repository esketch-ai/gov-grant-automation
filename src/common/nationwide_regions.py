"""Nationwide Regions: 대한민국 17개 광역시·도 표준 지역 코드 및 지자체 포털/TP 매핑.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set


@dataclass(frozen=True)
class RegionInfo:
    code: str              # 2자리 표준 시도 코드 (예: "11", "26")
    name: str              # 시도 명칭 (예: "서울", "부산")
    full_name: str         # 정식 명칭 (예: "서울특별시", "부산광역시")
    aliases: tuple[str, ...] # 별칭 및 포함 키워드
    tp_name: str           # 지역 테크노파크 (TP) 명칭
    portal_domain: str     # 지자체 대표 포털


NATIONWIDE_REGIONS: Dict[str, RegionInfo] = {
    "11": RegionInfo("11", "서울", "서울특별시", ("서울", "수도권", "서울시"), "서울테크노파크", "seoul.go.kr"),
    "26": RegionInfo("26", "부산", "부산광역시", ("부산", "부산시", "동남권"), "부산테크노파크", "busan.go.kr"),
    "27": RegionInfo("27", "대구", "대구광역시", ("대구", "대구시", "대경권"), "대구테크노파크", "daegu.go.kr"),
    "28": RegionInfo("28", "인천", "인천광역시", ("인천", "인천시", "인천권"), "인천테크노파크", "incheon.go.kr"),
    "29": RegionInfo("29", "광주", "광주광역시", ("광주", "광주시", "호남권"), "광주테크노파크", "gwangju.go.kr"),
    "30": RegionInfo("30", "대전", "대전광역시", ("대전", "대전시", "충청권"), "대전테크노파크", "daejeon.go.kr"),
    "31": RegionInfo("31", "울산", "울산광역시", ("울산", "울산시"), "울산테크노파크", "ulsan.go.kr"),
    "36": RegionInfo("36", "세종", "세종특별자치시", ("세종", "세종시"), "세종테크노파크", "sejong.go.kr"),
    "41": RegionInfo("41", "경기", "경기도", ("경기", "수도권", "경기도"), "경기테크노파크", "gg.go.kr"),
    "42": RegionInfo("42", "강원", "강원특별자치도", ("강원", "강원도"), "강원테크노파크", "provin.gangwon.kr"),
    "43": RegionInfo("43", "충북", "충청북도", ("충북", "충청북도"), "충북테크노파크", "chungbuk.go.kr"),
    "44": RegionInfo("44", "충남", "충청남도", ("충남", "충청남도"), "충남테크노파크", "chungnam.go.kr"),
    "45": RegionInfo("45", "전북", "전북특별자치도", ("전북", "전라북도"), "전북테크노파크", "jeonbuk.go.kr"),
    "46": RegionInfo("46", "전남", "전라남도", ("전남", "전라남도"), "전남테크노파크", "jeonnam.go.kr"),
    "47": RegionInfo("47", "경북", "경상북도", ("경북", "경상북도"), "경북테크노파크", "gb.go.kr"),
    "48": RegionInfo("48", "경남", "경상남도", ("경남", "경상남도"), "경남테크노파크", "gyeongnam.go.kr"),
    "50": RegionInfo("50", "제주", "제주특별자치도", ("제주", "제주도"), "제주테크노파크", "jeju.go.kr"),
}


def detect_region_from_text(text: str) -> Optional[RegionInfo]:
    """텍스트에서 가장 먼저 또는 가장 뚜렷하게 언급된 지역을 감지합니다."""
    if not text:
        return None
    for reg in NATIONWIDE_REGIONS.values():
        for alias in reg.aliases:
            if alias in text:
                return reg
    return None


def detect_all_regions_from_text(text: str) -> List[RegionInfo]:
    """텍스트에 언급된 모든 광역시도를 반환합니다."""
    found: List[RegionInfo] = []
    if not text:
        return found
    for reg in NATIONWIDE_REGIONS.values():
        if any(alias in text for alias in reg.aliases):
            found.append(reg)
    return found

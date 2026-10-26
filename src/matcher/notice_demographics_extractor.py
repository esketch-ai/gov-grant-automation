"""Notice Demographics Extractor: 공고문 텍스트로부터
지역 제한, 업력 요건, 청년/여성 우대 및 가점 조건을 기계식으로 정밀 추출하는 엔진.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from src.common.nationwide_regions import detect_all_regions_from_text


@dataclass
class NoticeDemographicsCriteria:
    """공고문에서 추출된 신청자격 및 가점 요건"""
    is_general_track: bool = False              # 전 업종/기술 무관 공고 여부
    target_regions: List[str] = field(default_factory=list) # 대상/제한 지역 (예: ["부산"])
    min_biz_age_years: float = 0.0              # 최소 업력 (예: 3.0년)
    max_biz_age_years: Optional[float] = None   # 최대 업력 (예: 3.0년, 7.0년)
    is_youth_only: bool = False                 # 청년 전용 공고
    is_youth_priority: bool = False             # 청년 우대/가점
    is_female_only: bool = False                # 여성기업 전용
    is_female_priority: bool = False            # 여성기업 우대/가점
    bonus_items: List[str] = field(default_factory=list) # 추출된 가점 항목 목록


class NoticeDemographicsExtractor:
    """공고문 자격·가점 요건 기계식 추출기"""

    GENERAL_TRACK_PATTERNS = [
        r"\[일반분야\]", r"일반분야", r"전\s*분야", r"업종\s*무관",
        r"창업지원사업\s*통합공고", r"초기창업패키지", r"예비창업패키지",
        r"청년창업사관학교", r"창업도약패키지",
    ]

    def extract(self, title: str, body: str = "") -> NoticeDemographicsCriteria:
        combined = f"{title}\n{body}"
        criteria = NoticeDemographicsCriteria()

        # 1. 일반 트랙 (기술 무관) 감지
        if any(re.search(p, combined) for p in self.GENERAL_TRACK_PATTERNS):
            criteria.is_general_track = True

        # 2. 지역 제한/우대 감지
        regions = detect_all_regions_from_text(combined)
        # 단순 주소 표기 외에 '소재', '관내', '이전' 등과 결합된 지역 필터링
        target_regs = set()
        for reg in regions:
            pattern = rf"{reg.name}(?:시|도)?\s*(?:소재|관내|본사|기업|클러스터|창경)"
            if re.search(pattern, combined):
                target_regs.add(reg.name)
        criteria.target_regions = sorted(list(target_regs))

        # 3. 업력 요건 감지
        if "예비창업자" in combined and "초기창업" not in combined:
            criteria.min_biz_age_years = 0.0
            criteria.max_biz_age_years = 0.0
        elif re.search(r"3년\s*이내|초기창업", combined):
            criteria.min_biz_age_years = 0.0
            criteria.max_biz_age_years = 3.0
        elif re.search(r"3년\s*이상\s*7년\s*이내|창업도약", combined):
            criteria.min_biz_age_years = 3.0
            criteria.max_biz_age_years = 7.0
        elif re.search(r"7년\s*이내", combined):
            criteria.min_biz_age_years = 0.0
            criteria.max_biz_age_years = 7.0

        # 4. 청년 요건 감지
        if "청년전용" in combined or "청년창업사관학교" in combined or "만 39세 이하" in combined:
            criteria.is_youth_only = True
            criteria.is_youth_priority = True
        elif "청년" in combined:
            criteria.is_youth_priority = True

        # 5. 여성 요건 감지
        if "여성전용" in combined or "여성기업 특화" in combined:
            criteria.is_female_only = True
            criteria.is_female_priority = True
        elif "여성기업" in combined or "여성대표" in combined:
            criteria.is_female_priority = True

        # 6. 가점 항목 추출
        bonus_list = []
        if criteria.is_youth_priority:
            bonus_list.append("청년 창업자 가점/우대")
        if criteria.is_female_priority:
            bonus_list.append("여성기업 가점/우대")
        if criteria.target_regions:
            bonus_list.append(f"관내({', '.join(criteria.target_regions)}) 소재 가점/우대")
        if "벤처기업" in combined:
            bonus_list.append("벤처기업 인증 가점")
        if "특허" in combined:
            bonus_list.append("특허 보유 가점")

        criteria.bonus_items = bonus_list

        return criteria

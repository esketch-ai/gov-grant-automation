"""Applicant Profiler: 사업주의 사업자등록 정보와 대표자 정보를 바탕으로
업력, 청년창업 해당 여부, 여성기업 여부, 관할 지자체 코드를 자동 계산·판정하는 엔진.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from src.common.nationwide_regions import RegionInfo, detect_region_from_text
from src.common.constants import (
    YOUTH_AGE_LIMIT_GENERAL,
    YOUTH_AGE_LIMIT_SPECIAL,
    BIZ_AGE_EARLY_STAGE_YEARS,
    BIZ_AGE_GROWTH_STAGE_YEARS,
)


class BizStage(str, Enum):
    """중소기업기본법 및 창업지원법 기준 기업 생애주기"""
    PRE_STARTUP = "예비창업자(0년)"
    EARLY_STAGE = "초기창업기업(3년이내)"
    GROWTH_STAGE = "창업도약기업(3~7년)"
    SCALEUP_MATURE = "중소·도약기업(7년초과)"


@dataclass
class CalculatedApplicantProfile:
    """자동 계산된 사업주의 정밀 상태 프로필"""
    company_name: str
    biz_reg_no: str                   # 사업자등록번호 10자리 (예: "123-45-67890")
    opened_date: Optional[date]       # 개업연월일
    biz_age_years: float              # 정확한 업력 (년 단위, 소수점 1자리)
    biz_stage: BizStage               # 기업 생애주기
    founder_birth_date: Optional[date] # 대표자 생년월일
    founder_age: int                  # 만 나이
    is_youth_39: bool                 # 중기부 청년창업 기준 (만 39세 이하)
    is_youth_34: bool                 # 과기부/일부 지자체 청년 기준 (만 34세 이하)
    is_female_founder: bool           # 여성 기업 여부
    region: Optional[RegionInfo]      # 본사 관할 광역시도
    address: str                      # 사업장 주소
    certifications: List[str] = field(default_factory=list) # 인증 (벤처, 이노비즈 등)


class ApplicantProfiler:
    """사업주 상태 판정기"""

    def __init__(self, reference_date: Optional[date] = None) -> None:
        # 기준일자 (기본값은 오늘)
        self.ref_date = reference_date or date.today()

    def profile_from_data(
        self,
        company_name: str,
        biz_reg_no: str,
        opened_at_str: Optional[str] = None,   # "2024-04-15" 또는 "20240415"
        founder_birth_str: Optional[str] = None, # "1994-06-20" 또는 "19940620"
        founder_gender: str = "",              # "F" (여성), "M" (남성), "" (미설정)
        address: str = "",
        certifications: Optional[List[str]] = None,
    ) -> CalculatedApplicantProfile:
        """사업자 정보로부터 1초 만에 법적 자격 상태를 산출합니다."""
        certifications = certifications or []

        # 1. 개업일 파싱 및 업력 계산
        opened_date = self._parse_date(opened_at_str)
        if opened_date:
            days_diff = (self.ref_date - opened_date).days
            biz_age_years = max(0.0, round(days_diff / 365.25, 1))
        else:
            biz_age_years = 0.0  # 개업일 미기재 시 예비창업자로 간주

        # 기업 생애주기 판정
        if biz_age_years == 0.0:
            biz_stage = BizStage.PRE_STARTUP
        elif biz_age_years <= BIZ_AGE_EARLY_STAGE_YEARS:
            biz_stage = BizStage.EARLY_STAGE
        elif biz_age_years <= BIZ_AGE_GROWTH_STAGE_YEARS:
            biz_stage = BizStage.GROWTH_STAGE
        else:
            biz_stage = BizStage.SCALEUP_MATURE

        # 2. 대표자 생년월일 파싱 및 만 나이/청년 판정
        birth_date = self._parse_date(founder_birth_str)
        if birth_date:
            age = self.ref_date.year - birth_date.year
            if (self.ref_date.month, self.ref_date.day) < (birth_date.month, birth_date.day):
                age -= 1
            is_youth_39 = age <= YOUTH_AGE_LIMIT_GENERAL
            is_youth_34 = age <= YOUTH_AGE_LIMIT_SPECIAL
        else:
            age = 0
            is_youth_39 = False  # 생년월일 미기재 시 청년 혜택 자동 부여 금지
            is_youth_34 = False

        # 3. 여성기업 여부 (남성 대표 및 성별 미지정은 법적 배제 원칙)
        gender_clean = (founder_gender or "").strip().upper()
        if gender_clean in ("M", "NONE"):
            is_female = False
        elif gender_clean == "F":
            is_female = True
        else:
            # 성별 미기재('') 상태: certifications에 명시되었더라도 대표자 성별 확인 전까지는 False
            is_female = False

        # 4. 소재지 관할 지역 감지
        region = detect_region_from_text(address)

        return CalculatedApplicantProfile(
            company_name=company_name,
            biz_reg_no=self._format_biz_no(biz_reg_no),
            opened_date=opened_date,
            biz_age_years=biz_age_years,
            biz_stage=biz_stage,
            founder_birth_date=birth_date,
            founder_age=age,
            is_youth_39=is_youth_39,
            is_youth_34=is_youth_34,
            is_female_founder=is_female,
            region=region,
            address=address,
            certifications=certifications,
        )

    def _parse_date(self, s: Optional[str]) -> Optional[date]:
        if not s:
            return None
        cleaned = re.sub(r"[^0-9]", "", s)
        if len(cleaned) == 8:
            return datetime.strptime(cleaned, "%Y%m%d").date()
        return None

    def _format_biz_no(self, s: str) -> str:
        cleaned = re.sub(r"[^0-9]", "", s)
        if len(cleaned) == 10:
            return f"{cleaned[:3]}-{cleaned[3:5]}-{cleaned[5:]}"
        return s

"""Multi-Axis Matcher: 단일 기술 키워드의 한계를 극복하는 4대 다차원 매칭 엔진.
심리상담, 교육, 콘텐츠 등 비(非)R&D/플랫폼 기업이 청년창업, 여성기업, 지역경제, 사회서비스, 바우처 등
실제 정부지원사업의 대부분을 차지하는 정책 목적형 공고에 정확히 매칭되도록 지원합니다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

from src.common.schemas import RawNotice
from src.common.nationwide_regions import NATIONWIDE_REGIONS


class NoticeTrack(str, Enum):
    """정부지원사업의 6대 트랙 분류"""
    GENERAL_STARTUP = "창업패키지(일반분야)"
    DEMOGRAPHIC_FOCUSED = "신분특화(청년/여성/시니어)"
    REGIONAL_LOCAL = "지역경제/로컬특화"
    SOCIAL_POLICY = "사회서비스/마음건강/복지"
    DEEP_TECH_RND = "기술R&D/과기·산업부"
    VOUCHER_BIZ = "바우처/디지털전환(DX)"


@dataclass
class ApplicantProfile:
    """사업주의 다차원 기업 프로필"""
    company_name: str
    biz_age_years: float              # 업력 (예: 0.5=6개월, 2.0=2년, 4.5=4년 6개월)
    founder_age: int                  # 대표자 만 나이 (청년 기준: 만 39세 이하)
    is_female_founder: bool = False   # 여성 기업 여부
    location: str = "서울"            # 본사 소재지 (예: "부산", "대구", "전남")
    is_social_venture: bool = False   # 소셜벤처/사회적기업 여부
    tags: List[str] = field(default_factory=list)  # 사업 키워드 (예: ["심리상담", "플랫폼"])


@dataclass
class MultiAxisEvaluationResult:
    """다차원 매칭 판정 결과"""
    is_eligible: bool
    match_score: int                  # 0 ~ 100
    matched_track: NoticeTrack
    track_description: str
    pass_reasons: List[str] = field(default_factory=list)
    bonus_points: List[str] = field(default_factory=list)
    disqualification_reasons: List[str] = field(default_factory=list)


class MultiAxisMatcher:
    """4대 축(자격·신분, 정책·범주, 자금용도, 온톨로지 확장) 기반 지능형 매칭 엔진"""

    # 1. 도메인 온톨로지 확장 사전 (기술 키워드를 정부 정책 테마로 매핑)
    DOMAIN_ONTOLOGY: Dict[str, Set[str]] = {
        "심리상담": {
            "마음건강", "정신건강", "멘탈헬스", "디지털치료", "사회서비스",
            "고립은둔", "심리", "상담", "복지", "비대면", "플랫폼", "웰니스",
        },
        "교육": {
            "에듀테크", "직무교육", "인재양성", "평생학습", "비대면교육", "디지털배움터",
        },
        "식품": {
            "푸드테크", "로컬푸드", "스마트제조", "안전위생", "지역특산물",
        },
        "친환경": {
            "넷제로", "탄소중립", "ESG", "에너지효율", "순환경제", "재활용",
        },
        "인공지능": {
            "AI", "AX", "머신러닝", "LAM", "LLM", "빅데이터", "디지털전환",
        },
    }

    # 2. 일반 트랙 (전 업종 대상) 판정 키워드
    GENERAL_TRACK_KEYWORDS = [
        "창업지원사업 통합공고", "예비창업패키지", "초기창업패키지", "창업도약패키지",
        "청년창업사관학교", "청창사", "일반분야", "전 분야", "업종 무관",
        "혁신시제품", "우수조달", "조달청", "시제품 지정",
    ]

    def evaluate(self, profile: ApplicantProfile, notice: RawNotice) -> MultiAxisEvaluationResult:
        """사업주 프로필과 공고 간의 다차원 매칭을 수행합니다."""
        title = notice.title
        body = (notice.body_text or "") + " " + title
        portal = notice.portal_id

        # 1. 공고 트랙 자동 식별
        track = self._classify_notice_track(title, body)

        pass_reasons: List[str] = []
        bonus_points: List[str] = []
        disqualifications: List[str] = []

        # 2. 업력 요건 자격 검증 (Eligibility Check)
        is_age_eligible, age_reason = self._check_biz_age(profile.biz_age_years, title, body)
        if not is_age_eligible:
            disqualifications.append(age_reason)
        else:
            pass_reasons.append(age_reason)

        # 3. 대표자 신분(청년/여성) 요건 검증
        is_youth = profile.founder_age <= 39
        if "청년" in title or "청년" in body:
            if is_youth:
                pass_reasons.append(f"만 {profile.founder_age}세 청년 대표자 조건 충족")
                bonus_points.append("청년 창업가 전형 적합 (+15점)")
            else:
                disqualifications.append(f"만 {profile.founder_age}세는 청년(만 39세 이하) 전형 지원 불가")

        if "여성" in title or "여성기업" in body:
            if profile.is_female_founder:
                pass_reasons.append("여성 대표자/여성기업 지원 자격 충족")
                bonus_points.append("여성기업 특화 가점 (+10점)")
            elif any(w in title for w in ["여성기업", "여성창업", "여성특화", "여성전용"]) or "여성기업 확인서" in body:
                disqualifications.append("여성기업/여성대표자 전용 공고로 남성 대표자 지원 불가")

        # 4. 지역 요건 검증 (전국 17개 시도 인식 및 배타적 지역 한정 가드레일)
        exclusive_region_terms = [
            "한정", "전용", "타 시도 지원 불가", "타 시도 제외",
            "타 지역 지원 불가", "타지역 지원 불가",
            "소재 기업 전용", "소재 창업기업 한정", "소재한 창업기업 한정",
        ]
        is_region_exclusive = any(term in body for term in exclusive_region_terms)

        target_regions = []
        for reg in NATIONWIDE_REGIONS.values():
            if any(alias in title for alias in reg.aliases) or (is_region_exclusive and any(alias in body for alias in reg.aliases)):
                target_regions.append(reg)

        if target_regions:
            matched = any(reg.name == profile.location or profile.location in reg.aliases for reg in target_regions)
            if matched:
                pass_reasons.append(f"소재지({profile.location}) 부합")
                bonus_points.append(f"{profile.location} 지역 특화 가점 (+10점)")
            elif is_region_exclusive:
                target_names = "/".join(r.name for r in target_regions)
                disqualifications.append(f"해당 지자체({target_names}) 소재 기업 전용 공고로 {profile.location} 소재 기업 지원 불가")

        # 5. 트랙별 특화 매칭 스코어 산정
        if disqualifications:
            return MultiAxisEvaluationResult(
                is_eligible=False,
                match_score=0,
                matched_track=track,
                track_description=track.value,
                pass_reasons=pass_reasons,
                bonus_points=bonus_points,
                disqualification_reasons=disqualifications,
            )

        # 점수 계산
        base_score = 70

        # [케이스 A] 일반 트랙 (창업패키지, 청창사 등): 기술 키워드 무관 전 업종 수용
        if track in (NoticeTrack.GENERAL_STARTUP, NoticeTrack.DEMOGRAPHIC_FOCUSED):
            base_score = 90
            pass_reasons.append("업종 무관 일반 분야 공고로 아이템 제한 없이 신청 가능")

        # [케이스 B] 지역경제 / 로컬 특화 트랙
        elif track == NoticeTrack.REGIONAL_LOCAL:
            if profile.location in title or profile.location in body:
                base_score = 88
                pass_reasons.append(f"{profile.location} 지역 경제 활성화 및 로컬 비즈니스 모델 부합")
            else:
                base_score = 65

        # [케이스 C] 사회서비스 / 마음건강 / 복지 트랙
        elif track == NoticeTrack.SOCIAL_POLICY:
            expanded_keywords = self._get_expanded_keywords(profile.tags)
            matched_kws = [kw for kw in expanded_keywords if kw in body]
            if matched_kws:
                base_score = 92
                pass_reasons.append(f"정책 테마 시맨틱 온톨로지 매칭 성공 ({', '.join(matched_kws[:3])})")
            else:
                base_score = 60

        # [케이스 D] 기술 R&D 트랙
        elif track == NoticeTrack.DEEP_TECH_RND:
            expanded_keywords = self._get_expanded_keywords(profile.tags)
            matched_kws = [kw for kw in expanded_keywords if kw in body]
            if matched_kws:
                base_score = 85
                pass_reasons.append(f"R&D 기술 분야 매칭 ({', '.join(matched_kws[:2])})")
            else:
                base_score = 40
                disqualifications.append("공고의 R&D RFP 기술 분야와 기업 보유 기술 간 접점 부족")

        # [케이스 E] 바우처 트랙
        elif track == NoticeTrack.VOUCHER_BIZ:
            base_score = 85
            pass_reasons.append("비대면 서비스 및 플랫폼 디지털 인프라 도입 바우처 지원 대상")

        # 가점 합산 (최대 100점)
        total_score = min(100, base_score + len(bonus_points) * 5)
        is_eligible = total_score >= 70 and not disqualifications

        return MultiAxisEvaluationResult(
            is_eligible=is_eligible,
            match_score=total_score,
            matched_track=track,
            track_description=track.value,
            pass_reasons=pass_reasons,
            bonus_points=bonus_points,
            disqualification_reasons=disqualifications,
        )

    def _classify_notice_track(self, title: str, body: str) -> NoticeTrack:
        """공고명과 본문을 분석하여 6대 정책 트랙으로 분류"""
        combined = f"{title} {body}"

        if any(kw in combined for kw in self.GENERAL_TRACK_KEYWORDS):
            return NoticeTrack.GENERAL_STARTUP

        if any(kw in combined for kw in ["여성기업", "여성창업", "청년창업", "시니어", "재창업"]):
            return NoticeTrack.DEMOGRAPHIC_FOCUSED

        if any(kw in combined for kw in ["브라이트클럽", "대표 창업기업", "로컬크리에이터", "지역혁신", "마을기업", "지역거점", "지자체"]):
            return NoticeTrack.REGIONAL_LOCAL

        if any(kw in combined for kw in ["사회서비스", "마음건강", "정신건강", "복지", "취약계층", "소셜벤처"]):
            return NoticeTrack.SOCIAL_POLICY

        if any(kw in combined for kw in ["바우처", "비대면", "클라우드지원", "데이터바우처"]):
            return NoticeTrack.VOUCHER_BIZ

        return NoticeTrack.DEEP_TECH_RND

    def _check_biz_age(self, biz_age_years: float, title: str, body: str) -> tuple[bool, str]:
        """업력 요건 부합 여부 판정"""
        combined = f"{title} {body}"

        # 예비창업자 전용
        if "예비창업" in title or "예비창업자" in combined:
            if biz_age_years == 0:
                return True, "예비창업자 조건 충족"
            elif "초기창업" not in combined:
                return False, f"기창업자(업력 {biz_age_years}년)는 예비창업자 전용 공고 지원 불가"

        # 초기창업 (3년 이내)
        if "초기창업" in combined or "3년 이내" in combined:
            if biz_age_years <= 3.0:
                return True, f"업력 {biz_age_years}년으로 초기창업(3년 이내) 조건 충족"
            else:
                return False, f"업력 {biz_age_years}년은 초기창업(3년 이내) 요건 초과"

        # 창업도약 (3년 초과 7년 이내)
        if "창업도약" in combined or "3년 이상 7년 이내" in combined:
            if 3.0 < biz_age_years <= 7.0:
                return True, f"업력 {biz_age_years}년으로 도약기(3~7년) 조건 충족"
            else:
                return False, f"업력 {biz_age_years}년은 도약기(3~7년) 요건 불부합"

        # 7년 이내 일반 창업기업
        if "7년 이내" in combined:
            if biz_age_years <= 7.0:
                return True, f"업력 {biz_age_years}년으로 7년 이내 창업기업 요건 충족"
            else:
                return False, f"업력 {biz_age_years}년은 7년 이내 요건 초과"

        return True, f"업력 {biz_age_years}년 지원 가능"

    def _get_expanded_keywords(self, tags: List[str]) -> Set[str]:
        """아이템 태그로부터 도메인 온톨로지 확장 키워드 집합 생성"""
        result = set(tags)
        for tag in tags:
            for base_word, related_words in self.DOMAIN_ONTOLOGY.items():
                if base_word in tag or tag in base_word:
                    result.update(related_words)
        return result


# ---------------------------------------------------------------------------
# 모듈급 트랙 분류기 (REQ-020: 공고 목록 다차원 탭 필터링 재사용용)
# 공고명/본문만으로 사업 트랙을 식별 (프로필 의존 X → 목록 페이지에서 1건당 저비용 분류)
# ---------------------------------------------------------------------------
_CLASSIFY = MultiAxisMatcher()


def classify_notice_track(title: str, body: str = "") -> NoticeTrack:
    """공고명(+본문)으로부터 6대 정책 트랙을 분류합니다 (웹 탭 필터링/다차원 매칭 재사용용)."""
    return _CLASSIFY._classify_notice_track(title or "", body or "")

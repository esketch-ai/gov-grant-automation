"""
QQAQC GAN Framework · 대한민국 7대 부처/기관 및 지자체 대표 공고 풀
중기부, 과기부, 산업부, 복지부, 방사청, 농식품부, 조달청, 부산/서울 지자체 공고 14선.
"""
from __future__ import annotations

from typing import Any, Dict, List
from src.common.schemas import RawNotice


AGENCY_NOTICE_POOL: List[Dict[str, Any]] = [
    # -------------------------------------------------------------
    # 1. 중소벤처기업부 / 창업진흥원
    # -------------------------------------------------------------
    {
        "notice_id": "N-01-MSS-EARLY-GENERAL",
        "ministry_code": "MSS",
        "agency_name": "중소벤처기업부 / 창업진흥원",
        "raw_notice": RawNotice(
            portal_id="k_startup",
            title="2026년도 초기창업패키지(일반분야) 창업기업 모집공고",
            organization="창업진흥원",
            ministry="중소벤처기업부",
            deadline="2026-11-20 18:00",
            detail_url="https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=175783",
            body_text="창업 3년 이내의 모든 분야 기업 대상. 업종 무관 일반 분야 공고로 아이템 제한 없이 신청 가능.",
        ),
        "target_audience": "업력 3년 이내 스타트업 (전 업종)",
        "hard_filters": {"max_age_years": 3.0},
    },
    {
        "notice_id": "N-02-MSS-YOUTH-ACADEMY",
        "ministry_code": "MSS",
        "agency_name": "중소벤처기업부 / 중소벤처기업진흥공단",
        "raw_notice": RawNotice(
            portal_id="k_startup",
            title="2026년 청년창업사관학교(만 39세 이하) 입교생 모집",
            organization="중소벤처기업진흥공단",
            ministry="중소벤처기업부",
            deadline="2026-11-25 17:00",
            detail_url="https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=175783",
            body_text="만 39세 이하의 청년 창업자만을 대상으로 하며 창업 3년 이내 기업 한정.",
        ),
        "target_audience": "만 39세 이하 청년 + 업력 3년 이내",
        "hard_filters": {"max_founder_age": 39, "max_age_years": 3.0},
    },
    {
        "notice_id": "N-03-MSS-GROWTH-PACKAGE",
        "ministry_code": "MSS",
        "agency_name": "중소벤처기업부 / 창업진흥원",
        "raw_notice": RawNotice(
            portal_id="k_startup",
            title="2026년도 창업도약패키지 지원사업 창업기업 모집",
            organization="창업진흥원",
            ministry="중소벤처기업부",
            deadline="2026-11-28 18:00",
            detail_url="https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=175783",
            body_text="창업 후 3년 초과 7년 이내 도약기 기업 한정. 데스밸리 극복 및 스케일업 자금 지원.",
        ),
        "target_audience": "업력 3년 초과 7년 이내 도약기 기업",
        "hard_filters": {"min_age_years": 3.0, "max_age_years": 7.0},
    },
    {
        "notice_id": "N-04-MSS-FEMALE-GLOBAL",
        "ministry_code": "MSS",
        "agency_name": "중소벤처기업부 / 여성기업종합지원센터",
        "raw_notice": RawNotice(
            portal_id="k_startup",
            title="2026년 여성기업 글로벌 스케일업 및 해외판로 개척 지원사업",
            organization="여성기업종합지원센터",
            ministry="중소벤처기업부",
            deadline="2026-12-05 18:00",
            detail_url="https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=175783",
            body_text="여성기업지원에 관한 법률에 따른 '여성기업 확인서' 보유 필수. 비R&D 판로개척 지원.",
        ),
        "target_audience": "여성대표 여성기업 전용",
        "hard_filters": {"require_female_founder": True},
    },

    # -------------------------------------------------------------
    # 2. 과학기술정보통신부
    # -------------------------------------------------------------
    {
        "notice_id": "N-05-MSIT-LAM-AI",
        "ministry_code": "MSIT",
        "agency_name": "과학기술정보통신부 / IITP",
        "raw_notice": RawNotice(
            portal_id="iris",
            title="2026년 「인간-AI 협업형 LAM 개발·글로벌 실증 」사업 공고",
            organization="정보통신기획평가원(IITP)",
            ministry="과학기술정보통신부",
            deadline="2026-12-10 18:00",
            detail_url="https://www.iris.go.kr/contents/retrieveBsnsAncmView.do?ancmId=022696",
            body_text="기업부설연구소 또는 연구개발전담부서 보유 필수. 거대행동모델(LAM) 및 온디바이스 인공지능 원천 R&D.",
        ),
        "target_audience": "인공지능 딥테크 R&D (연구소 필수)",
        "hard_filters": {"requires_rnd_lab": True},
    },
    {
        "notice_id": "N-06-MSIT-ICT-VOUCHER",
        "ministry_code": "MSIT",
        "agency_name": "과학기술정보통신부 / NIPA",
        "raw_notice": RawNotice(
            portal_id="iris",
            title="2026년도 중소기업 ICT 융합 바우처 지원사업",
            organization="정보통신산업진흥원(NIPA)",
            ministry="과학기술정보통신부",
            deadline="2026-11-30 18:00",
            detail_url="https://www.iris.go.kr/contents/retrieveBsnsAncmView.do?ancmId=022696",
            body_text="AI, 클라우드, 데이터 솔루션을 도입하고자 하는 중소기업 수요처 바우처 지원.",
        ),
        "target_audience": "ICT 솔루션 도입 전 업종 중소기업 (바우처 트랙)",
        "hard_filters": {},
    },

    # -------------------------------------------------------------
    # 3. 산업통상자원부
    # -------------------------------------------------------------
    {
        "notice_id": "N-07-MOTIE-CIRCULAR-CARBON",
        "ministry_code": "MOTIE",
        "agency_name": "산업통상자원부 / KEIT",
        "raw_notice": RawNotice(
            portal_id="iris",
            title="2026년도 순환경제 및 탄소중립 선도 프로젝트 기술개발 공고",
            organization="한국산업기술기획평가원(KEIT)",
            ministry="산업통상자원부",
            deadline="2026-12-15 18:00",
            detail_url="https://www.iris.go.kr/contents/retrieveBsnsAncmView.do?ancmId=022696",
            body_text="탄소배출 감축, 온실가스 모니터링, 순환경제 기술개발. 기업부설연구소 또는 연구개발전담부서 보유 필수. 부채비율 500% 초과 기업 지원 제외.",
        ),
        "target_audience": "탄소중립 / 기후테크 기술 R&D",
        "hard_filters": {"max_debt_ratio": 500.0, "requires_rnd_lab": True},
    },

    # -------------------------------------------------------------
    # 4. 보건복지부
    # -------------------------------------------------------------
    {
        "notice_id": "N-08-MOHW-BIO-DTX",
        "ministry_code": "MOHW",
        "agency_name": "보건복지부 / KHIDI",
        "raw_notice": RawNotice(
            portal_id="iris",
            title="2026년도 바이오헬스 디지털치료기기(DTx) 임상 실증 기술개발사업",
            organization="한국보건산업진흥원(KHIDI)",
            ministry="보건복지부",
            deadline="2026-12-20 18:00",
            detail_url="https://www.iris.go.kr/contents/retrieveBsnsAncmView.do?ancmId=022696",
            body_text="의료기기 임상시험 및 디지털치료제 유효성 검증 R&D. 기업부설연구소 및 식약처 임상계획서 필수.",
        ),
        "target_audience": "바이오헬스 / DTx 의료기기 R&D",
        "hard_filters": {"requires_rnd_lab": True},
    },
    {
        "notice_id": "N-09-MOHW-SOCIAL-SERVICE",
        "ministry_code": "MOHW",
        "agency_name": "보건복지부 / 중앙사회서비스원",
        "raw_notice": RawNotice(
            portal_id="k_startup",
            title="2026년도 사회서비스 투자 R&D 및 소셜벤처 육성사업",
            organization="중앙사회서비스원",
            ministry="보건복지부",
            deadline="2026-11-25 18:00",
            detail_url="https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=175783",
            body_text="돌봄, 심리상담, 취약계층 복지 증진 플랫폼 및 소셜벤처 우대. 비R&D 서비스 실증 지원.",
        ),
        "target_audience": "사회서비스 / 심리상담 / 소셜벤처 / 복지",
        "hard_filters": {},
    },

    # -------------------------------------------------------------
    # 5. 방위사업청
    # -------------------------------------------------------------
    {
        "notice_id": "N-10-DAPA-DEFENSE-VENTURE",
        "ministry_code": "DAPA",
        "agency_name": "방위사업청 / 국방기술진흥연구소",
        "raw_notice": RawNotice(
            portal_id="ntis",
            title="2026년도 국방벤처 혁신기술 지원사업 공고",
            organization="국방기술진흥연구소",
            ministry="방위사업청",
            deadline="2026-12-08 17:00",
            detail_url="https://www.ntis.go.kr/rndgate/eg/un/ra/view.do?roRndUid=1279968",
            body_text="군수 방산, 무인기, 대드론 재밍, 유도무기 관련 하드웨어 부품 국산화 연구개발. 방산 전용.",
        ),
        "target_audience": "방위산업 / 국방 하드웨어 R&D",
        "hard_filters": {},
    },

    # -------------------------------------------------------------
    # 6. 농림축산식품부
    # -------------------------------------------------------------
    {
        "notice_id": "N-11-MAFRA-AGRI-VENTURE",
        "ministry_code": "MAFRA",
        "agency_name": "농림축산식품부 / 한국농업기술진흥원",
        "raw_notice": RawNotice(
            portal_id="k_startup",
            title="2026년도 농식품 벤처육성 지원사업(창업기업 모집)",
            organization="한국농업기술진흥원",
            ministry="농림축산식품부",
            deadline="2026-11-22 18:00",
            detail_url="https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=175783",
            body_text="농업, 식품 가공, 스마트팜, 로컬 농가 연계 기업 지원. 비R&D 및 사업화 자금 지원.",
        ),
        "target_audience": "농식품 / 스마트팜 / 로컬 푸드",
        "hard_filters": {},
    },

    # -------------------------------------------------------------
    # 7. 지자체 및 테크노파크 (부산, 서울)
    # -------------------------------------------------------------
    {
        "notice_id": "N-12-BUSAN-BRIGHT-CLUB",
        "ministry_code": "BUSAN",
        "agency_name": "부산광역시 / 부산테크노파크",
        "raw_notice": RawNotice(
            portal_id="k_startup",
            title="2026년 부산 대표 창업기업 브라이트클럽 육성지원사업",
            organization="부산테크노파크",
            ministry="부산광역시",
            deadline="2026-11-26 18:00",
            detail_url="https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=175783",
            body_text="공고일 기준 본사 또는 주사업장이 부산광역시에 소재한 창업기업 한정. 타 시도 지원 불가.",
        ),
        "target_audience": "부산광역시 소재 스타트업",
        "hard_filters": {"required_region": "부산"},
    },
    {
        "notice_id": "N-13-SEOUL-BIO-HUB",
        "ministry_code": "SEOUL",
        "agency_name": "서울특별시 / 서울바이오허브",
        "raw_notice": RawNotice(
            portal_id="iris",
            title="2026년 서울 바이오 혁신 스타트업 글로벌 실증 지원사업",
            organization="서울바이오허브",
            ministry="서울특별시",
            deadline="2026-12-12 18:00",
            detail_url="https://www.iris.go.kr/contents/retrieveBsnsAncmView.do?ancmId=022696",
            body_text="서울특별시 소재 바이오·의료기기 스타트업 전용. 타 지역 지원 불가.",
        ),
        "target_audience": "서울시 소재 + 바이오헬스 스타트업",
        "hard_filters": {"required_region": "서울"},
    },

    # -------------------------------------------------------------
    # 8. 조달청 나라장터
    # -------------------------------------------------------------
    {
        "notice_id": "N-14-PPS-INNOVATIVE-PRODUCT",
        "ministry_code": "PPS",
        "agency_name": "조달청 / 나라장터",
        "raw_notice": RawNotice(
            portal_id="g2b",
            title="2026년 제1차 조달청 혁신시제품 지정 공고",
            organization="조달청",
            ministry="기획재정부",
            deadline="2026-12-25 18:00",
            detail_url="https://www.g2b.go.kr:8081/ep/invitation/publish/bidInfoDtl.do?bidno=20261009120&bidseq=00&releaseYn=Y&taskClCd=5",
            body_text="상용화 직전 시제품(TRL 7 이상) 보유 기업 대상. 공공기관 테스트베드 매칭 및 수의계약 지원.",
        ),
        "target_audience": "시제품 보유 조달 혁신기업 (전 업종)",
        "hard_filters": {},
    },
]

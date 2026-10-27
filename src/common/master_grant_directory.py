"""
대한민국 중앙부처 및 17개 지자체 창업지원사업 통합공고 종합 정리함 마스터 디렉토리
(K-Startup 통합공고문 종합 안내책자 기반 정형 카탈로그)
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class MasterGrantProgram:
    """통합공고 마스터 지원사업 프로그램 스키마."""
    program_id: str             # 고유 ID (예: "MSS-PRE-2026")
    program_name: str           # 사업명 (예: "예비창업패키지")
    category: str               # 지원유형 ("사업화", "기술개발(R&D)", "시설·공간·보육", "멘토링·컨설팅", "글로벌", "융자·보증")
    supervising_ministry: str   # 소관 부처 (중소벤처기업부, 과학기술정보통신부, 산업통상자원부 등)
    operating_agency: str       # 전담/주관 기관 (창업진흥원, 한국지능정보사회진흥원, 테크노파크 등)
    region_scope: str           # 대상 지역 ("전국", "서울", "경기", "부산", "대전", "대구" 등)
    target_stage: str           # 지원 대상 단계 ("예비창업자", "초기창업(3년이내)", "창업도약(3~7년)", "성장기업(7년이내)", "전단계")
    target_qualifications: str  # 상세 지원 자격 (연령, 업종, 기술요건)
    expected_period: str        # 사업공고 개략적 시기 (예: "2026년 2월", "2026년 3월", "연중 수시")
    expected_month: int         # 정렬용 대표 월 (1~12, 수시는 0)
    support_scale: str          # 지원 규모 / 한도 (예: "최대 1억원", "최대 5억원")
    support_details: str        # 주요 지원 내용 요약
    inquiry_contact: str        # 문의처 / 대표 사이트
    source_portal: str          # 연결 포털 ID ("k_startup", "iris", "ntis", "g2b" 등)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------
# 대한민국 중앙부처 및 전국 17개 지자체 대표 통합공고 카탈로그 (SSOT)
# --------------------------------------------------------------------------
MASTER_GRANT_CATALOG: List[MasterGrantProgram] = [
    # =========================================================================
    # 1. 중소벤처기업부 / 창업진흥원 (핵심 패키지 & TIPS)
    # =========================================================================
    MasterGrantProgram(
        program_id="MSS-PRE-PACKAGE-2026",
        program_name="2026년도 예비창업패키지",
        category="사업화",
        supervising_ministry="중소벤처기업부",
        operating_agency="창업진흥원 / 창경센터",
        region_scope="전국",
        target_stage="예비창업자",
        target_qualifications="사업공고일까지 창업경험이 없거나 사업자등록이 없는 예비창업자",
        expected_period="2026년 2월",
        expected_month=2,
        support_scale="최대 1억원 (평균 5,000만원)",
        support_details="시제품 제작, 지식재산권 취득, 마케팅 등 사업화 자금 및 창업 멘토링 바우처 지원",
        inquiry_contact="창업진흥원 (국번없이 1357) / k-startup.go.kr",
        source_portal="k_startup",
    ),
    MasterGrantProgram(
        program_id="MSS-EARLY-PACKAGE-2026",
        program_name="2026년도 초기창업패키지",
        category="사업화",
        supervising_ministry="중소벤처기업부",
        operating_agency="창업진흥원 / 주관대학·기관",
        region_scope="전국",
        target_stage="초기창업(3년이내)",
        target_qualifications="창업 후 3년 이내 기업 (청년, 일반, 딥테크 전 분야)",
        expected_period="2026년 2월 ~ 3월",
        expected_month=2,
        support_scale="최대 1억원 (평균 7,000만원)",
        support_details="초기 창업기업의 안정화 및 시장 안착을 위한 시제품 개선, 사업화 자금, 판로 개척 지원",
        inquiry_contact="창업진흥원 (1357) / k-startup.go.kr",
        source_portal="k_startup",
    ),
    MasterGrantProgram(
        program_id="MSS-LEAP-PACKAGE-2026",
        program_name="2026년도 창업도약패키지",
        category="사업화",
        supervising_ministry="중소벤처기업부",
        operating_agency="창업진흥원 / 대기업 파트너",
        region_scope="전국",
        target_stage="창업도약(3~7년)",
        target_qualifications="창업 후 3년 초과 7년 이내 도약기 기업 (데스밸리 극복)",
        expected_period="2026년 3월",
        expected_month=3,
        support_scale="최대 3억원 (평균 1.2억원)",
        support_details="사업아이템 고도화, 대기업 협업 프로그램, 글로벌 스케일업 및 후속 투자 연계",
        inquiry_contact="창업진흥원 (1357) / k-startup.go.kr",
        source_portal="k_startup",
    ),
    MasterGrantProgram(
        program_id="MSS-TIPS-RND-2026",
        program_name="2026년도 민간투자주도형 기술창업지원(TIPS R&D)",
        category="기술개발(R&D)",
        supervising_ministry="중소벤처기업부",
        operating_agency="한국엔젤투자협회 / TIPS운영사",
        region_scope="전국",
        target_stage="성장기업(7년이내)",
        target_qualifications="TIPS 운영사로부터 1억원~2억원 이상 선투자 유치 기업",
        expected_period="연중 수시 (매월/격월 선정)",
        expected_month=0,
        support_scale="최대 5억원 R&D 연구비 + 사업화 1억원 + 해외마케팅 1억원",
        support_details="민간 엔젤투자사와 매칭하여 우수 기술 창업기업을 발굴, 정부 R&D 출연금 5억원 일괄 지원",
        inquiry_contact="한국엔젤투자협회 (02-3440-7422) / jointips.or.kr",
        source_portal="smtech",
    ),
    MasterGrantProgram(
        program_id="MSS-SUPER-GAP-2026",
        program_name="2026년도 초격차 스타트업 1000+ 프로젝트 (DIPS)",
        category="사업화",
        supervising_ministry="중소벤처기업부",
        operating_agency="창업진흥원 / 전문기술기관",
        region_scope="전국",
        target_stage="성장기업(7년이내)",
        target_qualifications="10대 초격차 분야(AI, 시스템반도체, 모빌리티, 바이오 등) 10년 이내 창업기업",
        expected_period="2026년 1월 ~ 2월",
        expected_month=1,
        support_scale="최대 6억원 (3년간 연 2억원) + R&D 5억원 연계",
        support_details="독보적인 기술력을 보유한 초격차 분야 스타트업의 글로벌 유니콘 육성 집중 스케일업 지원",
        inquiry_contact="창업진흥원 신산업창업실 (044-410-1681)",
        source_portal="k_startup",
    ),
    MasterGrantProgram(
        program_id="MSS-YOUTH-ACADEMY-2026",
        program_name="2026년 청년창업사관학교 입교생 모집",
        category="시설·공간·보육",
        supervising_ministry="중소벤처기업부",
        operating_agency="중소벤처기업진흥공단(KOSME)",
        region_scope="전국 (18개 지역 캠퍼스)",
        target_stage="초기창업(3년이내)",
        target_qualifications="만 39세 이하 청년 또는 창업 3년 이내 기업 대표자",
        expected_period="2026년 1월",
        expected_month=1,
        support_scale="최대 1억원 사업비 (총사업비 70% 이내) + 전용 입주공간",
        support_details="창업공간 무료 제공, 시제품 제작 인프라, 전담 코칭, 사업화 자금 원스톱 풀코스 지원",
        inquiry_contact="중진공 청년창업사관학교 (031-490-1278) / start.kosmes.or.kr",
        source_portal="k_startup",
    ),

    # =========================================================================
    # 2. 과학기술정보통신부 (AI, SW, 데이터 바우처)
    # =========================================================================
    MasterGrantProgram(
        program_id="MSIT-AI-VOUCHER-2026",
        program_name="2026년도 AI 바우처 지원사업",
        category="사업화",
        supervising_ministry="과학기술정보통신부",
        operating_agency="정보통신산업진흥원 (NIPA)",
        region_scope="전국",
        target_stage="전단계",
        target_qualifications="AI 솔루션을 도입하여 비즈니스 혁신을 추진하고자 하는 중소·벤처·스타트업",
        expected_period="2026년 2월 ~ 3월",
        expected_month=2,
        support_scale="최대 3억원 바우처",
        support_details="AI 공급기업의 솔루션 구매 및 맞춤형 알고리즘 도입 비용 바우처 일괄 지원",
        inquiry_contact="정보통신산업진흥원 AI산업기반팀 (043-931-5750) / nipa.kr",
        source_portal="nipa",
    ),
    MasterGrantProgram(
        program_id="MSIT-DATA-VOUCHER-2026",
        program_name="2026년도 데이터 바우처 지원사업",
        category="사업화",
        supervising_ministry="과학기술정보통신부",
        operating_agency="한국데이터산업진흥원 (K-DATA)",
        region_scope="전국",
        target_stage="전단계",
        target_qualifications="데이터 구매 및 가공을 통해 신제품·서비스를 개발하려는 스타트업/소상공인",
        expected_period="2026년 3월",
        expected_month=3,
        support_scale="일반가공 최대 4,500만원 / AI가공 최대 6,000만원",
        support_details="비즈니스 모델 고도화에 필요한 빅데이터 구매 및 AI 가공 서비스 바우처 제공",
        inquiry_contact="한국데이터산업진흥원 바우처추진단 (1833-2288) / kdata.or.kr",
        source_portal="iris",
    ),
    MasterGrantProgram(
        program_id="MSIT-K-GLOBAL-2026",
        program_name="2026년 K-Global 프로젝트 (글로벌 액셀러레이팅)",
        category="글로벌",
        supervising_ministry="과학기술정보통신부",
        operating_agency="정보통신산업진흥원 / 본투글로벌",
        region_scope="전국",
        target_stage="성장기업(7년이내)",
        target_qualifications="글로벌 시장 진출을 희망하는 ICT 유망 스타트업",
        expected_period="2026년 3월",
        expected_month=3,
        support_scale="최대 1억원 해외 진출 사업화 자금 + 현지 엑셀러레이팅",
        support_details="미국(실리콘밸리), 동남아, 유럽 등 해외 주요 권역 현지 런칭 및 글로벌 투자 유치",
        inquiry_contact="정보통신산업진흥원 글로벌성장팀 (043-931-5531)",
        source_portal="nipa",
    ),

    # =========================================================================
    # 3. 산업통상자원부 & 조달청 (R&BD 및 혁신조달)
    # =========================================================================
    MasterGrantProgram(
        program_id="MOTIE-RNBD-SCALEUP-2026",
        program_name="2026년 사업화연계기술개발사업 (R&BD 스케일업)",
        category="기술개발(R&D)",
        supervising_ministry="산업통상자원부",
        operating_agency="한국산업기술진흥원 (KIAT)",
        region_scope="전국",
        target_stage="성장기업(7년이내)",
        target_qualifications="기존 보유 기술(TRL 5~6 이상)의 상용화 및 양산을 추진하는 기술혁신기업",
        expected_period="2026년 3월 ~ 4월",
        expected_month=3,
        support_scale="최대 5억원 연구개발 지원금 (총 2개년 지원)",
        support_details="시제품 실증 시험, 양산 설계, 공정 혁신, 신뢰성 평가 등 상용화 R&BD 비용 지원",
        inquiry_contact="한국산업기술진흥원 사업화지원실 (02-6009-8000) / kiat.or.kr",
        source_portal="iris",
    ),
    MasterGrantProgram(
        program_id="PPS-INNOVATIVE-PRODUCT-2026",
        program_name="2026년 조달청 혁신시제품 지정 및 공공 테스트베드 지원",
        category="사업화",
        supervising_ministry="조달청 (기획재정부)",
        operating_agency="조달청 혁신조달기획관",
        region_scope="전국",
        target_stage="전단계",
        target_qualifications="상용화 직전(TRL 7 이상) 혁신 기술 제품을 보유한 기업",
        expected_period="2026년 2월, 5월, 8월 (분기별 회차)",
        expected_month=2,
        support_scale="최대 5억원 공공기관 테스트베드 구매 연계 + 3년간 수의계약 자격",
        support_details="조달청 예산으로 시제품을 선구매하여 공공기관에 무상 제공, 현장 실증 후 우수조달물품 직행",
        inquiry_contact="조달청 혁신조달운영과 (042-724-7221) / ppi.g2b.go.kr",
        source_portal="g2b",
    ),

    # =========================================================================
    # 4. 보건복지부 / 농식품부 / 방사청 특화
    # =========================================================================
    MasterGrantProgram(
        program_id="MOHW-BIO-STARTUP-2026",
        program_name="2026년 보건산업 초기 창업기업 육성 지원사업",
        category="사업화",
        supervising_ministry="보건복지부",
        operating_agency="한국보건산업진흥원 (KHIDI)",
        region_scope="전국",
        target_stage="초기창업(3년이내)",
        target_qualifications="의료기기, 디지털치료제(DTx), 스마트헬스케어, 바이오 창업 3년 이내 기업",
        expected_period="2026년 2월",
        expected_month=2,
        support_scale="최대 1.2억원 사업화 자금 + 병원 임상 컨설팅",
        support_details="식약처 인허가 코칭, 대학병원 전임상/임상 연계 및 의료기기 GMP 컨설팅",
        inquiry_contact="한국보건산업진흥원 보건산업육성단 (02-2095-1730)",
        source_portal="khidi",
    ),
    MasterGrantProgram(
        program_id="MAFRA-AGRITECH-VENTURE-2026",
        program_name="2026년 농식품 벤처창업 활성화 지원사업",
        category="사업화",
        supervising_ministry="농림축산식품부",
        operating_agency="한국농업기술진흥원 (KOAT)",
        region_scope="전국",
        target_stage="성장기업(7년이내)",
        target_qualifications="스마트팜, 그린바이오, 농식품 가공 푸드테크 기술 보유 창업기업",
        expected_period="2026년 2월 ~ 3월",
        expected_month=2,
        support_scale="최대 5,000만원 사업화 자금 + 크라우드펀딩 연계",
        support_details="농업기술 실용화 실증 테스트베드 제공, 농식품 투자 펀드 매칭 IR",
        inquiry_contact="한국농업기술진흥원 벤처창업본부 (063-919-1412)",
        source_portal="iris",
    ),
    MasterGrantProgram(
        program_id="DAPA-FAST-DEFENSE-2026",
        program_name="2026년 국방 신속연구개발사업(드론·AI·무인체계)",
        category="기술개발(R&D)",
        supervising_ministry="방위사업청",
        operating_agency="국방기술진흥연구소 (KRIT)",
        region_scope="전국",
        target_stage="전단계",
        target_qualifications="민간 첨단 신기술(드론, 안티드론, 자율로봇, 센서) 군 적용 가능 기업",
        expected_period="2026년 3월",
        expected_month=3,
        support_scale="과제당 10억원 ~ 30억원 (2개년 군 시험평가 연계)",
        support_details="민간의 성숙된 4차 산업혁명 기술을 군 전력화 체계에 신속 적용하는 R&D 전폭 지원",
        inquiry_contact="국방기술진흥연구소 신속획득기획팀 (055-751-5114)",
        source_portal="iris",
    ),

    # =========================================================================
    # 5. 전국 17개 지자체 특화 대표 창업지원사업 (지역별 포털 매핑)
    # =========================================================================
    # 1) 서울
    MasterGrantProgram(
        program_id="SEOUL-INNOVATION-RND-2026",
        program_name="2026년 서울형 R&D 혁신기술 지원사업",
        category="기술개발(R&D)",
        supervising_ministry="서울특별시",
        operating_agency="서울경제진흥원 (SBA) / 서울테크노파크",
        region_scope="서울",
        target_stage="성장기업(7년이내)",
        target_qualifications="서울시 소재 법인/개인사업자 (바이오·AI·로봇 혁신기술 보유 기업)",
        expected_period="2026년 3월",
        expected_month=3,
        support_scale="최대 2억원 연구개발비",
        support_details="서울 4대 미래신산업(AI, 바이오, 핀테크, 로봇) 기술 상용화 및 실증비 전액 지원",
        inquiry_contact="서울경제진흥원 R&D지원팀 (02-2222-3831) / sba.seoul.kr",
        source_portal="iris",
    ),
    # 2) 부산
    MasterGrantProgram(
        program_id="BUSAN-BRIGHT-CLUB-2026",
        program_name="2026년 부산 대표 창업기업 육성(브라이트클럽)",
        category="사업화",
        supervising_ministry="부산광역시",
        operating_agency="부산테크노파크 / 부산창조경제혁신센터",
        region_scope="부산",
        target_stage="초기창업(3년이내)",
        target_qualifications="부산광역시 관내에 본사를 둔 창업 7년 이내 유망 스타트업",
        expected_period="2026년 2월 ~ 3월",
        expected_month=2,
        support_scale="기업당 최대 2,500만원 사업화 바우처 + 부산시 시드펀드 매칭",
        support_details="부산시 인증 브라이트클럽 현판 수여, 지자체 사업화 자금, 부산창경 오픈이노베이션 연계",
        inquiry_contact="부산테크노파크 창업지원센터 (051-921-6002) / btp.or.kr",
        source_portal="k_startup",
    ),
    # 3) 경기
    MasterGrantProgram(
        program_id="GG-STAR-VENTURE-2026",
        program_name="2026년 경기도 스타트업 랩(Lab) 지원사업",
        category="시설·공간·보육",
        supervising_ministry="경기도",
        operating_agency="경기도경제과학진흥원 (GBSA) / 경기테크노파크",
        region_scope="경기",
        target_stage="초기창업(3년이내)",
        target_qualifications="경기도 소재 또는 판교/수원 테크노밸리 이전 예정 창업기업",
        expected_period="2026년 2월",
        expected_month=2,
        support_scale="최대 3,000만원 사업화 지원금 + 판교 오픈오피스 2년 무상",
        support_details="판교테크노밸리 거점 사무공간, 시제품 제작 팹랩(FabLab), 글로벌 IR 기회 제공",
        inquiry_contact="경기도경제과학진흥원 스타트업성장팀 (031-776-4800) / gbsa.or.kr",
        source_portal="k_startup",
    ),
    # 4) 인천
    MasterGrantProgram(
        program_id="INCHEON-STARTUP-PARK-2026",
        program_name="2026년 인천 스타트업파크 혁신 실증(PoC) 지원사업",
        category="사업화",
        supervising_ministry="인천광역시",
        operating_agency="인천테크노파크 (인천TP)",
        region_scope="인천",
        target_stage="성장기업(7년이내)",
        target_qualifications="인천 스타트업파크(송도) 입주 및 실증 인프라 활용 희망 기업",
        expected_period="2026년 3월",
        expected_month=3,
        support_scale="과제당 최대 5,000만원 실증비 + 송도 스마트시티 인프라",
        support_details="인천 송도·영종·청라 스마트시티 공공 인프라를 활용한 실증 테스트베드 지원",
        inquiry_contact="인천테크노파크 스타트업파크센터 (032-228-1200)",
        source_portal="k_startup",
    ),
    # 5) 대전
    MasterGrantProgram(
        program_id="DAEJEON-D-UNICORN-2026",
        program_name="2026년 대전 D-유니콘 육성 프로젝트",
        category="사업화",
        supervising_ministry="대전광역시",
        operating_agency="대전테크노파크 / 대덕연구개발특구",
        region_scope="대전",
        target_stage="성장기업(7년이내)",
        target_qualifications="대전 대덕특구 및 관내 본사 소재 딥테크(출연연 기술이전) 스타트업",
        expected_period="2026년 3월",
        expected_month=3,
        support_scale="기업당 최대 1억원 스케일업 자금 + 글로벌 투자 연계",
        support_details="정부출연연구기관과의 공동 R&D, 대덕특구 규제샌드박스 및 CES 혁신상 출품 전액 지원",
        inquiry_contact="대전테크노파크 기술사업화단 (042-930-4811)",
        source_portal="iris",
    ),
    # 6) 대구
    MasterGrantProgram(
        program_id="DAEGU-ABB-GROWTH-2026",
        program_name="2026년 대구 미래 5대 신산업(ABB: AI·BigData·Blockchain) 육성",
        category="기술개발(R&D)",
        supervising_ministry="대구광역시",
        operating_agency="대구테크노파크 (대구TP) / 대구디지털혁신진흥원",
        region_scope="대구",
        target_stage="초기창업(3년이내)",
        target_qualifications="대구 수성알파시티 및 관내 소재 AI/소프트웨어 혁신 스타트업",
        expected_period="2026년 3월",
        expected_month=3,
        support_scale="최대 7,000만원 기술개발비",
        support_details="수성알파시티 AI 데이터센터 인프라 무료 이용, 소프트웨어 제품 상용화 바우처 지원",
        inquiry_contact="대구디지털혁신진흥원 (053-655-5600)",
        source_portal="k_startup",
    ),
    # 7) 광주
    MasterGrantProgram(
        program_id="GWANGJU-AI-VALLEY-2026",
        program_name="2026년 광주 AI 중심도시 창업실증 지원사업",
        category="사업화",
        supervising_ministry="광주광역시",
        operating_agency="인공지능산업융합사업단 (AICA) / 광주창경",
        region_scope="광주",
        target_stage="성장기업(7년이내)",
        target_qualifications="국가 AI 데이터센터(첨단3지구) 고성능 컴퓨팅 자원을 활용하는 AI 스타트업",
        expected_period="2026년 2월",
        expected_month=2,
        support_scale="최대 1억원 실증비 + GPU 슈퍼컴퓨터 자원 무상 제공",
        support_details="광주 첨단지구 데이터센터 초거대 AI GPU 클러스터 무상 할당 및 실증 지원",
        inquiry_contact="인공지능산업융합사업단 창업지원팀 (062-610-3940)",
        source_portal="nipa",
    ),
    # 8) 울산
    MasterGrantProgram(
        program_id="ULSAN-SMART-MOBILITY-2026",
        program_name="2026년 울산 친환경 스마트모빌리티 창업기업 지원",
        category="사업화",
        supervising_ministry="울산광역시",
        operating_agency="울산테크노파크 / 울산창조경제혁신센터",
        region_scope="울산",
        target_stage="초기창업(3년이내)",
        target_qualifications="수소/전기차, 자율주행, 스마트선박 분야 부품·소프트웨어 창업기업",
        expected_period="2026년 3월",
        expected_month=3,
        support_scale="최대 4,000만원 사업화 자금",
        support_details="현대차/현대중공업 대기업 오픈이노베이션 밋업, 울산 테크노산단 입주 연계",
        inquiry_contact="울산테크노파크 기업지원단 (052-219-8611)",
        source_portal="k_startup",
    ),
    # 9) 강원
    MasterGrantProgram(
        program_id="GANGWON-BIO-TOUR-2026",
        program_name="2026년 강원 바이오헬스·디지털치료기기 벤처 육성",
        category="기술개발(R&D)",
        supervising_ministry="강원특별자치도",
        operating_agency="강원테크노파크 / 원주의료기기테크노밸리",
        region_scope="강원",
        target_stage="성장기업(7년이내)",
        target_qualifications="강원도 춘천/원주 바이오 및 디지털헬스케어 규제자유특구 이전·창업기업",
        expected_period="2026년 3월",
        expected_month=3,
        support_scale="최대 8,000만원 시제품 제작 및 인허가 비용",
        support_details="강원 규제자유특구 특례를 통한 비대면 진료 및 디지털치료제 실증 지원",
        inquiry_contact="원주의료기기테크노밸리 (033-760-6100)",
        source_portal="iris",
    ),
    # 10) 충북
    MasterGrantProgram(
        program_id="CHUNGBUK-K-BATTERY-2026",
        program_name="2026년 충북 K-배터리 및 바이오 첨단산업 스타트업 육성",
        category="사업화",
        supervising_ministry="충청북도",
        operating_agency="충북테크노파크 / 오송바이오진흥재단",
        region_scope="충북",
        target_stage="성장기업(7년이내)",
        target_qualifications="오창 이차전지 국가첨단전략산업 특화단지 또는 오송 바이오밸리 소재 기업",
        expected_period="2026년 3월",
        expected_month=3,
        support_scale="최대 5,000만원 사업화 자금",
        support_details="이차전지 소재/부품/장비 성능평가 시험비 지원 및 오송 첨단의료복합단지 연계",
        inquiry_contact="충북테크노파크 기업지원단 (043-270-2000)",
        source_portal="k_startup",
    ),
    # 11) 충남
    MasterGrantProgram(
        program_id="CHUNGNAM-DISPLAY-MOBILITY-2026",
        program_name="2026년 충남 차세대 디스플레이·미래차 스타트업 스케일업",
        category="사업화",
        supervising_ministry="충청남도",
        operating_agency="충남테크노파크 / 천안아산 창경센터",
        region_scope="충남",
        target_stage="성장기업(7년이내)",
        target_qualifications="천안, 아산 디스플레이 및 자동차 부품 특화단지 소재 기업",
        expected_period="2026년 4월",
        expected_month=4,
        support_scale="최대 4,500만원 사업화 자금",
        support_details="대기업 공급망 진입을 위한 신뢰성 인증비 및 글로벌 바이어 매칭",
        inquiry_contact="충남테크노파크 (041-589-0600)",
        source_portal="k_startup",
    ),
    # 12) 전북
    MasterGrantProgram(
        program_id="JEONBUK-AGRI-BIO-2026",
        program_name="2026년 전북 농생명·새만금 이차전지 유망 창업기업 육성",
        category="사업화",
        supervising_ministry="전북특별자치도",
        operating_agency="전북테크노파크 / 전북창조경제혁신센터",
        region_scope="전북",
        target_stage="초기창업(3년이내)",
        target_qualifications="전주 농생명클러스터 또는 익산 국가식품클러스터, 군산 새만금 산단 소재 기업",
        expected_period="2026년 2월 ~ 3월",
        expected_month=2,
        support_scale="최대 4,000만원 사업화 지원금",
        support_details="국가식품클러스터 파일럿 플랜트 장비 무상 사용, 농식품 모태펀드 투자 연계",
        inquiry_contact="전북창조경제혁신센터 (063-220-8900)",
        source_portal="k_startup",
    ),
    # 13) 전남
    MasterGrantProgram(
        program_id="JEONNAM-GREEN-ENERGY-2026",
        program_name="2026년 전남 해상풍력 및 블루이코노미 에너지 창업",
        category="사업화",
        supervising_ministry="전라남도",
        operating_agency="전남테크노파크 / 나주 에너지밸리",
        region_scope="전남",
        target_stage="성장기업(7년이내)",
        target_qualifications="나주 빛가람혁신도시 한전 에너지밸리 입주 및 신재생에너지 기업",
        expected_period="2026년 3월",
        expected_month=3,
        support_scale="최대 5,000만원 사업화 바우처 + 한전 협력기업 등록",
        support_details="한국전력공사 기술멘토링, 해상풍력 실증단지 참여 기회 제공",
        inquiry_contact="전남테크노파크 에너지센터 (061-729-2800)",
        source_portal="k_startup",
    ),
    # 14) 경북
    MasterGrantProgram(
        program_id="GYEONGBUK-BATTERY-AI-2026",
        program_name="2026년 경북 규제자유특구(이차전지·스마트팩토리) 유망 스타트업",
        category="사업화",
        supervising_ministry="경상북도",
        operating_agency="경북테크노파크 / 포항금속소재산업진흥원",
        region_scope="경북",
        target_stage="성장기업(7년이내)",
        target_qualifications="포항, 구미, 경산 소재 이차전지 재활용 및 AI 스마트팩토리 솔루션 기업",
        expected_period="2026년 3월",
        expected_month=3,
        support_scale="최대 5,000만원 사업화 바우처",
        support_details="포스텍(POSTECH) 연구진 기술 자문 및 포스코 체인지업그라운드 입주 우대",
        inquiry_contact="경북테크노파크 (053-819-3000)",
        source_portal="k_startup",
    ),
    # 15) 경남
    MasterGrantProgram(
        program_id="GYEONGNAM-AEROSPACE-DEFENSE-2026",
        program_name="2026년 경남 우주항공·방위산업 테크 스타트업 육성",
        category="기술개발(R&D)",
        supervising_ministry="경상남도",
        operating_agency="경남테크노파크 / 사천 우주항공청 연계",
        region_scope="경남",
        target_stage="성장기업(7년이내)",
        target_qualifications="사천, 창원, 진주 소재 우주항공청(KASA) 연계 항공우주 및 정밀 방산 중소기업",
        expected_period="2026년 3월 ~ 4월",
        expected_month=3,
        support_scale="최대 1억원 R&D 연구개발비",
        support_details="한국항공우주산업(KAI), 한화에어로스페이스 협력업체 등록 및 비행시험 지원",
        inquiry_contact="경남테크노파크 우주항공본부 (055-259-3300)",
        source_portal="iris",
    ),
    # 16) 제주
    MasterGrantProgram(
        program_id="JEJU-SMART-ISLAND-2026",
        program_name="2026년 제주 스마트아일랜드(관광·카본프리) 스타트업 지원",
        category="사업화",
        supervising_ministry="제주특별자치도",
        operating_agency="제주테크노파크 / 제주창조경제혁신센터",
        region_scope="제주",
        target_stage="초기창업(3년이내)",
        target_qualifications="제주도 소재 또는 이전 희망 친환경 모빌리티, 워케이션, 스마트관광 스타트업",
        expected_period="2026년 3월",
        expected_month=3,
        support_scale="최대 3,500만원 사업화 자금 + 제주 전용 펀드 매칭",
        support_details="제주 워케이션 공유오피스 입주, 카카오/넥슨 협력 멘토링 프로그램",
        inquiry_contact="제주창조경제혁신센터 (064-710-1900)",
        source_portal="k_startup",
    ),
    # 17) 세종
    MasterGrantProgram(
        program_id="SEJONG-SMART-CITY-2026",
        program_name="2026년 세종 자율주행·스마트시티 규제샌드박스 창업지원",
        category="기술개발(R&D)",
        supervising_ministry="세종특별자치시",
        operating_agency="세종테크노파크 / 고려대 세종산학단",
        region_scope="세종",
        target_stage="초기창업(3년이내)",
        target_qualifications="세종시 자율주행 규제자유특구 및 스마트국가산단 입주 혁신기업",
        expected_period="2026년 2월 ~ 3월",
        expected_month=2,
        support_scale="최대 5,000만원 시제품 제작비 + BRT 전용 실증도로 제공",
        support_details="세종 중앙공원 및 BRT 자율주행 도로 실증 테스트 지원",
        inquiry_contact="세종테크노파크 (044-850-2100)",
        source_portal="iris",
    ),
]


class MasterGrantService:
    """통합공고 총람 마스터 데이터 검색, 필터링 및 타임라인 로드맵 서비스."""

    def __init__(self, catalog: Optional[List[MasterGrantProgram]] = None) -> None:
        self._catalog = catalog or MASTER_GRANT_CATALOG

    def get_all_programs(
        self,
        region: Optional[str] = None,
        agency: Optional[str] = None,
        category: Optional[str] = None,
        month: Optional[int] = None,
        keyword: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """조건별 통합공고 과제 목록 필터링."""
        results: List[Dict[str, Any]] = []
        kw = keyword.lower().strip() if keyword else None

        for prog in self._catalog:
            # 1. 지역 필터 (전국 공고는 항상 포함, 또는 특정 지역 매칭)
            if region and region != "전국":
                if prog.region_scope != "전국" and region not in prog.region_scope:
                    continue

            # 2. 전담기관 필터
            if agency and agency not in prog.operating_agency:
                continue

            # 3. 지원유형 필터
            if category and category != "전체":
                if category != prog.category and category not in prog.category:
                    continue

            # 4. 공고시기(월) 필터
            if month is not None and month > 0:
                if prog.expected_month != month and prog.expected_month != 0:
                    continue

            # 5. 키워드 검색
            if kw:
                haystack = f"{prog.program_name} {prog.support_details} {prog.target_qualifications} {prog.operating_agency} {prog.supervising_ministry}".lower()
                if kw not in haystack:
                    continue

            results.append(prog.to_dict())

        return results

    def get_monthly_timeline(self) -> Dict[str, List[Dict[str, Any]]]:
        """월별(1~12월, 연중수시) 공고 예정 타임라인 구성."""
        timeline: Dict[str, List[Dict[str, Any]]] = {
            "1월": [],
            "2월": [],
            "3월": [],
            "4월": [],
            "5월~하반기": [],
            "연중 수시": [],
        }

        for prog in self._catalog:
            m = prog.expected_month
            if m == 1:
                timeline["1월"].append(prog.to_dict())
            elif m == 2:
                timeline["2월"].append(prog.to_dict())
            elif m == 3:
                timeline["3월"].append(prog.to_dict())
            elif m == 4:
                timeline["4월"].append(prog.to_dict())
            elif m >= 5:
                timeline["5월~하반기"].append(prog.to_dict())
            else:
                timeline["연중 수시"].append(prog.to_dict())

        return timeline

    def recommend_roadmap_for_item(self, item_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """사업 아이템의 프로필(업력, 지역, 기술분야)에 기반한 연간 추천 과제 로드맵 도출."""
        specs = item_profile.get("company_specs", {})
        meta = item_profile.get("item_meta", {})
        keywords = item_profile.get("domain_routing", {}).get("core_keywords", [])
        keywords_str = " ".join(keywords).lower()
        address = specs.get("address", "")

        # 지역 감지
        target_region = None
        for reg in ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]:
            if reg in address:
                target_region = reg
                break

        recommendations = []
        for prog in self._catalog:
            score = 50  # 기본 점수
            reasons = []

            # 1. 지역 적합성
            if prog.region_scope == "전국":
                score += 20
                reasons.append("전국 지원 가능 공고")
            elif target_region and target_region in prog.region_scope:
                score += 35
                reasons.append(f"소재지({target_region}) 전용 지자체 특화 공고")
            elif target_region and prog.region_scope != "전국":
                # 타지역 전용 공고는 제외
                continue

            # 2. 키워드/기술분야 적합성
            p_text = f"{prog.program_name} {prog.support_details} {prog.target_qualifications}".lower()
            matched_kws = [k for k in keywords if k.lower() in p_text]
            if matched_kws:
                score += min(30, len(matched_kws) * 15)
                reasons.append(f"핵심 키워드({', '.join(matched_kws[:2])}) 일치")

            # 3. 업력 적합성
            # 신규 등록 아이템은 초기창업/예비창업 우대
            if "초기창업" in prog.target_stage:
                score += 15
                reasons.append("창업 3년 이내 패키지")

            if score >= 65:
                item_dict = prog.to_dict()
                item_dict["recommendation_score"] = min(100, score)
                item_dict["recommendation_reasons"] = reasons
                recommendations.append(item_dict)

        recommendations.sort(key=lambda x: x["recommendation_score"], reverse=True)
        return recommendations

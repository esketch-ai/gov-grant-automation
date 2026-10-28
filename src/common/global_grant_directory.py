"""
해외 주요 선진국 및 거점 도시 특화 지원사업 마스터 디렉토리
(영국 DBT GEP, 프랑스 Cité/Station F, 호주 Austrade/Landing Pad, UAE Hub71, 대한민국 KSC)
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class GlobalGrantProgram:
    """해외 거점 국가/도시별 특화 지원사업 스키마."""
    program_id: str             # 고유 ID (예: "UK-DBT-GEP-2026")
    country: str                # 국가 ("영국", "프랑스", "호주", "UAE", "대한민국")
    country_code: str           # 국가코드 ("GB", "FR", "AU", "AE", "KR")
    city_hub: str               # 거점 도시 ("런던", "파리", "퍼스/시드니", "아부다비", "글로벌 거점")
    program_name: str           # 프로그램 국문 공식명칭
    program_name_en: str        # 프로그램 영문 공식명칭
    supervising_entity: str     # 주관 정부/기관 (영국 기업통상부, 프랑스해외문화진흥원, 호주 Austrade, ADGM 등)
    operating_entity: str       # 전담 운영 기관 / 파트너 (딜메이커 네트워크, 삼성문화재단, Spacecubed, Hub71 등)
    specialized_fields: List[str] # 특화 지원 분야 리스트
    support_type: str           # 지원 유형 ("비자/멘토링", "레지던시/체재비", "랜딩패드/바이어매칭", "현금+현물패키지", "해외거점/바우처")
    financial_benefit: str      # 재정 지원 내용 (금액, 항공료, 체재비 등)
    visa_benefit: str           # 비자 특혜 및 체류 혜택 (혁신가 비자, 골든 비자, 레지던시 등)
    space_facility_benefit: str # 공간 및 연구 인프라 (테스트베드, 스튜디오, 코워킹 등)
    mentoring_network: str      # 멘토링, 투자, 네트워크 연계
    target_qualifications: str  # 신청 자격 요건
    selection_scale: str        # 선발 규모 및 주기
    source_portal: str          # 연동 포털 ID ("uk_dbt_gep", "fr_cite_stationf", "au_austrade_landing", "uae_hub71_adgm", "kr_ksc_global")
    detail_url: str             # 공식 안내/신청 URL
    inquiry_contact: str        # 문의처 / 대표 창구
    case_studies: List[str]     # 주요 한국 진출/연계 사례

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------
# 해외 주요 선진국 및 거점 도시 특화 지원사업 마스터 카탈로그 (SSOT)
# --------------------------------------------------------------------------
GLOBAL_GRANTS_CATALOG: List[GlobalGrantProgram] = [
    # =========================================================================
    # 1. 영국 (런던) – AI, 딥테크, SaaS 유망 스타트업 유치
    # =========================================================================
    GlobalGrantProgram(
        program_id="UK-DBT-GEP-2026",
        country="영국",
        country_code="GB",
        city_hub="런던",
        program_name="영국 글로벌 기업가 프로그램 (GEP)",
        program_name_en="Global Entrepreneur Programme (GEP)",
        supervising_entity="영국 기업통상부 (Department for Business and Trade, DBT)",
        operating_entity="영국 DBT 글로벌 딜메이커 (Dealmaker) 네트워크 (24인 전담팀)",
        specialized_fields=["AI", "딥테크", "SaaS", "빅데이터", "클라우드"],
        support_type="비자/멘토링",
        financial_benefit="현지 VC/엔젤 투자 연계, R&D 세제 혜택(R&D Tax Relief) 컨설팅 지원",
        visa_benefit="영국 내무부(Home Office) 혁신가 창업자 비자(Innovator Founder Visa) 공식 보증 부여. 최소 투자금 요건 없음(0원), 3년 만에 무기한 체류 영주권(ILR) 신청 가능 (28일 저축 1,270파운드 입증)",
        space_facility_benefit="영국 내 글로벌 본사(HQ) 및 R&D 전략 거점 설립, 국가 R&D 테스트베드 인프라 제공",
        mentoring_network="글로벌 연쇄 창업가 24인 1:1 밀착 전담 코칭, Alumni Academy 네트워크, 현지 고급 기술 인재 채용 지원",
        target_qualifications="영국 시장 진출 및 글로벌 HQ/전략 R&D 센터를 설립하고자 하는 혁신 기술 보유 딥테크/AI 스타트업",
        selection_scale="수시 심사 및 딜메이커 추천 기반 선발",
        source_portal="uk_dbt_gep",
        detail_url="https://www.great.gov.uk/international/content/invest/how-we-help-you-invest-in-the-uk/global-entrepreneur-programme/",
        inquiry_contact="주한영국대사관 기업통상부 (DBT Korea) / GEP Direct Inquiry",
        case_studies=["삼쩜삼 (자비스앤빌런즈)", "한국축산데이터", "에이모 (AIMMO)", "핀텔 (Fintel)"],
    ),
    GlobalGrantProgram(
        program_id="UK-SEOUL-IMPERIAL-2026",
        country="영국",
        country_code="GB",
        city_hub="런던",
        program_name="서울AI허브 × 런던 임페리얼 칼리지 글로벌 산학협력 R&D",
        program_name_en="Seoul AI Hub × Imperial College London Collaborative Research",
        supervising_entity="서울시 / 영국 임페리얼 칼리지 런던 (Imperial College London)",
        operating_entity="서울AI허브 / 임페리얼 연구진 / 크레인 벤처파트너스(Crane VP) × KVIC",
        specialized_fields=["AI", "컴퓨터비전", "3D 얼굴 생성", "산업 자동화", "PCB 품질검사"],
        support_type="산학협동 R&D/투자연계",
        financial_benefit="공동 연구 프로젝트 수행 자금 및 Crane Venture Partners 연계 글로벌 투자 펀딩",
        visa_benefit="영국 학술/비즈니스 단기 방문 비자 지원 및 GEP 비자 패스트트랙 연계",
        space_facility_benefit="임페리얼 칼리지 화이트시티 캠퍼스 딥테크 연구실 및 글로벌 테크 허브 공간",
        mentoring_network="임페리얼 칼리지 석학 연구진과의 1:1 기술 고도화, 유럽 테크 VC 네트워크 피칭",
        target_qualifications="AI 알고리즘 및 딥테크 원천기술을 보유한 서울 소재 유망 AI 스타트업",
        selection_scale="연 5개사 내외 선발 (정밀 평가)",
        source_portal="uk_dbt_gep",
        detail_url="https://seoulaihub.kr/",
        inquiry_contact="서울AI허브 글로벌협력팀 (02-2133-2800)",
        case_studies=["3D 얼굴 생성 AI 스타트업", "PCB 불량 검사 자동화 솔루션 기업"],
    ),

    # =========================================================================
    # 2. 프랑스 (파리) – 창의적 작가, 미술 연구자, 문화·디지털 융합 테크 유치
    # =========================================================================
    GlobalGrantProgram(
        program_id="FR-CITE-SAMSUNG-2026",
        country="프랑스",
        country_code="FR",
        city_hub="파리",
        program_name="삼성문화재단 파리국제예술공동체 (Cité) 레지던시 지원사업",
        program_name_en="Samsung Foundation Cité internationale des arts Residency",
        supervising_entity="삼성문화재단 / 프랑스 문화부 파리국제예술공동체",
        operating_entity="파리국제예술공동체 (Cité internationale des arts)",
        specialized_fields=["시각예술", "현대미술", "전시기획", "미술사학", "미술비평/이론"],
        support_type="레지던시/체재비",
        financial_benefit="6개월간 스튜디오 사용료, 왕복 항공료, 월 체재비, 창작 활동 지원비, 관리비 전액 100% 무상 지원",
        visa_benefit="프랑스 장기 체류 문화예술인 비자 발급 공식 후원",
        space_facility_benefit="파리 시내 40m² 규모 전용 작업실 겸 주거 스튜디오(침실, 욕실, 주방 완비), 판화/도예 공방, 전시실, 공연장 자유 이용",
        mentoring_network="전 세계 60여 개국 입주 예술가·연구자 간 크로스 네트워크, 파리 주요 미술관/갤러리 큐레이터 매칭",
        target_qualifications="대한민국 국적의 유망 현대미술 작가, 독립 큐레이터, 미술사학자 및 평론가 (학술 연구자 포함)",
        selection_scale="연간 상·하반기 각 1~2명 엄선",
        source_portal="fr_cite_stationf",
        detail_url="https://www.samsungfoundation.org/",
        inquiry_contact="삼성문화재단 예술지원사업팀 / cite@samsung.com",
        case_studies=["국내 대표 중견 현대미술가", "유럽 비엔날레 참여 기획자 및 학술 연구자"],
    ),
    GlobalGrantProgram(
        program_id="FR-CITE-INSTITUT-2026",
        country="프랑스",
        country_code="FR",
        city_hub="파리",
        program_name="프랑스해외문화진흥원 × 주한프랑스대사관 Cité 레지던시",
        program_name_en="Institut Français × French Embassy Cité des Arts Residency",
        supervising_entity="프랑스 외교부 / 프랑스 문화부 / 주한프랑스대사관",
        operating_entity="프랑스해외문화진흥원 (Institut Français) / Cité des arts",
        specialized_fields=["시각예술", "문학/만화", "공연예술/무용", "디지털 창작(VR/AR)", "비디오 게임"],
        support_type="레지던시/문화교류",
        financial_benefit="3·6·9개월 스튜디오 무상 거주 지원 및 왕복 항공료 보조금",
        visa_benefit="주한프랑스대사관 문화예술 협약 패스트트랙 비자 지원",
        space_facility_benefit="파리 마레 지구 중심 Cité internationale des arts 스튜디오 및 미디어랩",
        mentoring_network="프랑스 현지 문화예술 기관, 페스티벌(앙굴렘 등), 디지털 크리에이티브 파트너 매칭",
        target_qualifications="시각, 문학, 공연 및 디지털 콘텐츠 분야에서 활동하는 대한민국 전문 창작자",
        selection_scale="분야별 3~5인 내외 선발",
        source_portal="fr_cite_stationf",
        detail_url="https://www.institutfrancais.com/",
        inquiry_contact="주한프랑스대사관 문화과 (02-3149-4300)",
        case_studies=["국제 VR 디지털 전시 출품 아티스트", "유럽 출판 연계 만화·웹툰 작가"],
    ),
    GlobalGrantProgram(
        program_id="FR-STATIONF-KSC-2026",
        country="프랑스",
        country_code="FR",
        city_hub="파리",
        program_name="라 프렌치 텍 (La French Tech) & KSC 파리 스테이션 F 입주 육성",
        program_name_en="La French Tech × KSC Paris (Station F) Acceleration",
        supervising_entity="프랑스 경제재정부 (La French Tech) / 중소벤처기업부 (창업진흥원)",
        operating_entity="K-스타트업 센터 파리 (KSC Paris) / Station F",
        specialized_fields=["AI", "뷰티테크", "디지털 플랫폼", "소비재 테크", "문화 융합 콘텐츠"],
        support_type="글로벌 액셀러레이팅/오피스",
        financial_benefit="기업당 해외 진출 자금 최대 6,000만 원 지원 + Station F 연계 글로벌 데모데이 참가비",
        visa_benefit="French Tech Visa (스타트업 창업자 및 임직원 대상 4년 거주 패스트트랙 비자) 연계",
        space_facility_benefit="세계 최대 스타트업 캠퍼스 Station F 내 KSC 전용 데스크 무상 배정, 회의실, 이벤트홀",
        mentoring_network="유럽 탑티어 엑셀러레이터 현지화 워크숍, 프랑스/유럽 대기업(L'Oréal, LVMH 등) 오픈이노베이션 연계",
        target_qualifications="유럽 시장 진출을 준비 중인 7년 이내 AI, 뷰티, 디지털 플랫폼 스타트업",
        selection_scale="연 15개사 내외 선발",
        source_portal="fr_cite_stationf",
        detail_url="https://lafrenchtech.gouv.fr/en/",
        inquiry_contact="창업진흥원 글로벌성장본부 / KSC 파리 데스크 (044-410-1700)",
        case_studies=["유럽 뷰티테크 시장 진출 K-스타트업", "Station F 글로벌 인큐베이션 유망주"],
    ),

    # =========================================================================
    # 3. 호주 (퍼스/시드니) – 호텔 경영·호스피탈리티, F&B, 테크 랜딩패드
    # =========================================================================
    GlobalGrantProgram(
        program_id="AU-DFAT-LANDING-PAD-2026",
        country="호주",
        country_code="AU",
        city_hub="퍼스 / 시드니",
        program_name="한-호 랜딩패드 프로그램 (Korea-Australia Landing Pad)",
        program_name_en="Korea-Australia Landing Pad Program (DFAT × Spacecubed)",
        supervising_entity="호주 외교통상부 (DFAT) 호주-한국 재단 (AKF, Australia-Korea Foundation)",
        operating_entity="스페이스큐브드 (Spacecubed, 서호주 최대 혁신 허브)",
        specialized_fields=["호스피탈리티", "F&B 마케팅", "디지털 혁신", "CleanTech", "AgriTech", "HealthTech", "AI"],
        support_type="랜딩패드/바이어매칭",
        financial_benefit="West Tech Fest 기간 'Landing Pad Week' 상주 참가를 위한 왕복 항공권 및 현지 숙박 보조금 100% 지원",
        visa_benefit="호주 비즈니스 단기 교류 비자(Subclass 400/600) 발급 행정 지원",
        space_facility_benefit="퍼스(Perth) 중심가 Spacecubed Riff/Fern 코워킹 스페이스 및 미팅룸 상시 제공",
        mentoring_network="한국 5개사 + 호주 5개사(총 10개사) 크로스보더 멘토링, 호주 벤처캐피털 피칭, 버추얼 글로벌 데모데이",
        target_qualifications="호주 및 아시아태평양(APAC) 시장 진출 의지를 갖춘 국내 유망 스타트업 (호스피탈리티, 클린테크, AI 등)",
        selection_scale="한국 5개사, 호주 5개사 (총 10개사 엄선)",
        source_portal="au_austrade_landing",
        detail_url="https://www.spacecubed.com/",
        inquiry_contact="Spacecubed Programs Team / info@spacecubed.com",
        case_studies=["호주 F&B 유통망 진출 테크기업", "서호주 광산·신재생 클린테크 협력사"],
    ),
    GlobalGrantProgram(
        program_id="AU-AUSTRADE-HORECA-2026",
        country="호주",
        country_code="AU",
        city_hub="시드니 / 멜버른",
        program_name="호주 무역투자대표부 (Austrade) 호스피탈리티 & F&B 진흥 매칭",
        program_name_en="Austrade Hospitality, F&B & Consumer Retail Landing Track",
        supervising_entity="호주 연방정부 무역투자대표부 (Austrade)",
        operating_entity="주한호주대사관 무역투자대표부 (Austrade Seoul)",
        specialized_fields=["호텔경영/호스피탈리티", "F&B 식음료", "글로벌 마케팅", "HORECA", "리테일 유통"],
        support_type="글로벌 B2B 판로개척",
        financial_benefit="대형 무역전시관 부스 임차비 지원 및 1:1 바이어 비즈니스 매칭 지원",
        visa_benefit="호주 상용 비즈니스 초청장 발급 지원",
        space_facility_benefit="Seoul Food & Hotel, Australian F&B Showcase 등 대형 B2B 상담장 부스 제공",
        mentoring_network="호텔·레스토랑·카페(HORECA) 프랜차이즈 및 대형 리테일 체인(이마트, 롯데마트, Coles, Woolworths) 바이어 직연계",
        target_qualifications="호주 농식품·식자재를 활용하거나 호주/APAC 시장으로 진출하고자 하는 F&B 및 호텔 솔루션 기업",
        selection_scale="연중 상시 B2B 상담회 매칭",
        source_portal="au_austrade_landing",
        detail_url="https://www.austrade.gov.au/",
        inquiry_contact="주한호주대사관 무역투자대표부 (02-398-2800)",
        case_studies=["국내 대형 유통사 F&B 론칭 브랜드", "호스피탈리티 주문 자동화 솔루션 기업"],
    ),

    # =========================================================================
    # 4. 중동 UAE (아부다비) – AI, 핀테크, 헬스테크, 기후테크 파격 인센티브 유치
    # =========================================================================
    GlobalGrantProgram(
        program_id="UAE-ADGM-HUB71-2026",
        country="UAE",
        country_code="AE",
        city_hub="아부다비",
        program_name="아부다비 글로벌 마켓 (ADGM) Hub71 Access Program",
        program_name_en="Hub71 Incentive & Access Program (ADGM Abu Dhabi)",
        supervising_entity="아부다비 경제개발부 (ADDED) / 아부다비 정부 (Ghadan 21 펀드)",
        operating_entity="Hub71 (아부다비 글로벌 마켓 ADGM 내 혁신 기술 허브)",
        specialized_fields=["AI", "핀테크", "헬스테크", "기후테크", "스마트시티", "Web3"],
        support_type="현금+현물 패키지",
        financial_benefit="기업당 최대 750,000 AED (한화 약 2억 8천만 원 상당) 인센티브:\n1. 현물 250,000 AED: 사무실, 주거, 건강보험 전액 지원\n2. 현금 250,000 AED: SAFE(조건부지분인수계약) 기반 현금 지원\n3. 성과 250,000 AED: 1년 수료 후 우수기업 추가 현금 지급",
        visa_benefit="ADGM Tech Startup Licence 발급 및 UAE 10년 거주 골든 비자(Golden Visa) 패스트트랙 추천",
        space_facility_benefit="Al Maryah Island 내 WeWork 전용 오피스 무상 배정 + 임직원 전용 연계 고급 주거 아파트 지원",
        mentoring_network="아부다비 국부펀드(Mubadala), 중동 주요 금융사·에너지 공기업과의 1:1 PoC 실증 기회, 임직원 건강보험 전액 커버",
        target_qualifications="아부다비 법인 설립 및 핵심 인력 현지 상주가 가능한 시드~시리즈A 단계 딥테크/핀테크/AI 스타트업",
        selection_scale="분기별 코호트(Cohort) 선발 (연간 40~50개사 글로벌 선발)",
        source_portal="uae_hub71_adgm",
        detail_url="https://www.hub71.com/",
        inquiry_contact="Hub71 Admissions Team / admissions@hub71.com",
        case_studies=["중동 디지털 결제 핀테크 진출 기업", "사막 기후테크 스마트팜 및 탄소감축 AI 기업"],
    ),

    # =========================================================================
    # 5. 대한민국 (글로벌) – 쌍방향 대치 대응 체계 (K-스타트업 센터, KSC)
    # =========================================================================
    GlobalGrantProgram(
        program_id="KR-MSS-KSC-HUB-2026",
        country="대한민국",
        country_code="KR",
        city_hub="글로벌 7대 거점 (파리, 실리콘밸리, 싱가포르, 도쿄 등)",
        program_name="중소벤처기업부 K-스타트업 센터 (KSC) 거점형 해외 진출 지원사업",
        program_name_en="K-Startup Center (KSC) Overseas Hub Landing & Scale-up",
        supervising_entity="중소벤처기업부 / 창업진흥원 / 중소벤처기업진흥공단",
        operating_entity="K-Startup Center 현지 운영 사무소 (실리콘밸리, 파리 Station F, 도쿄, 싱가포르)",
        specialized_fields=["AI", "바이오·헬스", "친환경·에너지", "DX 솔루션", "지능형 로봇"],
        support_type="해외거점/진출자금",
        financial_benefit="기업당 최대 6,000만 원 규모 해외 진출 및 사업화 바우처 지원",
        visa_benefit="거점 국가 비즈니스 비자 신청 행정 절차 및 보증 지원",
        space_facility_benefit="글로벌 전략 거점 4개국 현지 프리미엄 공유오피스 데스크 무상 입주 지원 (최대 1년)",
        mentoring_network="14주간 현지 최고 티어 액셀러레이터(AC) 전담 배정, 주차별 KPI 설정, 현지 바이어·VC 1:1 매칭",
        target_qualifications="업력 7년 이내 국내 창업기업 중 해외 시장 진출 역량 및 현지화 비즈니스 모델을 구비한 기업",
        selection_scale="거점별 15개사 내외 (총 80개사 이상)",
        source_portal="kr_ksc_global",
        detail_url="https://www.k-startup.go.kr/",
        inquiry_contact="창업진흥원 글로벌성장본부 (044-410-1700)",
        case_studies=["실리콘밸리 VC 투자 유치 성공 AI 기업", "싱가포르 동남아 본사 설립 핀테크 기업"],
    ),
    GlobalGrantProgram(
        program_id="KR-MSS-KSC-PROG-2026",
        country="대한민국",
        country_code="KR",
        city_hub="글로벌 프로그램 거점 (뉴욕, UAE 두바이/아부다비, 런던 등)",
        program_name="중소벤처기업부 K-스타트업 센터 (KSC) 프로그램형 글로벌 특화 트랙",
        program_name_en="K-Startup Center (KSC) Specialized Acceleration Program",
        supervising_entity="중소벤처기업부 / 중소벤처기업진흥공단",
        operating_entity="글로벌 탑티어 파트너 AC (Plug and Play, Techstars, Hub71 등)",
        specialized_fields=["스마트시티", "기후테크", "헬스케어", "핀테크", "콘텐츠"],
        support_type="집중 액셀러레이팅",
        financial_benefit="기업당 6,000만 원 현지 진출 자금 + 글로벌 IR 데모데이 참가 경비",
        visa_benefit="현지 파트너 초청 기반 상용 비자 및 임시 체류 지원",
        space_facility_benefit="현지 파트너 AC 전용 인큐베이팅 스페이스 단기 활용",
        mentoring_network="글로벌 멘토단 집중 코칭, 현지 유니콘 기업 필드 트립, 현지 전략적 투자자(SI) 및 재무적 투자자(FI) 밋업",
        target_qualifications="해외 진출 준비도(Export-ready)가 높고 타깃 시장 맞춤형 기술을 보유한 7년 이내 스타트업",
        selection_scale="프로그램별 10~15개사 선발",
        source_portal="kr_ksc_global",
        detail_url="https://www.kosmes.or.kr/",
        inquiry_contact="중소벤처기업진흥공단 글로벌협력처 (055-751-9000)",
        case_studies=["뉴욕 플러그앤플레이 연계 스케일업 기업", "중동 정부 PoC 수주 기술 스타트업"],
    ),
]


class GlobalGrantsService:
    """해외 특화 지원사업 검색 및 매칭 서비스."""

    def __init__(self, catalog: Optional[List[GlobalGrantProgram]] = None) -> None:
        self.catalog = catalog or GLOBAL_GRANTS_CATALOG

    def get_all_programs(
        self,
        country: Optional[str] = None,
        field: Optional[str] = None,
        visa_required: Optional[bool] = None,
        q: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """조건에 부합하는 해외 특화 지원사업 목록 필터링."""
        results: List[Dict[str, Any]] = []
        for p in self.catalog:
            # 국가 필터
            if country and country != "전체" and p.country != country:
                continue

            # 특화 분야 필터
            if field and field != "전체":
                matched_field = any(field.lower() in f.lower() for f in p.specialized_fields)
                if not matched_field:
                    continue

            # 비자 혜택 유무 필터
            if visa_required is True:
                if "비자" not in p.visa_benefit and "영주권" not in p.visa_benefit:
                    continue

            # 검색어 텍스트 필터
            if q:
                kw = q.strip().lower()
                text = " ".join([
                    p.program_name,
                    p.program_name_en,
                    p.country,
                    p.city_hub,
                    p.supervising_entity,
                    p.operating_entity,
                    " ".join(p.specialized_fields),
                    p.financial_benefit,
                    p.visa_benefit,
                    p.space_facility_benefit,
                    p.target_qualifications,
                    " ".join(p.case_studies),
                ]).lower()
                if kw not in text:
                    continue

            results.append(p.to_dict())

        return results

    def get_summary_by_country(self) -> Dict[str, Any]:
        """국가별 거점 지원사업 통계 및 핵심 혜택 집계."""
        summary: Dict[str, Any] = {}
        for p in self.catalog:
            c = p.country
            if c not in summary:
                summary[c] = {
                    "country": c,
                    "country_code": p.country_code,
                    "city_hub": p.city_hub,
                    "count": 0,
                    "fields": set(),
                    "programs": [],
                }
            summary[c]["count"] += 1
            summary[c]["fields"].update(p.specialized_fields)
            summary[c]["programs"].append({
                "id": p.program_id,
                "name": p.program_name,
                "support_type": p.support_type,
                "visa_benefit": p.visa_benefit[:60] + "...",
            })

        # Set to list for JSON serialization
        for c in summary:
            summary[c]["fields"] = list(summary[c]["fields"])

        return summary

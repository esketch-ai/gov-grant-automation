"""
전국 지자체별 과제지원 및 사무실(입주) 지원 전문 센터 디렉토리
(송파구 사회적경제지원센터, 강남스타트업센터, 판교 스타트업캠퍼스 등 전국 거점)
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class LocalSupportCenter:
    """지자체별 지원센터 데이터 스키마."""
    center_id: str              # 고유 식별자 (예: "SEOUL-SONGPA-SE")
    name: str                   # 센터/기관명 (예: "송파구 사회적경제지원센터")
    region: str                 # 광역 지자체 ("서울", "경기", "인천", "대전", "부산" 등)
    sub_region: str             # 기초 자치구/시 ("송파구", "강남구", "성남시", "유성구" 등)
    category: str               # 센터 유형 ("사회적경제", "청년창업지원", "테크노파크", "창업허브", "산업진흥원")
    website_url: str            # 공식 홈페이지 URL
    supports_office: bool       # 사무실/입주공간 지원 여부
    office_details: str         # 사무실 지원 세부 내용 (독립실, 코워킹, 임대료 감면, 비상주 등)
    supports_grants: bool       # 사업화/과제 지원 여부
    grant_details: str          # 과제/자금 지원 세부 내용 (시제품 제작비, 사업개발비, R&D 바우처 등)
    target_qualifications: str  # 지원 대상 자격 요건 (사회적기업, 청년, 3년 이내, 관내 이전 기업 등)
    contact_info: str           # 대표 전화 / 소재지

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------
# 전국 지자체별 핵심 지원센터 마스터 카탈로그 (SSOT)
# --------------------------------------------------------------------------
LOCAL_CENTERS_CATALOG: List[LocalSupportCenter] = [
    # =========================================================================
    # 1. 서울특별시 (Seoul Districts)
    # =========================================================================
    LocalSupportCenter(
        center_id="SEOUL-SONGPA-SE",
        name="송파구 사회적경제지원센터",
        region="서울",
        sub_region="송파구",
        category="사회적경제",
        website_url="https://www.songpase.org",
        supports_office=True,
        office_details="문정동 지식산업센터 내 독립 입주실(2~4인실), 코워킹스페이스, 최대 2년 입주 (임대료 대폭 감면)",
        supports_grants=True,
        grant_details="송파구 사회적경제기업 사업개발비, 시제품 제작 및 마케팅 바우처, 공공구매 판로 연계",
        target_qualifications="송파구 관내 (예비)사회적기업, 사회적협동조합, 마을기업 또는 입주 후 1개월 내 이전 기업",
        contact_info="02-406-1427 / 서울시 송파구 문정동",
    ),
    LocalSupportCenter(
        center_id="SEOUL-GANGNAM-STARTUP",
        name="강남스타트업센터 / 청년창업지원센터",
        region="서울",
        sub_region="강남구",
        category="청년창업지원",
        website_url="https://www.gangnam.go.kr",
        supports_office=True,
        office_details="역삼로 팁스타운 인근 스타트업 전용 독립보육실(4~8인실), 1인 오픈오피스 전액 무상 입주",
        supports_grants=True,
        grant_details="강남구 청년창업 테스트베드 실증비, 대기업 오픈이노베이션 PoC, 해외 IR 참가지원",
        target_qualifications="만 39세 이하 청년 창업자 또는 창업 7년 이내 유망 테크 스타트업",
        contact_info="02-3423-5500 / 서울시 강남구 역삼로",
    ),
    LocalSupportCenter(
        center_id="SEOUL-SEONGDONG-SV",
        name="성동구 소셜벤처허브 / 성동사회적경제",
        region="서울",
        sub_region="성동구",
        category="사회적경제",
        website_url="https://www.svhc.or.kr",
        supports_office=True,
        office_details="성수동 소셜벤처 밸리 중심 독립 업무공간, 팟캐스트 스튜디오, 공유 미팅룸 무상 제공",
        supports_grants=True,
        grant_details="성동구 소셜벤처 혁신경연대회 상금 및 사업화 자금(최대 2,000만원), 임팩트 투자 연계",
        target_qualifications="사회적 가치를 창출하는 소셜벤처, 청년 임팩트 스타트업, 예비창업자",
        contact_info="02-2290-7000 / 서울시 성동구 성수동",
    ),
    LocalSupportCenter(
        center_id="SEOUL-MAPO-HUB",
        name="서울창업허브 공덕 (SBA) / 마포청년나루",
        region="서울",
        sub_region="마포구",
        category="창업허브",
        website_url="https://hubgongdeok.startup-plus.kr",
        supports_office=True,
        office_details="국내 최대 규모 단일 스타트업 보육센터(공덕역), 독립 인큐베이팅실 150여실, 편의시설 완비",
        supports_grants=True,
        grant_details="서울형 R&D 오픈이노베이션 대기업 매칭 실증비(최대 5,000만원), 글로벌 진출 지원",
        target_qualifications="창업 7년 이내 전 분야 스타트업, 스케일업 희망 기업",
        contact_info="02-2115-2000 / 서울시 마포구 백범로 (공덕동)",
    ),
    LocalSupportCenter(
        center_id="SEOUL-SEOCHO-AI",
        name="AI 양재 허브 (서울시·서초구)",
        region="서울",
        sub_region="서초구",
        category="산업진흥원",
        website_url="https://ai-yangjae.kr",
        supports_office=True,
        office_details="양재 R&CD 혁신지구 내 AI 전용 독립 입주실, 고성능 GPU 클라우드 인프라 제공",
        supports_grants=True,
        grant_details="인공지능(AI) 알고리즘 고도화 R&D 바우처, AI 특화 벤처투자 데모데이 연계",
        target_qualifications="인공지능, 딥러닝, 빅데이터 원천기술 및 응용 서비스를 개발하는 창업기업",
        contact_info="02-6953-6400 / 서울시 서초구 매헌로",
    ),
    LocalSupportCenter(
        center_id="SEOUL-GWANAK-SVALLEY",
        name="관악S밸리 (낙성벤처창업센터/신림창업센터)",
        region="서울",
        sub_region="관악구",
        category="청년창업지원",
        website_url="https://www.gwanak.go.kr",
        supports_office=True,
        office_details="서울대 후문 낙성대 및 신림 벤처타운 입주실, 1인~6인실 및 비상주 주소지 등록 무상",
        supports_grants=True,
        grant_details="관악 벤처기업 스케일업 펀드 연계, 서울대 교수·연구진 기술 매칭 바우처",
        target_qualifications="서울시 및 관악구 소재 또는 이전 예정 유망 벤처기업, 대학생/청년 창업팀",
        contact_info="02-879-6680 / 서울시 관악구 낙성대로",
    ),

    # =========================================================================
    # 2. 경기도 및 인천광역시 (Gyeonggi & Incheon)
    # =========================================================================
    LocalSupportCenter(
        center_id="GG-SEONGNAM-PANGYO",
        name="성남산업진흥원 / 판교 스타트업캠퍼스",
        region="경기",
        sub_region="성남시",
        category="산업진흥원",
        website_url="https://www.snip.or.kr",
        supports_office=True,
        office_details="판교 제1·2테크노밸리 스타트업 랩 및 정자동 킨스타워 입주 오피스(시세 20% 수준 실비)",
        supports_grants=True,
        grant_details="성남형 AX/DX 테크 실증과제(최대 5,000만원), 시제품 제작, 특허 출원 바우처 지원",
        target_qualifications="성남시 판교/분당 소재 또는 이전 예정 ICT·소프트웨어·바이오 창업기업",
        contact_info="031-782-3000 / 경기도 성남시 분당구",
    ),
    LocalSupportCenter(
        center_id="INCHEON-STARTUP-PARK",
        name="인천 스타트업파크 (인천테크노파크)",
        region="인천",
        sub_region="연수구",
        category="테크노파크",
        website_url="https://startuppark.kr",
        supports_office=True,
        office_details="송도 컨벤시아 인근 투모로우시티 인스타 I·II 오피스, 최대 2년 전액 무상 입주 지원",
        supports_grants=True,
        grant_details="인천 스타트업 실증(PoC) 바우처(최대 1억원), 스마트시티·바이오 실증 테스트베드 연계",
        target_qualifications="스마트시티, 바이오융합, 4차산업 기술을 보유한 창업 7년 이내 스타트업",
        contact_info="032-260-0600 / 인천시 연수구 송도동",
    ),
    LocalSupportCenter(
        center_id="GG-SUWON-CENTER",
        name="수원도시재단 창업지원센터",
        region="경기",
        sub_region="수원시",
        category="청년창업지원",
        website_url="https://suwoncenter.org",
        supports_office=True,
        office_details="수원시 권선구 고색동 산업단지 내 독립 보육실(3~6인실) 및 코워킹스페이스 제공",
        supports_grants=True,
        grant_details="수원 창업오디션 사업화 자금(최대 3,000만원), 크라우드펀딩 수수료 지원",
        target_qualifications="수원시 관내 청년 창업자 및 창업 5년 이내 기업",
        contact_info="031-280-6300 / 경기도 수원시 권선구",
    ),
    LocalSupportCenter(
        center_id="GG-ANYANG-INDUSTRY",
        name="안양산업진흥원 / 청년창업지원센터",
        region="경기",
        sub_region="안양시",
        category="산업진흥원",
        website_url="https://ayip.or.kr",
        supports_office=True,
        office_details="평촌스마트스퀘어 본원 및 동안청년오피스 무상 입주실, 세미나룸·시제품 장비실",
        supports_grants=True,
        grant_details="안양시 청년창업펀드 1,000억 연계, 시제품 제작 및 SW 품질인증(GS) 지원금",
        target_qualifications="안양시 거주자 또는 안양시 관내 사업장 등록 기업",
        contact_info="031-8045-6700 / 경기도 안양시 동안구",
    ),
    LocalSupportCenter(
        center_id="GG-BUCHEON-BIZ",
        name="부천산업진흥원 / 부천사회적경제센터",
        region="경기",
        sub_region="부천시",
        category="사회적경제",
        website_url="https://bizbc.or.kr",
        supports_office=True,
        office_details="춘의테크노파크 R&D센터 내 입주공간 및 부천IoT혁신센터 코워킹실",
        supports_grants=True,
        grant_details="부천 로봇·금형 특화 R&BD 지원금, 사회적경제기업 사업개발비 지원",
        target_qualifications="부천시 소재 로봇, 메카트로닉스, 패키징, 사회적경제 기업",
        contact_info="032-716-6400 / 경기도 부천시 원미구",
    ),

    # =========================================================================
    # 3. 충청권 (Daejeon, Sejong, Chungcheong)
    # =========================================================================
    LocalSupportCenter(
        center_id="DAEJEON-D-UNICORN",
        name="대전창조경제혁신센터 (D-유니콘라운지)",
        region="대전",
        sub_region="유성구",
        category="창업허브",
        website_url="https://dci.or.kr",
        supports_office=True,
        office_details="KAIST·충남대 궁동 스타트업 파크 독립 오피스, D-유니콘 라운지 무상 이용",
        supports_grants=True,
        grant_details="대전 딥테크 바이오·ICT 사업화 자금(최대 1억원), 대전 엔젤투자 매칭펀드",
        target_qualifications="대덕연구개발특구 연계 기술창업팀, 대전시 소재 7년 이내 스타트업",
        contact_info="042-385-0600 / 대전시 유성구 대학로",
    ),
    LocalSupportCenter(
        center_id="SEJONG-TP-CAMPUS",
        name="세종테크노파크 / 청년창업사관학교",
        region="세종",
        sub_region="조치원읍",
        category="테크노파크",
        website_url="https://sjtp.or.kr",
        supports_office=True,
        office_details="조치원 SB플라자 및 산학연클러스터지원센터 내 스타트업 입주 오피스",
        supports_grants=True,
        grant_details="세종 스마트시티 규제샌드박스 실증비, 자율주행 서비스 실증 R&D 지원금",
        target_qualifications="세종시 소재 자율주행, 스마트시티, 정보통신기술 창업기업",
        contact_info="044-850-2100 / 세종특별자치시 조치원읍",
    ),
    LocalSupportCenter(
        center_id="CHUNGNAM-STARTUP",
        name="충남창조경제혁신센터 (천안아산 R&D집적지구)",
        region="충남",
        sub_region="천안시",
        category="창업허브",
        website_url="https://ccei.creativekorea.or.kr/chungnam",
        supports_office=True,
        office_details="천안아산역 KTX 역세권 청년창업보육실, 충남 창업마루 나비 독립 업무공간",
        supports_grants=True,
        grant_details="디스플레이·친환경 모빌리티 스타트업 사업화 자금, 농식품 벤처 바우처",
        target_qualifications="충남 관내 또는 천안·아산 이전 희망 기술창업 기업",
        contact_info="041-536-7800 / 충남 천안시 서북구",
    ),
    LocalSupportCenter(
        center_id="CHUNGBUK-OSONG-TP",
        name="충북테크노파크 (오송 바이오밸리 보육실)",
        region="충북",
        sub_region="청주시",
        category="테크노파크",
        website_url="https://cbtp.or.kr",
        supports_office=True,
        office_details="오송 생명과학단지 바이오플라자 보육실, 오창 이차전지 특구 입주실",
        supports_grants=True,
        grant_details="K-바이오헬스 전임상/인허가 컨설팅 바우처, 이차전지 소부장 시제품 제작비",
        target_qualifications="바이오, 제약, 의료기기, 이차전지 소부장 기술 보유 기업",
        contact_info="043-270-2000 / 충북 청주시 흥덕구 오송읍",
    ),

    # =========================================================================
    # 4. 영남권 (Busan, Daegu, Ulsan, Gyeongbuk, Gyeongnam)
    # =========================================================================
    LocalSupportCenter(
        center_id="BUSAN-CENTAP",
        name="센텀기술창업타운 (CENTAP, 부산테크노파크)",
        region="부산",
        sub_region="해운대구",
        category="테크노파크",
        website_url="https://centap.kr",
        supports_office=True,
        office_details="해운대구 센텀시티 기술창업 타운 내 독립오피스, TIPS운영사/AC 상주 공간",
        supports_grants=True,
        grant_details="부산 대표 창업기업 브라이트클럽 바우처(최대 2,500만원), 센텀 핀테크 실증비",
        target_qualifications="부산시 관내 기술창업 7년 이내 스타트업, TIPS 선발 희망 기업",
        contact_info="051-921-6000 / 부산시 해운대구 센텀동로",
    ),
    LocalSupportCenter(
        center_id="DAEGU-DASH",
        name="대구스케일업허브 (DASH, 대구테크노파크)",
        region="대구",
        sub_region="동구",
        category="테크노파크",
        website_url="https://dash.or.kr",
        supports_office=True,
        office_details="동대구 벤처밸리 DASH 단독빌딩, 1인실~10인실 독립 보육공간(시세 대비 80% 감면)",
        supports_grants=True,
        grant_details="대구 ABB(AI, 빅데이터, 블록체인) 사업화 과제, 로봇 솔루션 실증 바우처",
        target_qualifications="대구시 소재 또는 본사 이전 예정 테크 스타트업",
        contact_info="053-757-4100 / 대구시 동구 동대구로",
    ),
    LocalSupportCenter(
        center_id="POHANG-CHANGEUP",
        name="포스코 체인지업그라운드 (포항TP/포스텍)",
        region="경북",
        sub_region="포항시",
        category="창업허브",
        website_url="https://changeupground.com",
        supports_office=True,
        office_details="포스텍(POSTECH) 캠퍼스 내 아시아 최대 오피스 공간, 연구실(Lab) 무상 지원",
        supports_grants=True,
        grant_details="포스코 벤처펀드 시드투자 매칭, 이차전지·포항 신약개발 R&BD 지원금",
        target_qualifications="신소재, 배터리, 바이오, AI 기술 분야 유망 스타트업",
        contact_info="054-279-0114 / 경북 포항시 남구 지곡동",
    ),
    LocalSupportCenter(
        center_id="CHANGWON-INDUSTRY",
        name="창원산업진흥원 / 경남창조경제혁신센터",
        region="경남",
        sub_region="창원시",
        category="산업진흥원",
        website_url="https://cwip.or.kr",
        supports_office=True,
        office_details="창원 스마트혁신지원센터 내 독립오피스, 사천 항공우주 스타트업 보육실",
        supports_grants=True,
        grant_details="우주항공청(KASA) 연계 정밀부품 R&D 바우처, 방산 협력업체 스케일업 자금",
        target_qualifications="창원시 및 경남도내 항공우주, 정밀기계, 원전·방산 중소벤처기업",
        contact_info="055-716-7700 / 경남 창원시 의창구",
    ),

    # =========================================================================
    # 5. 호남, 강원, 제주권 (Gwangju, Jeonbuk, Jeonnam, Gangwon, Jeju)
    # =========================================================================
    LocalSupportCenter(
        center_id="GWANGJU-IPLEX",
        name="I-PLEX 광주 / 광주 AI집적단지",
        region="광주",
        sub_region="동구",
        category="청년창업지원",
        website_url="https://iplexgwangju.kr",
        supports_office=True,
        office_details="동구 대남대로 청년창업지원센터 독립실, 첨단3지구 국가AI데이터센터 입주공간",
        supports_grants=True,
        grant_details="광주 AI 시제품 제작 및 고성능 컴퓨팅 바우처, 청년창업 특례보증 자금",
        target_qualifications="광주시 관내 청년 창업기업, AI 및 데이터 기술 벤처기업",
        contact_info="062-239-9600 / 광주시 동구 대남대로",
    ),
    LocalSupportCenter(
        center_id="JEONBUK-INNO-TOWN",
        name="전북 사회적경제혁신타운 / 전주정보문화",
        region="전북",
        sub_region="군산시",
        category="사회적경제",
        website_url="https://jica.kr",
        supports_office=True,
        office_details="군산 사회적경제혁신타운 입주실, 전주 J-디지털 지식산업센터 독립공간",
        supports_grants=True,
        grant_details="농생명·바이오 스타트업 실증 지원, 탄소소재 융합기술 상용화 바우처",
        target_qualifications="전라북도 소재 사회적경제기업, 농생명·탄소소재 청년 창업팀",
        contact_info="063-281-4100 / 전북 군산시 옥구읍",
    ),
    LocalSupportCenter(
        center_id="GANGWON-CCEI-MED",
        name="강원창조경제혁신센터 / 원주의료기기테크노밸리",
        region="강원",
        sub_region="원주시",
        category="테크노파크",
        website_url="https://ccei.creativekorea.or.kr/gangwon",
        supports_office=True,
        office_details="원주 의료기기종합지원센터 보육실, 춘천 강원대 창업보육센터 업무공간",
        supports_grants=True,
        grant_details="디지털 헬스케어 인허가 및 시험평가 바우처, 강원 로컬크리에이터 활성화 자금",
        target_qualifications="디지털 헬스케어, 바이오의료기기, 로컬크리에이터 창업기업",
        contact_info="033-248-7900 / 강원도 춘천시 / 원주시",
    ),
    LocalSupportCenter(
        center_id="JEJU-VENTURE-MARU",
        name="제주창조경제혁신센터 (제주벤처마루)",
        region="제주",
        sub_region="제주시",
        category="창업허브",
        website_url="https://ccei.creativekorea.or.kr/jeju",
        supports_office=True,
        office_details="제주시 중앙로 제주벤처마루 독립 보육실, 서귀포 워케이션 공유오피스 무상 제공",
        supports_grants=True,
        grant_details="제주 스타트업 시드머니 투자 연계 (최대 1억원), 카본프리·스마트관광 실증비",
        target_qualifications="제주도 소재 또는 이전 희망 청년 스타트업, 워케이션 유치 기업",
        contact_info="064-710-1900 / 제주도 제주시 중앙로 (벤처마루)",
    ),

    # =========================================================================
    # 추가 1: 광역 및 기초 지자체 청년창업·사무공간 거점
    # =========================================================================
    LocalSupportCenter(
        center_id="SEOUL-MAPO-NARU",
        name="마포청년창업취업지원센터 (마포청년나루)",
        region="서울",
        sub_region="마포구",
        category="청년창업지원",
        website_url="https://www.mapo.go.kr",
        supports_office=True,
        office_details="청년 창업 오픈오피스 및 공유오피스 무상 제공, 1:1 멘토링룸, 창업스터디룸",
        supports_grants=True,
        grant_details="청년 창업 아이디어 검증비, IR 피칭 코칭, 마포구 로컬 크리에이터 사업화 지원금",
        target_qualifications="마포구 거주 또는 마포구 내 창업을 희망하는 만 39세 이하 청년 창업가",
        contact_info="02-3144-0740 / 서울시 마포구 합정동",
    ),
    LocalSupportCenter(
        center_id="SEOUL-GANGBUK-MARU",
        name="강북청년창업마루",
        region="서울",
        sub_region="강북구",
        category="청년창업지원",
        website_url="https://gb.go.kr",
        supports_office=True,
        office_details="청년 창업가 독립 입주 오피스(2~4인실) 및 공유오피스, 비즈니스 라운지 무상 지원",
        supports_grants=True,
        grant_details="강북구 청년 창업도전 지원금, 1:1 전문가 그룹 멘토링, 시제품 제작비 연계",
        target_qualifications="강북구 관내 청년 예비 창업가 또는 창업 3년 이내 초기 기업",
        contact_info="02-901-6114 / 서울시 강북구 4·19로",
    ),
    LocalSupportCenter(
        center_id="INCHEON-NAMDONG-YOUTH",
        name="남동구 청년창업지원센터",
        region="인천",
        sub_region="남동구",
        category="청년창업지원",
        website_url="https://www.namdong.go.kr",
        supports_office=True,
        office_details="관내 청년 기업 전용 독립 보육실 및 개방형 코워킹 데스크 무상 제공, 촬영 스튜디오",
        supports_grants=True,
        grant_details="사업화 마케팅 지원금, 시제품 고도화 자금, 남동국가산단 제조 연계 멘토링",
        target_qualifications="만 19세~39세 청년 창업자 또는 관내 1개월 이내 본사 이전 가능 기업",
        contact_info="032-453-2000 / 인천시 남동구 만수동",
    ),
    LocalSupportCenter(
        center_id="BUSAN-HAEUNDAE-CHAEUM",
        name="해운대 청년채움공간",
        region="부산",
        sub_region="해운대구",
        category="청년창업지원",
        website_url="https://www.haeundae.go.kr",
        supports_office=True,
        office_details="해운대구 청년 창업 인큐베이팅 시설, 독립 오피스 및 오픈데스크 무상 입주",
        supports_grants=True,
        grant_details="청년 창업 컨설팅 및 위탁 보육, 해운대 관광·문화·ICT 콘텐츠 사업화 바우처",
        target_qualifications="해운대구 거주 청년 예비 창업가 및 창업 3년 이내 초기 기업",
        contact_info="051-749-4000 / 부산시 해운대구 중동",
    ),
    LocalSupportCenter(
        center_id="BUSAN-STARTUP-PORTAL",
        name="부산창업포털 (부산테크노파크/창조경제)",
        region="부산",
        sub_region="해운대구",
        category="창업허브",
        website_url="https://www.busanstartup.kr",
        supports_office=True,
        office_details="부산 관내 16개 시군구 창업 입주공간 및 메이커스페이스 통합 공고 및 예약 연계",
        supports_grants=True,
        grant_details="부산 단디벤처포럼, 글로벌 바운스(BOUNCE) 지원금, 부산 대표 창업기업 육성 바우처",
        target_qualifications="부산 관내 소재 및 이전 유치 유망 스타트업 (예비~7년 이내)",
        contact_info="051-744-8494 / 부산시 해운대구 센텀중앙로",
    ),
    LocalSupportCenter(
        center_id="DAEGU-STARTUP-DASH",
        name="대구창업허브 (DASH)",
        region="대구",
        sub_region="북구",
        category="창업허브",
        website_url="https://startup.daegu.go.kr",
        supports_office=True,
        office_details="대구 스케일업허브(DASH), 동대구벤처밸리 등 입주공간 및 회의실 대관 지원",
        supports_grants=True,
        grant_details="대구 C-Lab 액셀러레이팅, 시제품 제작(C-Fab) 자금, ABB(AI·빅데이터) 실증비",
        target_qualifications="대구시 소재 또는 대구 이전 계획이 있는 혁신 기술 스타트업",
        contact_info="053-757-4100 / 대구시 북구 연암로",
    ),

    # =========================================================================
    # 추가 2: 광역 및 기초 사회적경제 전담 거점
    # =========================================================================
    LocalSupportCenter(
        center_id="GYEONGGI-PEOPLES-SE",
        name="경기도 사회적경제 종합지원플랫폼 (사람과세상)",
        region="경기",
        sub_region="안양시",
        category="사회적경제",
        website_url="https://www.peoples.kr",
        supports_office=True,
        office_details="경기도 28개 시군 통합 거점 코워킹 및 혁신허브 입주 공간 연계",
        supports_grants=True,
        grant_details="경기도 사회적경제 청년혁신활동가 지원, 성장단계별 맞춤형 바우처 사업",
        target_qualifications="경기도 31개 시군 관내 사회적기업, 소셜벤처, 협동조합",
        contact_info="070-4760-6132 / 경기도 안양시 동안구 시민대로",
    ),
    LocalSupportCenter(
        center_id="GYEONGGI-PAJU-SE",
        name="파주시 사회적경제지원센터",
        region="경기",
        sub_region="파주시",
        category="사회적경제",
        website_url="https://www.paju.go.kr",
        supports_office=True,
        office_details="파주 청년사회적기업가 육성 입주 공간 무상 대여 및 커뮤니티홀",
        supports_grants=True,
        grant_details="파주형 사회적경제 모델 발굴 지원금, 로컬 거버넌스 공공구매 연계",
        target_qualifications="파주시 관내 사회적경제 기업 및 예비 창업 희망자",
        contact_info="031-940-5250 / 경기도 파주시 시청로 50",
    ),
    LocalSupportCenter(
        center_id="BUSAN-BSEC",
        name="부산광역시 사회적경제통합지원센터",
        region="부산",
        sub_region="사상구",
        category="사회적경제",
        website_url="https://www.bsec.or.kr",
        supports_office=True,
        office_details="사회적경제 혁신 거점 입주실 및 공유 미팅 라운지",
        supports_grants=True,
        grant_details="부산 사회적기업 사업개발비 지원, 판로 지원 및 공공구매 박람회 부스 지원",
        target_qualifications="부산 관내 사회적기업, 협동조합, 마을기업 및 소셜벤처",
        contact_info="051-505-1090 / 부산시 사상구 모라로",
    ),
    LocalSupportCenter(
        center_id="DAEGU-DGSE",
        name="대구광역시 사회적경제지원센터",
        region="대구",
        sub_region="중구",
        category="사회적경제",
        website_url="https://dgse.or.kr",
        supports_office=True,
        office_details="사회적경제 소셜라운지 및 창업 인큐베이팅실 지원",
        supports_grants=True,
        grant_details="대구형 사회적경제 혁신 프로젝트 지원금, 크라우드펀딩 연계 매칭 자금",
        target_qualifications="대구시 관내 사회적경제기업 및 예비창업자",
        contact_info="053-431-9824 / 대구시 중구 중앙대로",
    ),
    LocalSupportCenter(
        center_id="GWANGJU-GJSE",
        name="광주광역시 사회적경제지원센터",
        region="광주",
        sub_region="광산구",
        category="사회적경제",
        website_url="https://gjse.or.kr",
        supports_office=True,
        office_details="사회적경제 징검다리 창업 입주공간 및 스마트워크룸",
        supports_grants=True,
        grant_details="광주 사회적가치 측정(SVI) 연계 인센티브, 시제품 고도화 사업비",
        target_qualifications="광주시 소재 사회적기업, 협동조합, 사회적경제 육성 트랙 참여기업",
        contact_info="062-531-6651 / 광주시 광산구 하남산단6번로",
    ),
    LocalSupportCenter(
        center_id="JEONNAM-JNREC",
        name="전라남도 사회적경제통합지원센터",
        region="전남",
        sub_region="무안군",
        category="사회적경제",
        website_url="https://jnrec.kr",
        supports_office=True,
        office_details="전남 22개 시군 로컬 크리에이터 창업 오피스 및 교육실",
        supports_grants=True,
        grant_details="농수산 로컬 사회적기업 판로 개척, 남도장터 입점 연계, 지역특화 사업비",
        target_qualifications="전라남도 22개 시군 관내 사회적경제기업 및 청년 로컬창업가",
        contact_info="061-285-0552 / 전남 무안군 삼향읍 후광대로",
    ),

    # =========================================================================
    # 추가 3: 지역 테크노파크 (TP) 핵심 거점
    # =========================================================================
    LocalSupportCenter(
        center_id="SEOUL-TP",
        name="서울테크노파크",
        region="서울",
        sub_region="노원구",
        category="테크노파크",
        website_url="https://www.seoultp.or.kr",
        supports_office=True,
        office_details="스마트ICT융합동 및 나노소재 인큐베이팅실 (최대 5년 입주 지원)",
        supports_grants=True,
        grant_details="NT(나노기술)·IT 시제품 제작 지원, 서울스마트공장 보급, 특허 바우처",
        target_qualifications="나노, ICT, 스마트팩토리, 첨단 융합기술 분야 스타트업 및 중소기업",
        contact_info="02-944-6000 / 서울시 노원구 공릉로 232",
    ),
    LocalSupportCenter(
        center_id="GYEONGGI-TP",
        name="경기테크노파크 / 경기대진TP",
        region="경기",
        sub_region="안산시",
        category="테크노파크",
        website_url="https://www.gtp.or.kr",
        supports_office=True,
        office_details="안산 R&D집적단지 기술보육센터 및 포천 대진TP 공장형 입주실",
        supports_grants=True,
        grant_details="자동차부품·신재생에너지 상용화 R&D, 경기스마트제조혁신 바우처 지원",
        target_qualifications="경기도 관내 중소제조기업 및 부품소재 스타트업",
        contact_info="031-500-3000 / 경기도 안산시 상록구 해안로 705",
    ),
    LocalSupportCenter(
        center_id="GWANGJU-TP",
        name="광주테크노파크",
        region="광주",
        sub_region="북구",
        category="테크노파크",
        website_url="https://www.gjtp.or.kr",
        supports_office=True,
        office_details="첨단산단 본부 및 제2단지 바이오·스마트가전 시험인증 입주실",
        supports_grants=True,
        grant_details="모빌리티 전장, 생체의료, AI 반도체 패키징 실증 R&D 및 시제품 바우처",
        target_qualifications="광주시 주력산업(모빌리티, 생체의료, 에너지, 가전) 기업",
        contact_info="062-602-7000 / 광주시 북구 첨단과기로 333",
    ),
    LocalSupportCenter(
        center_id="CHUNGNAM-TP",
        name="충남테크노파크",
        region="충남",
        sub_region="천안시",
        category="테크노파크",
        website_url="https://www.ctp.or.kr",
        supports_office=True,
        office_details="천안 직산 본원 보육실 및 디스플레이센터, 아산 자동차부품 R&D동",
        supports_grants=True,
        grant_details="디스플레이 혁신공정, 탄소저감 친환경 자동차, 수소에너지 R&D 바우처",
        target_qualifications="충청남도 소재 디스플레이, 이차전지, 모빌리티 분야 기업",
        contact_info="041-589-0114 / 충남 천안시 서북구 직산로 136",
    ),

    # =========================================================================
    # 추가 4: 전국 MICE 및 전시·컨벤션 기반 B2B 판로 지원 거점 (9대 컨벤션)
    # =========================================================================
    LocalSupportCenter(
        center_id="SEOUL-COEX-MICE",
        name="코엑스 (COEX)",
        region="서울",
        sub_region="강남구",
        category="MICE·판로지원",
        website_url="https://www.coex.co.kr",
        supports_office=False,
        office_details="글로벌 비즈니스 미팅 라운지 및 바이어 1:1 상담장 상설 운영",
        supports_grants=True,
        grant_details="바이오코리아, 한국전자전, ICT 스타트업 특별관 참가 부스비 지원 (서울시/중기부 연계)",
        target_qualifications="ICT, 첨단 바이오, 유망 테크 스타트업 및 글로벌 수출 유망 중소기업",
        contact_info="02-6000-0114 / 서울시 강남구 영동대로 513",
    ),
    LocalSupportCenter(
        center_id="GYEONGGI-KINTEX-MICE",
        name="킨텍스 (KINTEX)",
        region="경기",
        sub_region="고양시",
        category="MICE·판로지원",
        website_url="https://www.kintex.com",
        supports_office=False,
        office_details="국내 최대 전시 컨벤션 바이어 상담실 및 비즈니스 인큐베이팅 지원 시설",
        supports_grants=True,
        grant_details="첨단 제조업·스마트시티 박람회 부스 임차료 지원, 글로벌 수출상담회 바이어 매칭",
        target_qualifications="제조업 고도화, AI/모빌리티, 스마트팩토리 분야 중소기업 및 스타트업",
        contact_info="031-810-8114 / 경기도 고양시 일산서구 킨텍스로 217-60",
    ),
    LocalSupportCenter(
        center_id="SEOUL-SETEC-MICE",
        name="SETEC (서울산업진흥원)",
        region="서울",
        sub_region="강남구",
        category="MICE·판로지원",
        website_url="https://www.setec.or.kr",
        supports_office=False,
        office_details="중소기업 상설 전시 및 비즈니스 상담 공간, 세미나룸",
        supports_grants=True,
        grant_details="서울시 소상공인·청년창업 박람회 참가지원, B2B 대형 유통망 입점 상담회 무상 매칭",
        target_qualifications="서울시 소재 초기 청년 창업가, 소상공인 및 소셜벤처",
        contact_info="02-2187-4600 / 서울시 강남구 남부순환로 3104",
    ),
    LocalSupportCenter(
        center_id="INCHEON-CONVENSIA-MICE",
        name="송도컨벤시아",
        region="인천",
        sub_region="연수구",
        category="MICE·판로지원",
        website_url="https://songdoconvensia.visitincheon.or.kr",
        supports_office=False,
        office_details="인천 IFEZ 글로벌 비즈니스 미팅룸 및 무역 상담 지원 라운지",
        supports_grants=True,
        grant_details="바이오·뷰티·모빌리티 산업전 부스 임차료 지원, 해외 바이어 1:1 수출 상담 연계",
        target_qualifications="인천 및 수도권 소재 바이오, 뷰티, 스마트물류 관련 유망 중소·벤처기업",
        contact_info="032-210-1114 / 인천시 연수구 센트럴로 123",
    ),
    LocalSupportCenter(
        center_id="BUSAN-BEXCO-MICE",
        name="벡스코 (BEXCO)",
        region="부산",
        sub_region="해운대구",
        category="MICE·판로지원",
        website_url="https://www.bexco.co.kr",
        supports_office=False,
        office_details="B2B 수출상담장, 마이스 스타트업 지원 라운지 및 컨퍼런스룸",
        supports_grants=True,
        grant_details="기후산업국제박람회(WCE), 국제수산무역엑스포(BISFE) 부스 임차 및 해외 마케팅 지원",
        target_qualifications="해양·물류, 친환경 에너지, ICT 스타트업 및 부울경 중소기업",
        contact_info="051-740-7300 / 부산시 해운대구 APEC로 55",
    ),
    LocalSupportCenter(
        center_id="DAEGU-EXCO-MICE",
        name="엑스코 (EXCO)",
        region="대구",
        sub_region="북구",
        category="MICE·판로지원",
        website_url="https://www.exco.co.kr",
        supports_office=False,
        office_details="신기술 발표회 및 비즈니스 수출 상담 공간, 기업 브리핑룸",
        supports_grants=True,
        grant_details="대구 국제 미래모빌리티엑스포(DIFA), 메디엑스포 참가지원 및 해외 바이어 초청 지원",
        target_qualifications="미래모빌리티, 첨단 로봇, 디지털 헬스케어 관련 혁신 기업",
        contact_info="053-601-5000 / 대구시 북구 엑스코로 10",
    ),
    LocalSupportCenter(
        center_id="GWANGJU-KDJ-MICE",
        name="김대중컨벤션센터 (KDJ Center)",
        region="광주",
        sub_region="서구",
        category="MICE·판로지원",
        website_url="https://kdjcenter.gjto.or.kr",
        supports_office=False,
        office_details="호남권 최대 컨벤션 수출 밋업 라운지 및 비즈니스 상담실",
        supports_grants=True,
        grant_details="BIXPO(빛가람 국제 전력기술 엑스포), 에너지/AI 기업 판로 개척 및 수출상담회 바우처",
        target_qualifications="호남권 에너지신산업, 인공지능, 미래차 관련 중소·벤처기업",
        contact_info="062-611-2000 / 광주시 서구 상무누리로 30",
    ),
    LocalSupportCenter(
        center_id="DAEJEON-DCC-MICE",
        name="대전컨벤션센터 (DCC)",
        region="대전",
        sub_region="유성구",
        category="MICE·판로지원",
        website_url="https://www.dcckorea.or.kr",
        supports_office=False,
        office_details="대덕연구개발특구 연계 과학기술 비즈니스 미팅룸 및 화상회의실",
        supports_grants=True,
        grant_details="나노반도체, 국방서비스로봇, 바이오헬스 학술·전시 및 기술이전 매칭 지원",
        target_qualifications="대덕특구 연구원 창업기업, 딥테크 스타트업 및 국방/나노 기업",
        contact_info="042-250-1100 / 대전시 유성구 엑스포로 107",
    ),
    LocalSupportCenter(
        center_id="GYEONGNAM-CECO-MICE",
        name="창원컨벤션센터 (CECO)",
        region="경남",
        sub_region="창원시",
        category="MICE·판로지원",
        website_url="https://www.ceco.co.kr",
        supports_office=False,
        office_details="동남권 정밀기계·방위산업 B2B 수출 상담장 및 기업지원센터",
        supports_grants=True,
        grant_details="첨단정밀기계, 첨단항공부품, SMR 원자력 산업전 참가 부스 및 글로벌 바이어 상담 지원",
        target_qualifications="경남 및 동남권 정밀기계, 원자력/방산, 항공우주 제조 기업",
        contact_info="055-212-1000 / 경남 창원시 성산구 원이대로 362",
    ),
]


class LocalCentersService:
    """전국 지자체별 과제 및 사무실 지원 센터 검색/필터링 서비스 계층."""

    def __init__(self, catalog: Optional[List[LocalSupportCenter]] = None) -> None:
        self._catalog = catalog or LOCAL_CENTERS_CATALOG

    def get_centers(
        self,
        region: Optional[str] = None,
        category: Optional[str] = None,
        office_only: bool = False,
        grants_only: bool = False,
        keyword: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """조건별 지자체 지원센터 목록 필터링."""
        results: List[Dict[str, Any]] = []
        kw = keyword.lower().strip() if keyword else None

        for center in self._catalog:
            # 1. 지역 필터
            if region and region != "전국":
                if region not in center.region and region not in center.sub_region:
                    continue

            # 2. 카테고리 필터
            if category and category != "전체":
                if category not in center.category:
                    continue

            # 3. 사무실 지원 여부 필터
            if office_only and not center.supports_office:
                continue

            # 4. 과제 지원 여부 필터
            if grants_only and not center.supports_grants:
                continue

            # 5. 키워드 검색
            if kw:
                haystack = f"{center.name} {center.sub_region} {center.office_details} {center.grant_details} {center.target_qualifications}".lower()
                if kw not in haystack:
                    continue

            results.append(center.to_dict())

        return results

    def get_regions_summary(self) -> Dict[str, int]:
        """지역별 센터 수 요약 집계."""
        summary: Dict[str, int] = {}
        for center in self._catalog:
            summary[center.region] = summary.get(center.region, 0) + 1
        return summary

"""
원클릭 프로젝트 생성기 (Scaffolder)
- 디렉토리 트리
- config (master_portals.yaml / mail_config.yaml)
- 2종 샘플 사업 아이템 (item_01 디지털 MRV, item_02 AI 음성 분리)
- SQLite 마스터 DB 스키마

실행:  python3 bootstrap_project.py
"""

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path("gov-grant-automation")

DIRECTORIES = [
    "config",
    "items/item_01_carbon_dmrv",
    "items/item_02_voice_ai",
    "storage/chroma_db",
    "storage/downloads",
    "src/common/llm",
    "src/collector",
    "src/deduplicator",
    "src/parser",
    "src/matcher",
    "src/notifier",
    "opencode/agents",
    "tests",
]

# ---------------------------------------------------------------------------
# config/master_portals.yaml
# ---------------------------------------------------------------------------
MASTER_PORTALS_YAML = """portals:
  k_startup:
    name: "K-Startup 창업지원포털"
    adapter_type: "TypeA_OpenAPI_Scrape"
    base_url: "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do"
    api_endpoint: "https://apis.data.go.kr/B552735/kisedKstartupService/getAnnouncementInformation"

  g2b:
    name: "나라장터 국가종합전자조달"
    adapter_type: "TypeB_G2B_API"
    base_url: "https://www.g2b.go.kr/"
    api_endpoint: "http://apis.data.go.kr/1230000/BidPublicInfoService04/getBidPblancListInfoServcPPSSrch01"

  ntis:
    name: "NTIS 국가과학기술지식정보서비스"
    adapter_type: "TypeC_RndAggregator"
    base_url: "https://www.ntis.go.kr/rndgate/eg/un/ra/mng.do"

  iris:
    name: "IRIS 범부처통합연구지원시스템"
    adapter_type: "TypeC_RndAggregator"
    base_url: "https://www.iris.go.kr/"

  nipa:
    name: "정보통신산업진흥원(NIPA)"
    adapter_type: "TypeD_AgencyBoard"
    base_url: "https://www.nipa.kr/home/2-2"
    ministry: "과학기술정보통신부"

  keit:
    name: "KEIT 산업기술R&D 정보포털(이로움)"
    adapter_type: "TypeD_AgencyBoard"
    base_url: "https://srome.keit.re.kr/"
    ministry: "산업통상자원부"

  smtech:
    name: "SMTECH 중소기업기술개발사업"
    adapter_type: "TypeD_AgencyBoard"
    base_url: "https://www.smtech.go.kr/"
    ministry: "중소벤처기업부"

  khidi:
    name: "KHIDI 한국보건산업진흥원"
    adapter_type: "TypeD_AgencyBoard"
    base_url: "https://www.khidi.or.kr/"
    ministry: "보건복지부"

  rndia:
    name: "RNDIA 한국산업기술진흥협회"
    adapter_type: "TypeD_AgencyBoard"
    base_url: "https://www.rndia.or.kr/board/rndBiz/list.do"

  modoo:
    name: "모두(Modoo) 지원포털"
    adapter_type: "TypeD_AgencyBoard"
    base_url: "https://www.modoo.or.kr/"

  songpa_se:
    name: "송파구 사회적경제지원센터"
    adapter_type: "TypeE_LegacyASP"
    base_url: "https://www.songpase.org/bbs.asp"
    static_params:
      pc: "n01"
"""

# ---------------------------------------------------------------------------
# config/mail_config.yaml
# ---------------------------------------------------------------------------
MAIL_CONFIG_YAML = """smtp:
  host: "smtp.gmail.com"
  port: 587
  # 계정 정보는 .env 를 통해 주입 (하드코딩 금지). .env.example 참조.
  username: "${SMTP_USERNAME}"
  password: "${SMTP_PASSWORD}"
  sender_name: "정부과제 AI 매칭 에이전트"
  max_attachment_size_mb: 20
"""

# ---------------------------------------------------------------------------
# items/item_01_carbon_dmrv
# ---------------------------------------------------------------------------
ITEM_01_PROFILE_YAML = """item_meta:
  item_id: "item_01_carbon_dmrv"
  item_name: "AI 기반 디지털 MRV 및 탄소배출권 자산 라우팅 플랫폼"
  recipients: ["pm@company.com"]

collection_scope:
  selected_bookmarks: ["k_startup", "ntis", "iris", "nipa", "keit", "smtech", "g2b", "songpa_se"]
  enable_open_web_discovery: true

eligibility_specs:
  entity_type: "법인사업자"
  founded_date: "2023-05-10"
  business_age_years: 3
  headquarters_location: "경기도 성남시"
  branch_locations: ["서울특별시"]
  employee_count: 8
  recent_annual_revenue_krw: 500000000
  certifications: ["벤처기업", "기업부설연구소"]
  ip_patents_count: 3

rnd_and_bid_specs:
  has_rnd_institute: true
  current_trl: 6
  consortium_possible: true
  g2b_license_codes: ["1468"]
  direct_production_certs: ["정보시스템개발서비스"]

domain_routing:
  target_ministries: ["과학기술정보통신부", "산업통상자원부", "중소벤처기업부", "환경부"]
  core_keywords: ["탄소배출권", "디지털 MRV", "기후테크", "스마트빌딩", "에너지", "블록체인", "AX"]
  exclude_keywords: ["단순 제조", "전통시장", "소상공인 점포개선", "바이오 임상"]
  min_match_score: 75

owner_confirmed_policies:
  max_acceptable_cash_match_krw: 50000000
  accept_mandatory_hiring: true
  available_demand_partners: ["운수사 컨소시엄", "지자체 및 금융기관"]
"""

ITEM_01_PROPOSAL_MD = """[사업계획서 핵심 요약: AI 기반 디지털 MRV 및 탄소배출권 플랫폼]

1. 핵심 기술 및 솔루션 개요
- 수송(EV 및 상용차), 스마트빌딩, 축산 메탄 감축 등 다중 섹터에서 발생하는 온실가스 감축 데이터를 실시간 수집하고 AI로 표준화하는 디지털 MRV(측정·보고·검증) 인프라 플랫폼.
- 감축량 산정 알고리즘 자동화, 하이브리드 크레딧 매칭, 블록체인 기반 탄소배출권 생명주기 추적 기술(관련 특허 3건 출원 완료).

2. 주요 적용 분야 및 실증 실적
- 전기차 및 모빌리티 운행 데이터 기반 온실가스 감축 외부사업 등록 및 블록체인 거래 플랫폼 구축 완료.
- 기업 ESG 스폰서, 중소기업, 금융 매수자를 연결하는 탄소금융 및 자산 라우팅 아키텍처 보유.
"""

# ---------------------------------------------------------------------------
# items/item_02_voice_ai  (샘플 제2사업 아이템)
# ---------------------------------------------------------------------------
ITEM_02_PROFILE_YAML = """item_meta:
  item_id: "item_02_voice_ai"
  item_name: "AI 음성 분리 및 다자간 화자 인식 솔루션"
  recipients: ["pm@company.com"]

collection_scope:
  selected_bookmarks: ["k_startup", "nipa", "smtech", "modoo", "g2b", "ntis"]
  enable_open_web_discovery: true

eligibility_specs:
  entity_type: "법인사업자"
  founded_date: "2021-09-01"
  business_age_years: 5
  headquarters_location: "서울특별시 마포구"
  branch_locations: []
  employee_count: 12
  recent_annual_revenue_krw: 1200000000
  certifications: ["벤처기업", "기업부설연구소", "ISO/IEC 27001"]
  ip_patents_count: 5

rnd_and_bid_specs:
  has_rnd_institute: true
  current_trl: 7
  consortium_possible: true
  g2b_license_codes: ["1468", "1724"]
  direct_production_certs: ["정보시스템개발서비스", "소프트웨어개발업"]

domain_routing:
  target_ministries: ["과학기술정보통신부", "중소벤처기업부"]
  core_keywords: ["음성분리", "화자인식", "음성인식", "언어모델", "AI 반도체", "AX", "딥파스킹 방제"]
  exclude_keywords: ["단순 제조", "전통시장", "농수산업"]
  min_match_score: 75

owner_confirmed_policies:
  max_acceptable_cash_match_krw: 70000000
  accept_mandatory_hiring: true
  available_demand_partners: ["공공기관", "금융권", "통신사"]
"""

ITEM_02_PROPOSAL_MD = """[사업계획서 핵심 요약: AI 음성 분리 및 다자간 화자 인식 솔루션]

1. 핵심 기술 및 솔루션 개요
- 4명 이상 동시 대화가 가능한 화자 분리(Speaker Diarization)와 화자 검증(Speaker Verification)을 통합한 온프레미스 음성 AI 솔루션.
- 초소형 디코드어와 경량화(ONNX/TensorRT) 기반기의 에지 인퍼런스, 딥파스킹(Deepfake) 판별 모듈 내장.

2. 주요 적용 분야 및 실증 실적
- 금융 콜센터·법률회의록·의료진담 등 민감 대화 환경의 화자 인식 실증 완료.
- 공공·금융 수요처 3곳과 상용화 계약(POC) 수행.
"""


def init_database(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.executescript(
        """
    CREATE TABLE IF NOT EXISTS announcements (
        canonical_id TEXT PRIMARY KEY,
        official_notice_no TEXT,
        title TEXT NOT NULL,
        organization TEXT,
        ministry TEXT,
        deadline TEXT,
        source_portal TEXT,
        detail_url TEXT,
        local_attachment_dir TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS rfp_chunks (
        rfp_id TEXT PRIMARY KEY,
        canonical_id TEXT,
        rfp_number TEXT,
        rfp_title TEXT,
        target_trl TEXT,
        budget_info TEXT,
        markdown_content TEXT,
        FOREIGN KEY(canonical_id) REFERENCES announcements(canonical_id)
    );

    CREATE TABLE IF NOT EXISTS site_selectors (
        domain TEXT PRIMARY KEY,
        row_selector TEXT,
        title_selector TEXT,
        date_selector TEXT,
        link_selector TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS dispatch_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id TEXT,
        canonical_id TEXT,
        rfp_id TEXT,
        match_score INTEGER,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(item_id, canonical_id, rfp_id)
    );
    """
    )
    conn.commit()
    conn.close()


def build_workspace() -> None:
    for d in DIRECTORIES:
        (PROJECT_ROOT / d).mkdir(parents=True, exist_ok=True)

    (PROJECT_ROOT / "config/master_portals.yaml").write_text(MASTER_PORTALS_YAML, encoding="utf-8")
    (PROJECT_ROOT / "config/mail_config.yaml").write_text(MAIL_CONFIG_YAML, encoding="utf-8")

    for d in DIRECTORIES:
        # .gitkeep 을 빈 디렉터리에 배치
        if d.split("/")[-1] in ("chroma_db", "downloads"):
            (PROJECT_ROOT / d / ".gitkeep").touch()

    (PROJECT_ROOT / "items/item_01_carbon_dmrv/profile.yaml").write_text(ITEM_01_PROFILE_YAML, encoding="utf-8")
    (PROJECT_ROOT / "items/item_01_carbon_dmrv/proposal.md").write_text(ITEM_01_PROPOSAL_MD, encoding="utf-8")
    (PROJECT_ROOT / "items/item_01_carbon_dmrv/custom_urls.yaml").write_text("custom_urls: []\n", encoding="utf-8")

    (PROJECT_ROOT / "items/item_02_voice_ai/profile.yaml").write_text(ITEM_02_PROFILE_YAML, encoding="utf-8")
    (PROJECT_ROOT / "items/item_02_voice_ai/proposal.md").write_text(ITEM_02_PROPOSAL_MD, encoding="utf-8")
    (PROJECT_ROOT / "items/item_02_voice_ai/custom_urls.yaml").write_text("custom_urls: []\n", encoding="utf-8")

    init_database(PROJECT_ROOT / "storage/grant_master.db")
    print(f"[완료] {PROJECT_ROOT.resolve()} 경로에 프로젝트 초기 환경이 구축되었습니다.")


if __name__ == "__main__":
    build_workspace()

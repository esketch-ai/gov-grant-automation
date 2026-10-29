"""
REQ-003 · SQLite DB 영속화 계층 (박준호/정민재 담당)

파이프라인 단계별 영속화 + 중복발송 방지(REQ-005 연계)를 위한 안전 degrade 레퍼런스.
- announcements            : 수집·중복제거 후 canonical 공고 영속화
- rfp_chunks               : 분할된 RFP 청크 영속화
- dispatch_history         : 발송 건(중복발송 방지, UNIQUE(item_id,canonical_id,rfp_id))

설계 원칙(최은정/박준호):
- DB 연동 실패는 **파이프라인을 멈추지 않는다**. 모든 공개 메서드는 try/except로 감싸
  예외 시 WARN 로그 + 무해한 반환값(degrade sentinel)을 제공한다.
- 스키마는 idempotent(CREATE TABLE IF NOT EXISTS)으로 db.py가 스스로 보강한다.
"""
from __future__ import annotations

import re
import json
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

from .logging_config import get_logger
from .schemas import RawNotice

logger = get_logger("db")


class GrantDatabase:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)

    # ------------------------------------------------------------------ schema
    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def ensure_schema(self) -> None:
        """idempotent 스키마 보강(스스로 self-sufficient하게)."""
        try:
            with self._connect() as conn:
                conn.executescript(
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
                    target_year INTEGER DEFAULT 2026,
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
                CREATE TABLE IF NOT EXISTS company_profile (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    company_name TEXT,
                    biz_reg_no TEXT,
                    opened_date TEXT,
                    founder_birth TEXT,
                    founder_gender TEXT,
                    address TEXT,
                    debt_ratio_pct REAL,
                    has_rnd_lab INTEGER DEFAULT 0,
                    is_capital_impaired INTEGER DEFAULT 0,
                    has_tax_arrears INTEGER DEFAULT 0,
                    current_pi_projects INTEGER DEFAULT 0,
                    current_member_projects INTEGER DEFAULT 0,
                    registered_patents_count INTEGER DEFAULT 0,
                    available_cash_fund INTEGER DEFAULT 0,
                    prior_grant_history TEXT,
                    certifications TEXT,
                    tags TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS tenants (
                    id TEXT PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    biz_reg_no TEXT,
                    opened_date TEXT,
                    rep_name TEXT,
                    region TEXT,
                    plan_tier TEXT DEFAULT 'PRO',
                    tenant_salt TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    email TEXT NOT NULL,
                    name TEXT NOT NULL,
                    avatar_url TEXT,
                    auth_provider TEXT DEFAULT 'google',
                    role TEXT DEFAULT 'OWNER',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(tenant_id) REFERENCES tenants(id)
                );
                CREATE TABLE IF NOT EXISTS tenant_assets (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    asset_category TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_size INTEGER DEFAULT 0,
                    content_text TEXT,
                    parsed_metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(tenant_id) REFERENCES tenants(id)
                );
                CREATE TABLE IF NOT EXISTS grant_projects (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    announcement_id TEXT,
                    announcement_title TEXT,
                    template_id TEXT DEFAULT 'PSST',
                    status TEXT DEFAULT 'DRAFTING',
                    progress_pct INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(tenant_id) REFERENCES tenants(id)
                );
                -- REQ-032 · 실전 유료화 B2B SaaS 스키마
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    plan_code TEXT NOT NULL,
                    billing_cycle TEXT DEFAULT 'monthly',
                    supply_price INTEGER DEFAULT 0,
                    vat_amount INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'ACTIVE',
                    current_period_start TEXT,
                    current_period_end TEXT,
                    dunning_retry_count INTEGER DEFAULT 0,
                    billing_key_enc TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS payments (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    subscription_id TEXT,
                    payment_type TEXT DEFAULT 'SUBSCRIPTION',
                    supply_amount INTEGER DEFAULT 0,
                    vat_amount INTEGER DEFAULT 0,
                    total_amount INTEGER DEFAULT 0,
                    refunded_amount INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'PAID',
                    tax_invoice_status TEXT DEFAULT 'ISSUED',
                    receipt_url TEXT,
                    paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS credit_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    delta INTEGER NOT NULL,
                    balance_after INTEGER NOT NULL,
                    reason TEXT,
                    project_id TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS proposal_snapshots (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    tenant_id TEXT NOT NULL,
                    version_no INTEGER DEFAULT 1,
                    encrypted_sections_blob TEXT,
                    encrypted_budget_blob TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT,
                    actor_user_id TEXT,
                    category TEXT,
                    action TEXT,
                    ip_address TEXT DEFAULT '',
                    prev_hash TEXT NOT NULL,
                    curr_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                -- REQ-047 · 바이브코딩 프로토타입 검증 엔진 & 7:3 피드백 리워드 경제
                CREATE TABLE IF NOT EXISTS prototype_campaigns (
                    id TEXT PRIMARY KEY,
                    item_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    prototype_url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    target_testers INTEGER DEFAULT 50,
                    fee_per_test INTEGER DEFAULT 2000,
                    tester_reward INTEGER DEFAULT 1400,
                    platform_fee INTEGER DEFAULT 600,
                    total_budget INTEGER DEFAULT 100000,
                    completed_testers INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'ACTIVE',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    request_type TEXT DEFAULT 'PAID',
                    category TEXT DEFAULT '일반',
                    target_goal TEXT DEFAULT '',
                    payment_status TEXT DEFAULT 'COMPLETED',
                    payment_id TEXT DEFAULT '',
                    is_featured INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS prototype_payments (
                    payment_id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    payment_method TEXT NOT NULL,
                    payment_status TEXT NOT NULL,
                    paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS prototype_sessions (
                    id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL,
                    tester_id TEXT NOT NULL,
                    active_seconds INTEGER DEFAULT 0,
                    visible_seconds INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'STARTED',
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS prototype_feedbacks (
                    id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL,
                    session_id TEXT NOT NULL UNIQUE,
                    tester_id TEXT NOT NULL,
                    tester_alias TEXT NOT NULL,
                    dwell_seconds INTEGER NOT NULL,
                    ux_score INTEGER NOT NULL,
                    functionality_score INTEGER NOT NULL,
                    willingness_to_pay INTEGER NOT NULL,
                    nps_recommend_score INTEGER NOT NULL,
                    blocker_category TEXT NOT NULL,
                    qualitative_feedback TEXT NOT NULL,
                    reward_amount INTEGER NOT NULL,
                    reward_status TEXT DEFAULT 'PAID',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_campaign_tester_unique ON prototype_feedbacks (campaign_id, tester_id);
                CREATE TABLE IF NOT EXISTS notebook_sync_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notebook_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    added_count INTEGER DEFAULT 0,
                    updated_count INTEGER DEFAULT 0,
                    total_count INTEGER DEFAULT 0,
                    sync_hash TEXT,
                    message TEXT,
                    payload_snapshot TEXT
                );
                CREATE TABLE IF NOT EXISTS dynamic_global_grants (
                    program_id TEXT PRIMARY KEY,
                    country TEXT NOT NULL,
                    country_code TEXT,
                    city_hub TEXT,
                    program_name TEXT NOT NULL,
                    program_name_en TEXT,
                    supervising_entity TEXT,
                    operating_entity TEXT,
                    specialized_fields TEXT,
                    support_type TEXT,
                    financial_benefit TEXT,
                    visa_benefit TEXT,
                    space_facility_benefit TEXT,
                    mentoring_network TEXT,
                    target_qualifications TEXT,
                    selection_scale TEXT,
                    source_portal TEXT,
                    detail_url TEXT,
                    inquiry_contact TEXT,
                    case_studies TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    version INTEGER DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS dynamic_master_grants (
                    program_id TEXT PRIMARY KEY,
                    program_name TEXT NOT NULL,
                    category TEXT,
                    supervising_ministry TEXT,
                    operating_agency TEXT,
                    region_scope TEXT,
                    target_stage TEXT,
                    target_qualifications TEXT,
                    expected_period TEXT,
                    expected_month INTEGER DEFAULT 0,
                    support_scale TEXT,
                    support_details TEXT,
                    inquiry_contact TEXT,
                    source_portal TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    version INTEGER DEFAULT 1
                );
                """
                )
                # prototype_campaigns 컬럼 동적 마이그레이션 (기존 DB 호환)
                for col_name, col_type in [
                    ("request_type", "TEXT DEFAULT 'PAID'"),
                    ("category", "TEXT DEFAULT '일반'"),
                    ("target_goal", "TEXT DEFAULT ''"),
                    ("payment_status", "TEXT DEFAULT 'COMPLETED'"),
                    ("payment_id", "TEXT DEFAULT ''"),
                    ("is_featured", "INTEGER DEFAULT 0"),
                ]:
                    try:
                        conn.execute(f"ALTER TABLE prototype_campaigns ADD COLUMN {col_name} {col_type}")
                    except Exception:
                        pass

                # company_profile 단일행(id=1) 기본행 확보(프로필 부재 시 빈 상태 반환 방지)
                conn.execute("INSERT OR IGNORE INTO company_profile (id) VALUES (1);")
                # 기본 테넌트 및 데모 사용자 시드 (하위 호환성 유지)
                conn.execute("""
                INSERT OR IGNORE INTO tenants (id, company_name, biz_reg_no, opened_date, rep_name, region, plan_tier)
                VALUES ('tenant_default', '(주)초롱소프트 / SSHAI', '123-45-67890', '2024-01-15', '홍길동', '서울', 'PRO');
                """)
                conn.execute("""
                INSERT OR IGNORE INTO users (id, tenant_id, email, name, auth_provider, role)
                VALUES ('user_default', 'tenant_default', 'ceo@chorong.ai', '홍길동 대표', 'local_demo', 'OWNER');
                """)
                # REQ-047 데모 바이브코딩 검증 캠페인 시드 (유료 보증 + 무료 품앗이 듀얼 트랙)
                conn.execute("""
                INSERT OR IGNORE INTO prototype_campaigns (
                    id, item_id, tenant_id, prototype_url, title, description,
                    target_testers, fee_per_test, tester_reward, platform_fee, total_budget,
                    completed_testers, status, created_at, request_type, category, target_goal, payment_status, is_featured
                ) VALUES (
                    'camp_01_carbon_dmrv', 'item_01_carbon_dmrv', 'tenant_default',
                    'https://carbon-dmrv-demo.vibecoding.app',
                    '2026 탄소배출권 디지털 MRV 및 에너지 AX 웹앱',
                    '센서 데이터 자동 집계 및 온실가스 배출량 인증 보고서 생성 프로토타입 실사용 검증',
                    50, 2000, 1400, 600, 100000, 34, 'ACTIVE', '2026-10-27 10:00:00',
                    'PAID', '기후/에너지', '사업계획서 시장 검증 증빙', 'PAID', 1
                );
                """)
                conn.execute("""
                INSERT OR IGNORE INTO prototype_campaigns (
                    id, item_id, tenant_id, prototype_url, title, description,
                    target_testers, fee_per_test, tester_reward, platform_fee, total_budget,
                    completed_testers, status, created_at, request_type, category, target_goal, payment_status, is_featured
                ) VALUES (
                    'camp_02_voice_ai', 'item_02_voice_ai', 'tenant_default',
                    'https://ondevice-voice-ai.vibecoding.app',
                    '초경량 온디바이스 음성인식 AI 컨트롤러',
                    '네트워크 단절 환경에서의 산업용 음성 커맨드 제어 반응속도 및 오인식률 테스트',
                    30, 2000, 1400, 600, 60000, 12, 'ACTIVE', '2026-10-27 14:00:00',
                    'PAID', 'AI/딥테크', '현장 음성인식 UX 검증', 'PAID', 1
                );
                """)
                conn.execute("""
                INSERT OR IGNORE INTO prototype_campaigns (
                    id, item_id, tenant_id, prototype_url, title, description,
                    target_testers, fee_per_test, tester_reward, platform_fee, total_budget,
                    completed_testers, status, created_at, request_type, category, target_goal, payment_status, is_featured
                ) VALUES (
                    'camp_03_local_fnb', 'item_03_local_fnb', 'tenant_default',
                    'https://local-fnb-order.figma.site',
                    '로컬 골목상권 단골 리워드 & 테이블오더 기획안 (Figma)',
                    '소상공인 매장용 QR 테이블오더 주문 동선 및 단골 스탬프 UI/UX 품앗이 피드백을 구합니다.',
                    10, 0, 0, 0, 0, 7, 'ACTIVE', '2026-10-28 11:00:00',
                    'FREE', '로컬/F&B', '주문 플로우 및 UI 편의성 검증', 'FREE', 0
                );
                """)
                conn.execute("""
                INSERT OR IGNORE INTO prototype_campaigns (
                    id, item_id, tenant_id, prototype_url, title, description,
                    target_testers, fee_per_test, tester_reward, platform_fee, total_budget,
                    completed_testers, status, created_at, request_type, category, target_goal, payment_status, is_featured
                ) VALUES (
                    'camp_04_saas_crm', 'item_04_saas_crm', 'tenant_default',
                    'https://b2b-lead-crm.app',
                    'B2B 영업 리드 파이프라인 자동화 SaaS',
                    '중소기업 맞춤 견적서 자동 생성 및 계약 전환율 개선 기능 실사용 테스터 모집',
                    50, 2000, 1400, 600, 100000, 28, 'ACTIVE', '2026-10-28 13:30:00',
                    'PAID', 'SaaS/플랫폼', 'B2B 결제전환율 측정', 'PAID', 1
                );
                """)
                conn.execute("""
                INSERT OR IGNORE INTO prototype_campaigns (
                    id, item_id, tenant_id, prototype_url, title, description,
                    target_testers, fee_per_test, tester_reward, platform_fee, total_budget,
                    completed_testers, status, created_at, request_type, category, target_goal, payment_status, is_featured
                ) VALUES (
                    'camp_05_edu_vr', 'item_05_edu_vr', 'tenant_default',
                    'https://edu-metaverse-demo.web.app',
                    '직업계고 실습용 인터랙티브 가상 시뮬레이터',
                    '위험 산업설비 안전교육 가상체험 시뮬레이터 학생 몰입도 및 UX 동료 평가 요청',
                    15, 0, 0, 0, 0, 9, 'ACTIVE', '2026-10-28 15:00:00',
                    'FREE', '문화/콘텐츠', '몰입도 및 인터랙션 평가', 'FREE', 0
                );
                """)
                conn.execute("""
                INSERT OR IGNORE INTO prototype_campaigns (
                    id, item_id, tenant_id, prototype_url, title, description,
                    target_testers, fee_per_test, tester_reward, platform_fee, total_budget,
                    completed_testers, status, created_at, request_type, category, target_goal, payment_status, is_featured
                ) VALUES (
                    'camp_06_health_ai', 'item_06_health_ai', 'tenant_default',
                    'https://smart-vital-care.app',
                    '시니어 웨어러블 바이탈 이상징후 조기감지 케어앱',
                    '보호자 안심 알림 및 긴급호출 인터페이스 50명 실사용 검증 (정부지원사업 제출용)',
                    50, 2000, 1400, 600, 100000, 41, 'ACTIVE', '2026-10-28 16:20:00',
                    'PAID', '바이오/헬스', '정부과제 시장반응 증빙', 'PAID', 1
                );
                """)
                conn.execute("""
                INSERT OR IGNORE INTO prototype_campaigns (
                    id, item_id, tenant_id, prototype_url, title, description,
                    target_testers, fee_per_test, tester_reward, platform_fee, total_budget,
                    completed_testers, status, created_at, request_type, category, target_goal, payment_status, is_featured
                ) VALUES (
                    'camp_07_creator_pay', 'item_07_creator_pay', 'tenant_default',
                    'https://creator-settle.notion.site',
                    '1인 크리에이터 간편 정산 및 세무 증빙 노션 기획안',
                    '복잡한 외주 정산 및 부가세 신고 자동 매칭 기획안에 대한 초기 프리랜서 피드백',
                    10, 0, 0, 0, 0, 4, 'ACTIVE', '2026-10-28 17:00:00',
                    'FREE', '핀테크/금융', '초기 기획안 논리 및 편의성 검증', 'FREE', 0
                );
                """)
                # REQ-047 데모 피드백 시드
                sample_feedbacks = [
                    ('fb_demo_01', 'camp_01_carbon_dmrv', 'sess_seed_01', 'tester_01', '동료 창업자 #12 (기후테크)', 142, 5, 4, 4, 9, '기능오류/버그', '데이터 연동 속도가 빠르고 직관적입니다. 엑셀 내보내기 서식 지원이 추가되면 좋겠습니다.', 1400, 'PAID', '2026-10-27 11:20:00'),
                    ('fb_demo_02', 'camp_01_carbon_dmrv', 'sess_seed_02', 'tester_02', '제조업 전문 대표님 #07', 95, 4, 5, 5, 10, '기타', '현장 센서와의 실시간 동기화 인터페이스가 우수합니다. 공장별 커스텀 대시보드 기능이 필요합니다.', 1400, 'PAID', '2026-10-27 13:45:00'),
                    ('fb_demo_03', 'camp_01_carbon_dmrv', 'sess_seed_03', 'tester_03', '초기창업자 #88 (SaaS)', 180, 4, 4, 3, 8, '속도지연', '초기 로딩 시 대용량 데이터 렌더링에 약간의 지연이 발생하지만 전체적인 분석 프로세스가 명확합니다.', 1400, 'PAID', '2026-10-27 15:10:00'),
                    ('fb_demo_04', 'camp_01_carbon_dmrv', 'sess_seed_04', 'tester_04', 'ESG 컨설턴트 #19', 210, 5, 5, 5, 10, '기타', '정부 온실가스 배출권 검증 가이드라인에 완벽히 부합하는 필수 입력 필드가 잘 정리되어 있습니다.', 1400, 'PAID', '2026-10-27 17:30:00'),
                    ('fb_demo_05', 'camp_01_carbon_dmrv', 'sess_seed_05', 'tester_05', 'IT 솔루션 대표 #34', 85, 3, 4, 3, 7, 'UI깨짐/가독성', '모바일 반응형 뷰에서 일부 차트 범례가 겹쳐 보입니다. 데스크톱 뷰는 매우 훌륭합니다.', 1400, 'PAID', '2026-10-28 09:15:00'),
                ]
                for fb in sample_feedbacks:
                    conn.execute("""
                    INSERT OR IGNORE INTO prototype_feedbacks (
                        id, campaign_id, session_id, tester_id, tester_alias,
                        dwell_seconds, ux_score, functionality_score, willingness_to_pay,
                        nps_recommend_score, blocker_category, qualitative_feedback,
                        reward_amount, reward_status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """, fb)
                # 기존 테이블 마이그레이션: target_year 컬럼 유무 점검 및 추가
                cols = [r["name"] for r in conn.execute("PRAGMA table_info(announcements)").fetchall()]
                if "target_year" not in cols:
                    conn.execute("ALTER TABLE announcements ADD COLUMN target_year INTEGER DEFAULT 2026;")
                # REQ-030: tenant_salt 컬럼 유무 점검 및 추가(idempotent)
                tcols = [r["name"] for r in conn.execute("PRAGMA table_info(tenants)").fetchall()]
                if "tenant_salt" not in tcols:
                    conn.execute("ALTER TABLE tenants ADD COLUMN tenant_salt TEXT DEFAULT '';")
                # REQ-032: 1테넌트=1사업자 Hard-Lock / 구독 / 멤버십 잔여 한도 컬럼 보강(idempotent)
                if "biz_model" not in tcols:
                    conn.execute("ALTER TABLE tenants ADD COLUMN biz_model TEXT DEFAULT 'ict_deeptech';")
                if "subscription_tier" not in tcols:
                    conn.execute("ALTER TABLE tenants ADD COLUMN subscription_tier TEXT DEFAULT 'free';")
                if "credit_balance" not in tcols:
                    conn.execute("ALTER TABLE tenants ADD COLUMN credit_balance INTEGER DEFAULT 0;")
                conn.commit()
                # REQ-035: grant_master.db 기본 Ground-Truth 2026 공고 2건 시딩
                if self.db_path.name == "grant_master.db" and "pytest" not in str(self.db_path):
                    conn.execute(
                        """INSERT OR IGNORE INTO announcements
                           (canonical_id, official_notice_no, title, organization, ministry, deadline, source_portal, detail_url, target_year)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            "iris:2026_lam_ai",
                            "제2026-022696호",
                            "2026년도 인간-AI 협업형 LAM 개발 지원사업",
                            "정보통신기획평가원",
                            "과학기술정보통신부",
                            "2026-12-31",
                            "iris",
                            "https://www.iris.go.kr/contents/retrieveBsnsAncmView.do?ancmId=022696",
                            2026,
                        ),
                    )
                    conn.execute(
                        """INSERT OR IGNORE INTO announcements
                           (canonical_id, official_notice_no, title, organization, ministry, deadline, source_portal, detail_url, target_year)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            "k_startup:2026_master_biz",
                            "제2026-175783호",
                            "2026년도 중앙부처 및 지자체 창업지원사업 통합공고",
                            "창업진흥원",
                            "중소벤처기업부",
                            "2026-12-31",
                            "k_startup",
                            "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn=175783",
                            2026,
                        ),
                    )
        except Exception as e:
            logger.warning("DB 스키마 보강 실패(degrade): %s", e)

    # ------------------------------------------------------------------ 영속화
    def upsert_announcement(self, notice: RawNotice, canonical_id: str,
                            official_notice_no: str = "", target_year: Optional[int] = None) -> bool:
        """
        canonical_id 기준으로 INSERT OR REPLACE. 실패 시 False(return)·파이프라인 미중단.
        target_year가 지정되지 않은 경우 공고 텍스트에서 4자리 연도를 자동 추정하여 저장.
        """
        try:
            detected_year = target_year
            if detected_year is None:
                text_to_search = f"{notice.title} {official_notice_no} {notice.deadline}"
                found_years = [int(y) for y in re.findall(r"\b(202\d)\b", text_to_search)]
                detected_year = max(found_years) if found_years else 2026

            with self._connect() as conn:
                cur = conn.execute(
                    """INSERT OR REPLACE INTO announcements
                       (canonical_id, official_notice_no, title, organization,
                        ministry, deadline, source_portal, detail_url, local_attachment_dir, target_year)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (
                        canonical_id,
                        official_notice_no,
                        notice.title,
                        notice.organization,
                        notice.ministry,
                        notice.deadline,
                        notice.portal_id,
                        notice.detail_url,
                        str(notice.downloaded_files[0]) if notice.downloaded_files else "",
                        detected_year,
                    ),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.warning("upsert_announcement 실패[%s]: %s", canonical_id, e)
            return False

    def upsert_rfp_chunk(self, rfp_chunk: dict, canonical_id: str, rfp_id: str) -> bool:
        try:
            with self._connect() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO rfp_chunks
                       (rfp_id, canonical_id, rfp_number, rfp_title, target_trl,
                        budget_info, markdown_content)
                       VALUES (?,?,?,?,?,?,?)""",
                    (
                        rfp_id,
                        canonical_id,
                        rfp_chunk.get("rfp_number", ""),
                        rfp_chunk.get("rfp_title", ""),
                        rfp_chunk.get("target_trl", ""),
                        rfp_chunk.get("budget_info", ""),
                        rfp_chunk.get("content", ""),
                    ),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.warning("upsert_rfp_chunk 실패[%s]: %s", rfp_id, e)
            return False

    def get_rfp_chunks(self, canonical_id: str) -> List[dict]:
        """공고의 저장된 RFP 청크 목록을 조회합니다."""
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "SELECT rfp_id, canonical_id, rfp_number, rfp_title, markdown_content as content "
                    "FROM rfp_chunks WHERE canonical_id=?",
                    (canonical_id,),
                )
                return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            logger.warning("get_rfp_chunks 실패[%s]: %s", canonical_id, e)
            return []

    # ------------------------------------------------------------------ 발송 통제
    def is_dispatched(self, item_id: str, canonical_id: str, rfp_id: str) -> Optional[bool]:
        """
        이미 발송됐는지 확인.
        - True/False: DB 확인 결과(확정)
        - None: DB 접근 실패(degrade) — 호출측은 None 시 '안보존적으로 발송 건너뜀'
        """
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT 1 FROM dispatch_history WHERE item_id=? AND canonical_id=? AND rfp_id=?",
                    (item_id, canonical_id, rfp_id),
                ).fetchone()
            return row is not None
        except Exception as e:
            logger.warning("is_dispatched 확인 실패(degrade): %s", e)
            return None

    def record_dispatch(self, item_id: str, canonical_id: str, rfp_id: str,
                        match_score: int) -> Optional[bool]:
        """
        발송 기록. **새로운 건이면 True, 중복이면 False(DB UNIQUE제약+재확인).**
        DB 실패 시 None(degrade).
        """
        # 선재확인으로 중복 차단(UNIQUE 제약과 이중 안전장치)
        exists = self.is_dispatched(item_id, canonical_id, rfp_id)
        if exists is True:
            return False
        if exists is None:
            return None  # 확정 불가: degrade sentinel
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO dispatch_history (item_id, canonical_id, rfp_id, match_score) "
                    "VALUES (?,?,?,?)",
                    (item_id, canonical_id, rfp_id, match_score),
                )
                conn.commit()
            return True
        except Exception as e:
            # UNIQUE 제약 충돌(동시재입력)이면 중복으로 취급
            logger.warning("record_dispatch 실패[%s/%s]: %s", canonical_id, rfp_id, e)
            if "UNIQUE" in str(e):
                return False
            return None

    # ------------------------------------------------------------------ 조회
    def count_dispatched(self, item_id: Optional[str] = None) -> int:
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT COUNT(*) FROM dispatch_history"
                    + (" WHERE item_id=?" if item_id else ""),
                    (item_id,) if item_id else (),
                ).fetchone()
                return int(row[0]) if row else 0
        except Exception as e:
            logger.warning("count_dispatched 실패: %s", e)
            return 0

    # ------------------------------------------------------------------ 사이트 셀렉터 자가치유
    def get_site_selector(self, domain: str) -> Optional[dict]:
        """도메인별 크롤링 셀렉터 조회."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT domain, row_selector, title_selector, date_selector, link_selector, updated_at "
                    "FROM site_selectors WHERE domain=?",
                    (domain,),
                ).fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.warning("get_site_selector 실패[%s]: %s", domain, e)
            return None

    def upsert_site_selector(
        self,
        domain: str,
        row_selector: str,
        title_selector: str,
        date_selector: str,
        link_selector: str,
    ) -> bool:
        """자가치유된 최신 셀렉터 저장/갱신."""
        try:
            with self._connect() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO site_selectors
                       (domain, row_selector, title_selector, date_selector, link_selector, updated_at)
                       VALUES (?,?,?,?,?,CURRENT_TIMESTAMP)""",
                    (domain, row_selector, title_selector, date_selector, link_selector),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.warning("upsert_site_selector 실패[%s]: %s", domain, e)
            return False

    def list_site_selectors(self) -> List[dict]:
        """전체 등록된 사이트 셀렉터 목록 조회."""
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "SELECT domain, row_selector, title_selector, date_selector, link_selector, updated_at "
                    "FROM site_selectors ORDER BY updated_at DESC"
                )
                return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            logger.warning("list_site_selectors 실패: %s", e)
            return []

    # ------------------------------------------------------------------ 사업주 프로필 (REQ-020)
    _CP_JSON_COLS = ("prior_grant_history", "certifications", "tags")
    _CP_BOOL_COLS = ("has_rnd_lab", "is_capital_impaired", "has_tax_arrears")
    _CP_INT_COLS = (
        "current_pi_projects", "current_member_projects",
        "registered_patents_count", "available_cash_fund",
    )

    def _decode_profile_row(self, row: sqlite3.Row) -> dict:
        """sqlite 행 -> Python dict( JSON열 해독 / boolean·int 형식 환원)."""
        row = dict(row)
        for col in self._CP_JSON_COLS:
            raw = row.get(col)
            if not raw:
                row[col] = []
                continue
            try:
                row[col] = json.loads(raw)
            except Exception:
                row[col] = []
        for col in self._CP_BOOL_COLS:
            row[col] = bool(row.get(col))
        for col in self._CP_INT_COLS:
            v = row.get(col)
            row[col] = int(v) if v else 0
        return row

    def get_company_profile(self) -> Optional[dict]:
        """
        현재 저장된 사업주 프로필(id=1) 조회.
        - dict: 저장된 프로필(JSON 해독, boolean/int 환원)
        - None: DB 접근 실패(degrade) — 호출측은 빈 프로필 폴백 사용.
        (빈 기본행은 항상 존재 하므로 '미설정' 상태를 company_name로 구분.)
        """
        try:
            with self._connect() as conn:
                row = conn.execute("SELECT * FROM company_profile WHERE id=1").fetchone()
                if row is None:
                    return None
                return self._decode_profile_row(row)
        except Exception as e:
            logger.warning("get_company_profile 실패(degrade): %s", e)
            return None

    def upsert_company_profile(self, data: dict) -> bool:
        """
        사업주 프로필 저장/갱신(단일행 id=1 INSERT OR REPLACE).
        data는 company_profile 컬럼의 부분 집합 허용. 누락값은 기본값으로 보강.
        실패 시 False(return)·파이프라인 미중단(degrade).
        """
        if not isinstance(data, dict):
            logger.warning("upsert_company_profile: 타입 불일치 %s", type(data).__name__)
            return False

        def _g(col, default=None):
            return data.get(col, default)

        # JSON/boolean/int 정규화
        prior = _g("prior_grant_history", []) or []
        certs = _g("certifications", []) or []
        tags = _g("tags", []) or []
        if isinstance(prior, str):
            prior = [x.strip() for x in prior.split(",") if x.strip()]
        if isinstance(certs, str):
            certs = [x.strip() for x in certs.split(",") if x.strip()]
        if isinstance(tags, str):
            tags = [x.strip() for x in tags.split(",") if x.strip()]

        def _to_int(v):
            try:
                return int(v) if v not in (None, "", False) else 0
            except (ValueError, TypeError):
                return 0

        row = {
            "company_name": (str(_g("company_name", "") or "")).strip(),
            "biz_reg_no": (str(_g("biz_reg_no", "") or "")).strip(),
            "opened_date": (str(_g("opened_date", "") or "")).strip(),
            "founder_birth": (str(_g("founder_birth", "") or "")).strip(),
            "founder_gender": (str(_g("founder_gender", "") or "")).strip().upper()[:1] or "",
            "address": (str(_g("address", "") or "")).strip(),
            "debt_ratio_pct": (float(_g("debt_ratio_pct")) if _g("debt_ratio_pct") not in (None, "", False) else None),
            "has_rnd_lab": 1 if _g("has_rnd_lab") else 0,
            "is_capital_impaired": 1 if _g("is_capital_impaired") else 0,
            "has_tax_arrears": 1 if _g("has_tax_arrears") else 0,
            "current_pi_projects": _to_int(_g("current_pi_projects", 0)),
            "current_member_projects": _to_int(_g("current_member_projects", 0)),
            "registered_patents_count": _to_int(_g("registered_patents_count", 0)),
            "available_cash_fund": _to_int(_g("available_cash_fund", 0)),
            "prior_grant_history": json.dumps(prior, ensure_ascii=False),
            "certifications": json.dumps(certs, ensure_ascii=False),
            "tags": json.dumps(tags, ensure_ascii=False),
        }

        try:
            with self._connect() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO company_profile
                       (id, company_name, biz_reg_no, opened_date, founder_birth, founder_gender,
                        address, debt_ratio_pct, has_rnd_lab, is_capital_impaired, has_tax_arrears,
                        current_pi_projects, current_member_projects, registered_patents_count,
                        available_cash_fund, prior_grant_history, certifications, tags, updated_at)
                       VALUES (1,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
                    (
                        row["company_name"], row["biz_reg_no"], row["opened_date"],
                        row["founder_birth"], row["founder_gender"], row["address"],
                        row["debt_ratio_pct"], row["has_rnd_lab"],
                        row["is_capital_impaired"], row["has_tax_arrears"],
                        row["current_pi_projects"], row["current_member_projects"],
                        row["registered_patents_count"], row["available_cash_fund"],
                        row["prior_grant_history"], row["certifications"], row["tags"],
                    ),
                )
                conn.commit()
            return True
        except Exception as e:
            logger.warning("upsert_company_profile 실패(degrade): %s", e)
            return False

    def clear_company_profile(self) -> bool:
        """사업주 프로필 초기화(빈 기본행으로 리셋)."""
        try:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE company_profile SET company_name='', biz_reg_no='', opened_date='', "
                    "founder_birth='', founder_gender='', address='', debt_ratio_pct=NULL, "
                    "has_rnd_lab=0, is_capital_impaired=0, has_tax_arrears=0, current_pi_projects=0, "
                    "current_member_projects=0, registered_patents_count=0, available_cash_fund=0, "
                    "prior_grant_history='[]', certifications='[]', tags='[]', updated_at=CURRENT_TIMESTAMP "
                    "WHERE id=1",
                )
                conn.commit()
            return True
        except Exception as e:
            logger.warning("clear_company_profile 실패(degrade): %s", e)
            return False

    # ------------------------------------------------------------------ 연도 거버넌스 및 통계
    def get_year_statistics(self) -> Dict[str, Any]:
        """연도별 공고 집계 및 2026 연도 거버넌스 무결성 지표 산출."""
        default_stats = {
            "total_announcements": 0,
            "year_2026_count": 0,
            "past_years_count": 0,
            "future_years_count": 0,
            "compliance_rate_pct": 100.0,
            "by_year": {},
            "by_portal": {},
        }
        try:
            with self._connect() as conn:
                cur = conn.execute("SELECT target_year, COUNT(*) as cnt FROM announcements GROUP BY target_year")
                by_year = {int(r["target_year"]): int(r["cnt"]) for r in cur.fetchall() if r["target_year"] is not None}

                cur = conn.execute("SELECT source_portal, COUNT(*) as cnt FROM announcements GROUP BY source_portal")
                by_portal = {str(r["source_portal"]): int(r["cnt"]) for r in cur.fetchall()}

                total = sum(by_year.values())
                y2026 = by_year.get(2026, 0)
                past = sum(cnt for yr, cnt in by_year.items() if yr < 2026)
                future = sum(cnt for yr, cnt in by_year.items() if yr > 2026)
                compliance = (y2026 / total * 100.0) if total > 0 else 100.0

                return {
                    "total_announcements": total,
                    "year_2026_count": y2026,
                    "past_years_count": past,
                    "future_years_count": future,
                    "compliance_rate_pct": round(compliance, 1),
                    "by_year": by_year,
                    "by_portal": by_portal,
                }
        except Exception as e:
            logger.warning("get_year_statistics 실패: %s", e)
            return default_stats

    def list_announcements(
        self,
        query: str = "",
        portal: str = "",
        year_filter: str = "all",
        limit: int = 100,
    ) -> List[dict]:
        """
        공고 목록 다중 조건 조회 (검색어, 포털, 연도별 필터링 지원).
        year_filter 옵션:
        - 'all': 전체 공고
        - '2026': 2026년도 공고만 (target_year = 2026)
        - 'past': 2025년 이하 과거 공고 (target_year < 2026)
        - 'future': 2027년 이상 공고 (target_year > 2026)
        """
        try:
            with self._connect() as conn:
                sql = "SELECT * FROM announcements WHERE 1=1"
                params: list = []
                if query:
                    sql += " AND (title LIKE ? OR ministry LIKE ? OR organization LIKE ?)"
                    q_like = f"%{query}%"
                    params.extend([q_like, q_like, q_like])
                if portal:
                    sql += " AND source_portal = ?"
                    params.append(portal)
                if year_filter == "2026":
                    sql += " AND target_year = 2026"
                elif year_filter == "past":
                    sql += " AND target_year < 2026"
                elif year_filter == "future":
                    sql += " AND target_year > 2026"

                sql += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)

                cur = conn.execute(sql, params)
                return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            logger.warning("list_announcements 실패: %s", e)
            return []

    # ------------------------------------------------------------------ 멀티테넌트 및 Vault 자산 관리
    def get_tenant(self, tenant_id: str) -> Optional[dict]:
        """테넌트 단일 조회."""
        try:
            with self._connect() as conn:
                row = conn.execute("SELECT * FROM tenants WHERE id = ?", (tenant_id,)).fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.warning("get_tenant 실패: %s", e)
            return None

    def upsert_tenant(self, data: dict) -> bool:
        """테넌트 정보 등록 또는 수정."""
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO tenants (id, company_name, biz_reg_no, opened_date, rep_name, region, plan_tier, tenant_salt)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        company_name = excluded.company_name,
                        biz_reg_no = excluded.biz_reg_no,
                        opened_date = excluded.opened_date,
                        rep_name = excluded.rep_name,
                        region = excluded.region,
                        plan_tier = excluded.plan_tier,
                        tenant_salt = COALESCE(NULLIF(excluded.tenant_salt, ''), tenant_salt);
                    """,
                    (
                        data.get("id"),
                        data.get("company_name", "미등록 기업"),
                        data.get("biz_reg_no", ""),
                        data.get("opened_date", ""),
                        data.get("rep_name", ""),
                        data.get("region", "서울"),
                        data.get("plan_tier", "PRO"),
                        data.get("tenant_salt", ""),
                    ),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.warning("upsert_tenant 실패: %s", e)
            return False

    def list_tenants(self) -> List[dict]:
        """전체 테넌트 목록 조회."""
        try:
            with self._connect() as conn:
                cur = conn.execute("SELECT * FROM tenants ORDER BY created_at DESC")
                return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            logger.warning("list_tenants 실패: %s", e)
            return []

    def get_user(self, user_id: str) -> Optional[dict]:
        """사용자 단일 조회."""
        try:
            with self._connect() as conn:
                row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.warning("get_user 실패: %s", e)
            return None

    def get_user_by_email(self, email: str) -> Optional[dict]:
        """이메일 기반 사용자 조회."""
        try:
            with self._connect() as conn:
                row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.warning("get_user_by_email 실패: %s", e)
            return None

    def upsert_user(self, data: dict) -> bool:
        """사용자 계정 생성 또는 갱신."""
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO users (id, tenant_id, email, name, avatar_url, auth_provider, role)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        tenant_id = excluded.tenant_id,
                        email = excluded.email,
                        name = excluded.name,
                        avatar_url = excluded.avatar_url,
                        auth_provider = excluded.auth_provider,
                        role = excluded.role;
                    """,
                    (
                        data.get("id"),
                        data.get("tenant_id"),
                        data.get("email"),
                        data.get("name"),
                        data.get("avatar_url", ""),
                        data.get("auth_provider", "google"),
                        data.get("role", "OWNER"),
                    ),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.warning("upsert_user 실패: %s", e)
            return False

    def add_tenant_asset(self, asset: dict) -> bool:
        """테넌트 지식 자산고(Vault)에 파일 및 메타데이터 적재."""
        import json
        try:
            parsed_meta_str = asset.get("parsed_metadata")
            if isinstance(parsed_meta_str, dict):
                parsed_meta_str = json.dumps(parsed_meta_str, ensure_ascii=False)

            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO tenant_assets (id, tenant_id, asset_category, file_name, file_size, content_text, parsed_metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        asset_category = excluded.asset_category,
                        file_name = excluded.file_name,
                        file_size = excluded.file_size,
                        content_text = excluded.content_text,
                        parsed_metadata = excluded.parsed_metadata;
                    """,
                    (
                        asset.get("id"),
                        asset.get("tenant_id"),
                        asset.get("asset_category", "PROPOSAL"),
                        asset.get("file_name", "document.pdf"),
                        int(asset.get("file_size", 0)),
                        asset.get("content_text", ""),
                        parsed_meta_str or "{}",
                    ),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.warning("add_tenant_asset 실패: %s", e)
            return False

    def list_tenant_assets_raw(self, tenant_id: str, category: Optional[str] = None) -> List[dict]:
        """자산을 저장된 원문(raw) 형태로 조회. 암호 복호화는 보안/서비스 레이어에서 수행.
        (list_tenant_assets와 달리 parsed_metadata를 json.loads하지 않고 그대로 반환)"""
        try:
            with self._connect() as conn:
                sql = "SELECT * FROM tenant_assets WHERE tenant_id = ?"
                params = [tenant_id]
                if category and category != "ALL":
                    sql += " AND asset_category = ?"
                    params.append(category)
                sql += " ORDER BY created_at DESC"
                cur = conn.execute(sql, params)
                return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            logger.warning("list_tenant_assets_raw 실패: %s", e)
            return []

    def get_tenant_asset_raw(self, asset_id: str, tenant_id: str) -> Optional[dict]:
        """단일 자산의 저장된 원문(raw) 조회(parsed_metadata json 파싱 X)."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM tenant_assets WHERE id = ? AND tenant_id = ?",
                    (asset_id, tenant_id),
                ).fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.warning("get_tenant_asset_raw 실패: %s", e)
            return None

    def list_tenant_assets(self, tenant_id: str, category: Optional[str] = None) -> List[dict]:
        """테넌트의 자산 목록 조회 (카테고리 필터 옵션)."""
        import json
        try:
            with self._connect() as conn:
                sql = "SELECT * FROM tenant_assets WHERE tenant_id = ?"
                params = [tenant_id]
                if category and category != "ALL":
                    sql += " AND asset_category = ?"
                    params.append(category)
                sql += " ORDER BY created_at DESC"
                cur = conn.execute(sql, params)
                rows = []
                for r in cur.fetchall():
                    item = dict(r)
                    if item.get("parsed_metadata"):
                        try:
                            item["parsed_metadata"] = json.loads(item["parsed_metadata"])
                        except Exception:
                            item["parsed_metadata"] = {}
                    else:
                        item["parsed_metadata"] = {}
                    rows.append(item)
                return rows
        except Exception as e:
            logger.warning("list_tenant_assets 실패: %s", e)
            return []

    def get_tenant_asset(self, asset_id: str, tenant_id: str) -> Optional[dict]:
        """단일 자산 상세 조회 (테넌트 격리 보장)."""
        import json
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM tenant_assets WHERE id = ? AND tenant_id = ?",
                    (asset_id, tenant_id),
                ).fetchone()
                if not row:
                    return None
                item = dict(row)
                if item.get("parsed_metadata"):
                    try:
                        item["parsed_metadata"] = json.loads(item["parsed_metadata"])
                    except Exception:
                        item["parsed_metadata"] = {}
                return item
        except Exception as e:
            logger.warning("get_tenant_asset 실패: %s", e)
            return None

    def delete_tenant_asset(self, asset_id: str, tenant_id: str) -> bool:
        """자산 삭제 (테넌트 격리 보장)."""
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "DELETE FROM tenant_assets WHERE id = ? AND tenant_id = ?",
                    (asset_id, tenant_id),
                )
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            logger.warning("delete_tenant_asset 실패: %s", e)
            return False

    def create_grant_project(self, project: dict) -> str:
        """도전 과제 프로젝트 생성."""
        import uuid
        pid = project.get("id") or f"proj_{uuid.uuid4().hex[:12]}"
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO grant_projects (id, tenant_id, announcement_id, announcement_title, template_id, status, progress_pct)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        announcement_title = excluded.announcement_title,
                        template_id = excluded.template_id,
                        status = excluded.status,
                        progress_pct = excluded.progress_pct;
                    """,
                    (
                        pid,
                        project.get("tenant_id"),
                        project.get("announcement_id"),
                        project.get("announcement_title", "지원 과제"),
                        project.get("template_id", "PSST"),
                        project.get("status", "DRAFTING"),
                        int(project.get("progress_pct", 0)),
                    ),
                )
                conn.commit()
                return pid
        except Exception as e:
            logger.warning("create_grant_project 실패: %s", e)
            return pid

    def list_grant_projects(self, tenant_id: str) -> List[dict]:
        """테넌트의 도전 과제 프로젝트 목록 조회."""
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "SELECT * FROM grant_projects WHERE tenant_id = ? ORDER BY created_at DESC",
                    (tenant_id,),
                )
                return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            logger.warning("list_grant_projects 실패: %s", e)
            return []

    def get_grant_project(self, project_id: str, tenant_id: str) -> Optional[dict]:
        """단일 도전 과제 프로젝트 조회."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM grant_projects WHERE id = ? AND tenant_id = ?",
                    (project_id, tenant_id),
                ).fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.warning("get_grant_project 실패: %s", e)
            return None

    def update_grant_project(self, project_id: str, tenant_id: str, **fields: Any) -> bool:
        """도전 과제 프로젝트 상태/진행률/템플릿 수정 (REQ-029, 테넌트 격리).

        허용 컬럼만 반영하며 WHERE tenant_id 조건으로 타 테넌트 편집을 차단한다.
        fields가 없으면 실제 변경 없이 존재 여부만 반환 (no-op).
        """
        allowed = {"status", "progress_pct", "template_id", "announcement_title"}
        payload = {k: v for k, v in fields.items() if k in allowed}
        if "progress_pct" in payload:
            try:
                payload["progress_pct"] = max(0, min(100, int(payload["progress_pct"])))
            except (ValueError, TypeError):
                payload.pop("progress_pct")
        try:
            with self._connect() as conn:
                if not payload:
                    cur = conn.execute(
                        "SELECT 1 FROM grant_projects WHERE id = ? AND tenant_id = ?",
                        (project_id, tenant_id),
                    ).fetchone()
                    return cur is not None
                cols = ", ".join(f"{k} = ?" for k in payload)
                cur = conn.execute(
                    f"UPDATE grant_projects SET {cols} WHERE id = ? AND tenant_id = ?",
                    list(payload.values()) + [project_id, tenant_id],
                )
                return cur.rowcount > 0
        except Exception as e:
            logger.warning("update_grant_project 실패: %s", e)
            return False

    def delete_grant_project(self, project_id: str, tenant_id: str) -> bool:
        """도전 과제 프로젝트 삭제 (REQ-029, 테넌트 격리). 타 테넌트는 차단."""
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "DELETE FROM grant_projects WHERE id = ? AND tenant_id = ?",
                    (project_id, tenant_id),
                )
                return cur.rowcount > 0
        except Exception as e:
            logger.warning("delete_grant_project 실패: %s", e)
            return False

    # ------------------------------------------------------------------ REQ-047 프로토타입 검증 & 리워드 경제 (무료/유료 듀얼 트랙)
    def create_prototype_campaign(self, campaign: dict) -> bool:
        """신규 프로토타입 검증 캠페인 생성 (무료 품앗이 / 유료 보증 트랙 지원)."""
        payload = dict(campaign)
        payload.setdefault("request_type", "PAID")
        payload.setdefault("category", "일반")
        payload.setdefault("target_goal", "")
        payload.setdefault("payment_status", "COMPLETED" if payload.get("request_type") == "PAID" else "FREE")
        payload.setdefault("payment_id", "")
        payload.setdefault("is_featured", 1 if payload.get("request_type") == "PAID" else 0)
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO prototype_campaigns (
                        id, item_id, tenant_id, prototype_url, title, description,
                        target_testers, fee_per_test, tester_reward, platform_fee,
                        total_budget, completed_testers, status, created_at,
                        request_type, category, target_goal, payment_status, payment_id, is_featured
                    ) VALUES (
                        :id, :item_id, :tenant_id, :prototype_url, :title, :description,
                        :target_testers, :fee_per_test, :tester_reward, :platform_fee,
                        :total_budget, :completed_testers, :status, :created_at,
                        :request_type, :category, :target_goal, :payment_status, :payment_id, :is_featured
                    )
                    """,
                    payload,
                )
                return True
        except Exception as e:
            logger.warning("create_prototype_campaign 실패: %s", e)
            return False

    def get_prototype_campaign(self, campaign_id: str) -> Optional[dict]:
        """단일 프로토타입 검증 캠페인 조회."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM prototype_campaigns WHERE id = ?", (campaign_id,)
                ).fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.warning("get_prototype_campaign 실패: %s", e)
            return None

    def list_prototype_campaigns(
        self,
        status: Optional[str] = None,
        item_id: Optional[str] = None,
        request_type: Optional[str] = None,
        category: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[dict]:
        """프로토타입 검증 캠페인 목록 조회 (유형별/분야별 필터 및 limit 지원)."""
        try:
            with self._connect() as conn:
                query = "SELECT * FROM prototype_campaigns WHERE 1=1"
                params: list = []
                if status:
                    query += " AND status = ?"
                    params.append(status)
                if item_id:
                    query += " AND item_id = ?"
                    params.append(item_id)
                if request_type and request_type != "ALL":
                    query += " AND request_type = ?"
                    params.append(request_type)
                if category and category != "ALL":
                    query += " AND category = ?"
                    params.append(category)
                query += " ORDER BY is_featured DESC, created_at DESC"
                if limit and limit > 0:
                    query += f" LIMIT {int(limit)}"
                cur = conn.execute(query, params)
                return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            logger.warning("list_prototype_campaigns 실패: %s", e)
            return []

    def update_prototype_campaign(self, campaign_id: str, **fields: Any) -> bool:
        """캠페인 상태/참여자 수 갱신."""
        allowed = {"completed_testers", "status", "title", "description", "prototype_url"}
        payload = {k: v for k, v in fields.items() if k in allowed}
        if not payload:
            return False
        try:
            with self._connect() as conn:
                cols = ", ".join(f"{k} = ?" for k in payload)
                cur = conn.execute(
                    f"UPDATE prototype_campaigns SET {cols} WHERE id = ?",
                    list(payload.values()) + [campaign_id],
                )
                return cur.rowcount > 0
        except Exception as e:
            logger.warning("update_prototype_campaign 실패: %s", e)
            return False

    def start_prototype_session(self, session: dict) -> bool:
        """테스터 실사용 세션 시작."""
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO prototype_sessions (
                        id, campaign_id, tester_id, active_seconds, visible_seconds,
                        status, started_at, completed_at
                    ) VALUES (
                        :id, :campaign_id, :tester_id, :active_seconds, :visible_seconds,
                        :status, :started_at, :completed_at
                    )
                    """,
                    session,
                )
                return True
        except Exception as e:
            logger.warning("start_prototype_session 실패: %s", e)
            return False

    def get_prototype_session(self, session_id: str) -> Optional[dict]:
        """프로토타입 세션 조회."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM prototype_sessions WHERE id = ?", (session_id,)
                ).fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.warning("get_prototype_session 실패: %s", e)
            return None

    def update_prototype_session(
        self, session_id: str, active_seconds: int, visible_seconds: int, status: str
    ) -> bool:
        """세션 하트비트 누적 및 상태 갱신."""
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    """
                    UPDATE prototype_sessions
                    SET active_seconds = ?, visible_seconds = ?, status = ?
                    WHERE id = ?
                    """,
                    (active_seconds, visible_seconds, status, session_id),
                )
                return cur.rowcount > 0
        except Exception as e:
            logger.warning("update_prototype_session 실패: %s", e)
            return False

    def save_prototype_feedback(self, feedback: dict) -> bool:
        """피드백 저장 및 리워드 지급 상태 기록."""
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO prototype_feedbacks (
                        id, campaign_id, session_id, tester_id, tester_alias,
                        dwell_seconds, ux_score, functionality_score, willingness_to_pay,
                        nps_recommend_score, blocker_category, qualitative_feedback,
                        reward_amount, reward_status, created_at
                    ) VALUES (
                        :id, :campaign_id, :session_id, :tester_id, :tester_alias,
                        :dwell_seconds, :ux_score, :functionality_score, :willingness_to_pay,
                        :nps_recommend_score, :blocker_category, :qualitative_feedback,
                        :reward_amount, :reward_status, :created_at
                    )
                    """,
                    feedback,
                )
                # 세션 상태도 COMPLETED로 갱신
                conn.execute(
                    "UPDATE prototype_sessions SET status = 'COMPLETED', completed_at = ? WHERE id = ?",
                    (feedback["created_at"], feedback["session_id"]),
                )
                # 캠페인 completed_testers 증가 및 목표 달성 시 COMPLETED 전환
                conn.execute(
                    """
                    UPDATE prototype_campaigns
                    SET completed_testers = completed_testers + 1,
                        status = CASE WHEN completed_testers + 1 >= target_testers THEN 'COMPLETED' ELSE status END
                    WHERE id = ?
                    """,
                    (feedback["campaign_id"],),
                )
                return True
        except Exception as e:
            logger.warning("save_prototype_feedback 실패: %s", e)
            return False

    def list_prototype_feedbacks(self, campaign_id: str) -> List[dict]:
        """캠페인에 등록된 피드백 목록 조회."""
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "SELECT * FROM prototype_feedbacks WHERE campaign_id = ? ORDER BY created_at DESC",
                    (campaign_id,),
                )
                return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            logger.warning("list_prototype_feedbacks 실패: %s", e)
            return []

    def has_prototype_feedback(self, campaign_id: str, tester_id: str) -> bool:
        """특정 테스터가 해당 캠페인에 이미 피드백을 완료했는지 확인 (중복 참여 원천 방지)."""
        if not tester_id:
            return False
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "SELECT COUNT(*) FROM prototype_feedbacks WHERE campaign_id = ? AND tester_id = ?",
                    (campaign_id, tester_id),
                )
                row = cur.fetchone()
                return bool(row and row[0] > 0)
        except Exception as e:
            logger.warning("has_prototype_feedback 실패: %s", e)
            return False

    def get_tester_rewards_summary(self, tester_id: str) -> dict:
        """특정 테스터의 누적 리워드 요약."""
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    """
                    SELECT COUNT(*) as completed_count, COALESCE(SUM(reward_amount), 0) as total_reward
                    FROM prototype_feedbacks
                    WHERE tester_id = ? AND reward_status = 'PAID'
                    """,
                    (tester_id,),
                )
                row = cur.fetchone()
                if row:
                    return {
                        "completed_count": row["completed_count"],
                        "total_reward": row["total_reward"],
                    }
                return {"completed_count": 0, "total_reward": 0}
        except Exception as e:
            logger.warning("get_tester_rewards_summary 실패: %s", e)
            return {"completed_count": 0, "total_reward": 0}



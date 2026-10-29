"""
정부지원사업 맞춤형 AI 코파일럿 · 공통 디자인 시스템 및 권한 분리 SSOT 모듈
(src/web/design_system.py)
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional
from fastapi import Request

STITCH_PROJECT_METADATA: Dict[str, Any] = {
    "project_id": "6532140447067945829",
    "project_title": "정부지원사업 맞춤형 AI 코파일럿",
    "design_system_asset": "assets/60b7c8e07043493594e9d93dcab37860",
    "screens": {
        "intro_main": {
            "screen_id": "bfd97889d5ba4a04831147143b460db8",
            "title": "초기 방문자 스토리 인트로",
            "image_url": "/static/intro/stitch_k_horizon_2027_intro_screen.png",
        },
        "subscriber_workspace": {
            "screen_id": "1ced2be73d7b47fd9c3adf14ebfa4c12",
            "title": "유료 사업자 맞춤 워크스페이스",
            "image_url": "/static/intro/stitch_k_horizon_2027_workspace_screen.png",
        },
        "governance_partner": {
            "screen_id": "7aa617b3c7a94fbfa4c07e4c491bd06f",
            "title": "거버넌스 공공/파트너 대시보드",
            "image_url": "/static/intro/stitch_governance_partner_dashboard.png",
        },
    },
}

DESIGN_COUNCIL_5EXPERTS: List[Dict[str, str]] = [
    {"name": "김도윤", "role": "디자인 시스템 리드", "pillar": "공통 CSS 및 컴포넌트 표준화"},
    {"name": "이서연", "role": "사용자 경험 디렉터", "pillar": "초기 방문자 / 유료 사업자 / 관리자 권한 분리"},
    {"name": "박현우", "role": "한글 조판 마스터", "pillar": "한글 가독성 및 수치 정렬 최적화"},
    {"name": "최유진", "role": "화면 설계 전문가", "pillar": "반응형 그리드 및 시각적 대비 구현"},
    {"name": "정민석", "role": "스토리텔링 총괄", "pillar": "5막 성장 스토리 및 파트너 생태계 설계"},
]

K_HORIZON_2027_TOKENS: Dict[str, Any] = {
    "name": "정부지원사업 맞춤형 코파일럿 디자인 시스템",
    "version": "2027.1",
    "colors": {
        "primary": "#256EF4",
        "cyan": "#06B6D4",
        "emerald": "#10B981",
        "gold": "#F59E0B",
    },
}

ROLE_PORTALS: Dict[str, Dict[str, Any]] = {
    "visitor": {
        "key": "visitor",
        "label": "초기 방문자",
        "short_label": "방문자",
        "badge": "초기 방문자 포털",
        "icon": "fa-compass",
        "accent_class": "kh-role-visitor",
        "accent_hex": "#06B6D4",
        "home_url": "/intro",
        "subtitle": "지원사업 맞춤 추천과 성장 스토리를 확인하는 초기 방문자 서비스",
        "cta_label": "1분 과제 진단",
        "cta_href": "/vault?role=subscriber",
        "nav_items": [
            {"href": "/intro", "label": "서비스 소개", "icon": "fa-sparkles", "page": "intro"},
            {"href": "/feedback-lounge", "label": "피드백 라운지", "icon": "fa-comments", "page": "feedback_lounge"},
            {"href": "/intro#story-5acts", "label": "성장 스토리", "icon": "fa-film", "page": "story"},
            {"href": "/intro#growth-partners", "label": "전문 파트너", "icon": "fa-handshake", "page": "partners"},
            {"href": "/pricing", "label": "요금제 안내", "icon": "fa-gem", "page": "pricing"},
        ],
    },
    "subscriber": {
        "key": "subscriber",
        "label": "유료 사업자",
        "short_label": "사업자",
        "badge": "유료 사업자 전용 워크스페이스",
        "icon": "fa-briefcase",
        "accent_class": "kh-role-subscriber",
        "accent_hex": "#10B981",
        "home_url": "/dashboard/biz",
        "subtitle": "맞춤 대시보드와 공고 요건 정밀 분석 공간",
        "cta_label": "맞춤 공고 탐색",
        "cta_href": "/announcements",
        "nav_items": [
            {"href": "/dashboard/biz", "label": "대시보드", "icon": "fa-chart-pie", "page": "dashboard_biz"},
            {"href": "/items", "label": "사업 아이템", "icon": "fa-id-card", "page": "items"},
            {"href": "/feedback-lounge", "label": "피드백 라운지", "icon": "fa-comments", "page": "feedback_lounge"},
            {"href": "/vault", "label": "기업 금고", "icon": "fa-vault", "page": "vault"},
            {"href": "/announcements", "label": "맞춤 공고", "icon": "fa-bullhorn", "page": "announcements"},
            {"href": "/proposals/tailor", "label": "요건 분석", "icon": "fa-clipboard-check", "page": "tailor"},
            {"href": "/projects", "label": "도전 과제", "icon": "fa-bullseye", "page": "projects"},
        ],
    },
    "admin": {
        "key": "admin",
        "label": "플랫폼 관리자",
        "short_label": "관리자",
        "badge": "관리자 통합 관제",
        "icon": "fa-shield-halved",
        "accent_class": "kh-role-admin",
        "accent_hex": "#F59E0B",
        "home_url": "/admin/platform",
        "subtitle": "플랫폼 현황 및 감사로그 모니터링",
        "cta_label": "운영 관제",
        "cta_href": "/admin/platform",
        "nav_items": [
            {"href": "/admin/platform", "label": "총괄 플랫폼", "icon": "fa-sliders", "page": "admin_platform"},
            {"href": "/governance/partner", "label": "거버넌스", "icon": "fa-building-columns", "page": "governance_partner"},
            {"href": "/portals", "label": "포털 연동", "icon": "fa-globe", "page": "portals"},
            {"href": "/audit", "label": "전주기 감사", "icon": "fa-shield-halved", "page": "audit"},
            {"href": "/admin/audit-logs", "label": "감사 추적", "icon": "fa-link", "page": "admin_audit_logs"},
            {"href": "/logs", "label": "시스템 로그", "icon": "fa-terminal", "page": "logs"},
        ],
    },
}

STORY_5ACTS: List[Dict[str, str]] = [
    {
        "act_no": "제1막",
        "badge": "야근의 한숨",
        "title": "끝없는 공고 검색의 피로",
        "img": "/static/media/intro/story_act1_exhaustion.jpg",
        "alt": "야근의 한숨",
        "quote": '"오늘도 공고만 찾다 하루가 다 갔네... 기관마다 다른 서식은 언제 다 채우지?"',
        "accent": "crimson",
    },
    {
        "act_no": "제2막",
        "badge": "아침 맞춤 알림",
        "title": "기업 맞춤 적격 과제 브리핑",
        "img": "/static/media/intro/story_act2_morning_alert.jpg",
        "alt": "아침 맞춤 알림",
        "quote": "출근길 도착한 적합 공고 알림 — 우리 기업 조건에 꼭 맞는 사업만 골라줍니다.",
        "accent": "cyan",
    },
    {
        "act_no": "제3막",
        "badge": "요건 정밀 분석",
        "title": "공고 요건 및 가점 정밀 분석",
        "img": "/static/media/intro/story_act3_warm_guide.jpg",
        "alt": "요건 정밀 분석 가이드",
        "quote": "등록된 기업 정보를 바탕으로 심사위원이 요구하는 핵심 자격요건과 가점 항목을 정밀 분석합니다.",
        "accent": "violet",
    },
    {
        "act_no": "제4막",
        "badge": "체계적 적시 지원",
        "title": "철저한 준비로 완성하는 지원",
        "img": "/static/media/intro/story_act4_winning_joy.jpg",
        "alt": "과제 지원 완료",
        "quote": "맞춤 공고 알림과 서식 가이드로 최적의 과제를 찾아 적시에 빈틈없이 지원하고, 기업 데이터는 안전하게 보호됩니다.",
        "accent": "emerald",
    },
    {
        "act_no": "제5막",
        "badge": "성장의 길잡이",
        "title": "5대 전문 파트너 생태계",
        "img": "/static/media/intro/story_act5_growth_network_fortune.jpg",
        "alt": "전문 파트너 연계",
        "quote": "회계·마케팅·광고·투자·법률 파트너 연결까지 — 대표님은 본연의 사업과 인맥에만 집중하세요.",
        "accent": "gold",
    },
]

GROWTH_ROADMAP_3STEPS: List[Dict[str, str]] = [
    {
        "step": "1단계: 예비·초기 창업",
        "target": "창업 3년 미만 · 초기 자금",
        "prep": "벤처기업 확인서 · 전담 연구개발 인력 · 표준 사업계획서 체계화",
        "grant_scale": "최대 1억 ~ 3억 원",
    },
    {
        "step": "2단계: 도약 및 기술개발",
        "target": "창업 3~7년 · 성장 가속",
        "prep": "핵심 특허 포트폴리오 · 기술개발 정량지표 · 고용 및 매출 증빙 연동",
        "grant_scale": "최대 5억 ~ 15억 원",
    },
    {
        "step": "3단계: 글로벌 진출 및 확장",
        "target": "글로벌 진출 및 고성장",
        "prep": "수출 바우처 · 글로벌 인증 · 후속 투자 및 판로 연계",
        "grant_scale": "최대 20억 원 이상",
    },
]

PARTNER_5ECOSYSTEM: List[Dict[str, str]] = [
    {"name": "회계·세무", "icon": "fa-calculator", "desc": "정부과제 연구비 정산 · 세액공제 자문 · 재무 건전성"},
    {"name": "마케팅·브랜딩", "icon": "fa-bullhorn", "desc": "시장 검증 · 고객 발굴 · 브랜드 스토리텔링"},
    {"name": "온라인 광고", "icon": "fa-chart-line", "desc": "바우처 연계 광고 효율화 · 성장 캠페인"},
    {"name": "벤처투자사", "icon": "fa-hand-holding-dollar", "desc": "전문 투자사 매칭 · 사업설명회 고도화 · 후속 투자"},
    {"name": "특허·법률", "icon": "fa-scale-balanced", "desc": "핵심 특허 출원 · 기술 분석 · 계약 법률 자문"},
]

BM_5TRACKS: List[Dict[str, str]] = [
    {
        "key": "ict_deeptech",
        "label": "정보통신·딥테크",
        "icon": "fa-microchip",
        "badge": "기술개발 특화",
        "guide": "정보통신·딥테크: 기술창업 우대 가점 및 핵심 기술성 중심 요건 분석 모드",
    },
    {
        "key": "smart_mfg",
        "label": "제조·공정혁신",
        "icon": "fa-industry",
        "badge": "설비·자동화",
        "guide": "제조·공정혁신: 공정 자동화·고도화 및 설비투자 매칭 최적화 모드",
    },
    {
        "key": "youth_women",
        "label": "청년·여성창업",
        "icon": "fa-rocket",
        "badge": "창업패키지",
        "guide": "청년·여성창업: 초기창업패키지 가점 트랙 및 차별화 스토리텔링 모드",
    },
    {
        "key": "local_creator",
        "label": "지역·소상공인",
        "icon": "fa-store",
        "badge": "판로개척",
        "guide": "지역·소상공인: 지역특화 브랜드 창출 및 신규 판로개척 지원금 모드",
    },
    {
        "key": "social_esg",
        "label": "친환경·사회혁신",
        "icon": "fa-leaf",
        "badge": "지속가능경영",
        "guide": "친환경·사회혁신: 환경 개선 및 사회적 가치 지표 중심 모드",
    },
]

PRICING_4TIERS: List[Dict[str, Any]] = [
    {
        "key": "free",
        "name": "무료 체험",
        "price_id": "price-free",
        "monthly_label": "0원 / 월",
        "annual_label": "0원 / 월",
        "credits_label": "사업 아이템 1개 · 맞춤 공고 매칭 · 25대 결격사유 1초 사전 검증",
        "badge": "기본 체험",
        "cta": "무료로 시작하기",
        "featured": False,
    },
    {
        "key": "growth",
        "name": "성장형",
        "price_id": "price-growth",
        "monthly_label": "39,000원 / 월",
        "annual_label": "31,200원 / 월 (20% 할인)",
        "credits_label": "사업 아이템 3개 · 공고 요건 심사 대응 가이드 · 카카오/메일 실시간 알림 · 프로토타입 검증 캠페인",
        "badge": "가장 인기",
        "cta": "상담 및 시작",
        "featured": True,
    },
    {
        "key": "scaleup",
        "name": "도약형",
        "price_id": "price-scaleup",
        "monthly_label": "120,000원 / 월",
        "annual_label": "96,000원 / 월 (20% 할인)",
        "credits_label": "사업 아이템 10개 · 다부처 과제 동시 트래킹 · 5대 전문 파트너 자문 · 심사위원 공인 보고서 무제한",
        "badge": "과제 집중",
        "cta": "상담 및 시작",
        "featured": False,
    },
    {
        "key": "agency",
        "name": "전문가형",
        "price_id": "price-agency",
        "monthly_label": "300,000원 / 월",
        "annual_label": "240,000원 / 월 (20% 할인)",
        "credits_label": "보육기업 다중 포트폴리오 관리 · 5대 전문 파트너 전담 배정 · 맞춤형 과제 기획 전략 자문",
        "badge": "거버넌스·컨설팅",
        "cta": "전문가 상담",
        "featured": False,
    },
]

_PAGE_TO_DEFAULT_ROLE: Dict[str, str] = {
    "intro": "visitor",
    "pricing": "visitor",
    "dashboard_biz": "subscriber",
    "vault": "subscriber",
    "projects": "subscriber",
    "tailor": "subscriber",
    "announcements": "subscriber",
    "matches": "subscriber",
    "admin_platform": "admin",
    "governance_partner": "admin",
    "admin_audit_logs": "admin",
    "dashboard": "admin",
    "items": "subscriber",
    "portals": "admin",
    "audit": "admin",
    "logs": "admin",
}


def resolve_role(request: Optional[Request], active_page: str = "intro") -> str:
    """요청의 ?role= 파라미터, sshai_role 쿠키, 또는 페이지 기본값으로 권한 판별."""
    if request is not None:
        q_role = (request.query_params.get("role") or "").strip().lower()
        if q_role in ROLE_PORTALS:
            return q_role
        c_role = (request.cookies.get("sshai_role") or "").strip().lower()
        if c_role in ROLE_PORTALS:
            return c_role
    return _PAGE_TO_DEFAULT_ROLE.get(active_page, "visitor")


def get_design_context(request: Optional[Request], active_page: str = "intro") -> Dict[str, Any]:
    """모든 템플릿에 공통 주입되는 단일 진실 공급원 컨텍스트."""
    role_key = resolve_role(request, active_page=active_page)
    return {
        "current_role": role_key,
        "role_portal": ROLE_PORTALS[role_key],
        "all_portals": ROLE_PORTALS,
        "story_5acts": STORY_5ACTS,
        "growth_steps": GROWTH_ROADMAP_3STEPS,
        "partner_pillars": PARTNER_5ECOSYSTEM,
        "bm_5tracks": BM_5TRACKS,
        "pricing_4tiers": PRICING_4TIERS,
    }

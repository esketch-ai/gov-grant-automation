"""REQ-042 · 10대 다각도 전문가별 전수 검사 및 교차 검증 자동화 스위트.
(tests/test_multi_specialist_10rounds.py)

10대 라운드별 검증 항목:
- Round 1 (총괄기획): 기획 사양 및 REQ 스펙 정합성 (27개 REQ, 2026 거버넌스, 4-Tier, 5 BM, 5 파트너, 블러페이월)
- Round 2 (디자인): K-Horizon 2027 픽셀 퍼펙트 & 토큰 (15개 화면 .kh-page-hero, 정적 인라인 0건, 160px/350px)
- Round 3 (타이포): 한국어 가독성 및 명도비 (10~11px 초소형 폰트 0건, 12.5px/13.5px 스케일)
- Round 4 (페르소나1): 초기 방문자(Visitor) E2E 저니 (/intro, /pricing, 쇼릴, 5막 스토리, 3대 탭, CTA 유입)
- Round 5 (페르소나2): 유료 사업자(Subscriber) E2E 저니 (6개 화면 200 OK, 워크스페이스, 데이터룸, 코파일럿)
- Round 6 (페르소나3): 플랫폼 관리자(Admin) E2E 저니 (8개 화면 200 OK, 콘솔, 파트너 배정, 감사로그)
- Round 7 (백엔드): FastAPI 라우트(76개+) & OpenAPI 스키마 (중복 ID 경고 0건, 결측 파라미터 500 크래시 방어)
- Round 8 (DB/보안): SQLite 영속성 & AES-256-GCM 보안 (HKDF-SHA256, Zero-Retention, 보안 응답 헤더 5종)
- Round 9 (BM/수집): 연도 필터링(2025 이하 100% 차단) & 포털 서킷 브레이커 상태 전이
- Round 10 (QA/회귀): QA Swarm 7대 에이전트 무결성(100점 만점), 복원 DOM ID(simNote/simChecks/verify-result)
"""
from __future__ import annotations

import glob
import os
import re
import time
import warnings
from pathlib import Path
from typing import Dict, List

import pytest
from fastapi.testclient import TestClient
from cryptography.exceptions import InvalidTag

from src.common.db import GrantDatabase
from src.common.resilience import CircuitBreaker, CircuitState
from src.collector.year_filter import YearFilter
from src.common.schemas import RawNotice
from src.security.encryption import AESENC_SENTINEL, VaultCryptoManager
from src.web.app import app
from src.web.design_system import (
    BM_5TRACKS,
    PARTNER_5ECOSYSTEM,
    PRICING_4TIERS,
    ROLE_PORTALS,
    STORY_5ACTS,
    GROWTH_ROADMAP_3STEPS,
)


@pytest.fixture
def client():
    return TestClient(app)


# =====================================================================
# [검사 1] 총괄기획팀 (PM/CPO): 기획 사양 및 REQ 스펙 정합성 전수 검사
# =====================================================================
def test_round1_product_strategy_and_req_spec_alignment(client):
    """REQ-042 Round 1: 27개 REQ 완료 정합성, 2026 거버넌스, 4-Tier, 5 BM, 5 파트너 토큰 검증."""
    # 1. REGISTRY.md 내 완료된 REQ 검증 (최소 27개 완료)
    registry_path = Path("SYNC/requests/REGISTRY.md")
    assert registry_path.exists(), "REGISTRY.md 파일이 존재해야 합니다."
    reg_text = registry_path.read_text(encoding="utf-8")
    done_count = len(re.findall(r"\|\s*✅\s*\*\*DONE\*\*", reg_text))
    assert done_count >= 27, f"완료된 REQ 개수가 최소 27개 이상이어야 합니다. (현재: {done_count})"

    # 2. 2026 단일 연도 거버넌스 확인
    res_status = client.get("/api/status")
    assert res_status.status_code == 200
    assert res_status.json().get("year_policy") == "2026_strict"

    # 3. 4-Tier 요금제 규격 검증 (무료, 성장, 도약, 전문가형 및 20% 연간 할인)
    assert len(PRICING_4TIERS) == 4
    tier_keys = [t["key"] for t in PRICING_4TIERS]
    assert tier_keys == ["free", "growth", "scaleup", "agency"]
    # 성장형 연간 할인 20% 확인 (39,000 -> 31,200)
    growth_tier = next(t for t in PRICING_4TIERS if t["key"] == "growth")
    assert "39,000" in growth_tier["monthly_label"]
    assert "31,200" in growth_tier["annual_label"]
    assert "20% 할인" in growth_tier["annual_label"]

    # 4. 5대 BM 맞춤 트랙 검증
    assert len(BM_5TRACKS) == 5
    bm_keys = [b["key"] for b in BM_5TRACKS]
    assert "ict_deeptech" in bm_keys
    assert "smart_mfg" in bm_keys
    assert "youth_women" in bm_keys
    assert "local_creator" in bm_keys
    assert "social_esg" in bm_keys

    # 5. 5대 전문 파트너 생태계 검증
    assert len(PARTNER_5ECOSYSTEM) == 5
    partner_names = [p["name"] for p in PARTNER_5ECOSYSTEM]
    assert "회계·세무" in partner_names
    assert "마케팅·브랜딩" in partner_names
    assert "온라인 광고" in partner_names
    assert "벤처투자사" in partner_names
    assert "특허·법률" in partner_names

    # 6. 블러 페이월 및 Zero-Retention 무보관 원칙 토큰 검증
    res_intro = client.get("/intro")
    assert res_intro.status_code == 200
    assert "paywall-preview" in res_intro.text
    assert "미리보기 및 유료 잠금" in res_intro.text
    assert "blur-sm" in res_intro.text


# =====================================================================
# [검사 2] 디자인팀 (UI Lead): K-Horizon 2027 픽셀 퍼펙트 & 토큰 전수 검사
# =====================================================================
def test_round2_visual_design_pixel_perfect_and_tokens(client):
    """REQ-042/REQ-047 Round 2: 전체 웹 화면 .kh-page-hero 100% 탑재, 정적 인라인 0건, 160px/350px CSS 검증."""
    template_files = sorted(glob.glob("src/web/templates/*.html"))
    # base.html 제외한 순수 페이지 템플릿 (기존 15개 + REQ-047 prototype_report.html 1개)
    page_templates = [f for f in template_files if not f.endswith("base.html")]
    assert len(page_templates) in (15, 16), f"15~16개의 페이지 템플릿이 존재해야 합니다. (현재: {len(page_templates)})"

    # 1. 15개 전체 페이지에 .kh-page-hero 탑재 확인
    for t_path in page_templates:
        content = Path(t_path).read_text(encoding="utf-8")
        assert "kh-page-hero" in content, f"{t_path}에 .kh-page-hero 배너가 누락되었습니다."

    # 2. 정적 인라인 스타일 style="..." 0건 검증 (동적 progress bar style="width: ...%" 제외)
    for t_path in template_files:
        content = Path(t_path).read_text(encoding="utf-8")
        # style="..." 속성 추출
        style_matches = re.findall(r'style="([^"]*)"', content)
        for s in style_matches:
            # 동적 게이지 너비 (width: {{...}}) 및 동적 렌더링을 위한 style만 허용
            is_dynamic_width = bool(re.search(r'width:\s*\{\{[^}]+\}\}%?', s))
            is_display_toggle = s.strip() in ("display: none;", "display:none")
            assert is_dynamic_width or is_display_toggle, (
                f"{t_path} 내 비인가 정적 인라인 스타일 발견: style=\"{s}\""
            )

    # 3. k_horizon_2027.css 토큰 검증 (160px 브랜드, 350px 제어박스, 84px 스크롤 오프셋)
    css_content = Path("src/web/static/css/k_horizon_2027.css").read_text(encoding="utf-8")
    assert ".kh-brand-box" in css_content
    assert "width: 160px;" in css_content
    assert ".kh-control-box" in css_content
    assert "width: 350px;" in css_content
    assert ".kh-scroll-target" in css_content
    assert "scroll-margin-top: 84px;" in css_content
    assert "scroll-padding-top: 84px;" in css_content


# =====================================================================
# [검사 3] 디자인 & 접근성: 한국어 가독성 및 명도비 전수 검사
# =====================================================================
def test_round3_korean_typography_readability_scale(client):
    """REQ-042 Round 3: 10~11px 초소형 폰트 0건, 정부배너 12.5px, GNB 13.5px 가독성 스케일 검증."""
    template_files = glob.glob("src/web/templates/*.html")
    # 1. 16개 전체 웹 템플릿 내 text-[10px], text-[11px] 초소형 폰트 0건 전수 검증
    for t_path in template_files:
        content = Path(t_path).read_text(encoding="utf-8")
        matches = re.findall(r'text-\[(10|11)px\]', content)
        assert len(matches) == 0, f"{t_path} 내 초소형 폰트 잔존: {matches}"

    # 2. k_horizon_2027.css 내 가독성 폰트 스케일 토큰 확인
    css_content = Path("src/web/static/css/k_horizon_2027.css").read_text(encoding="utf-8")
    # 정부 스트립: 12.5px
    assert "font-size: 12.5px;" in css_content
    # GNB 메뉴 링크: 13.5px
    assert "font-size: 13.5px;" in css_content
    # 역할 뱃지: 12px
    assert "font-size: 12px;" in css_content


# =====================================================================
# [검사 4] UIUX팀 (Persona 1): 초기 방문자(Visitor) E2E 저니 시뮬레이션
# =====================================================================
def test_round4_visitor_persona_e2e_journey(client):
    """REQ-042 Round 4: 방문자 /intro, /pricing, 쇼릴, 5막 스토리, 3대 탭, CTA 유입 200 OK."""
    # 1. /intro 랜딩 페이지 호출
    res_intro = client.get("/intro", cookies={"sshai_role": "visitor"})
    assert res_intro.status_code == 200
    text = res_intro.text

    # 2. 60초 공감 쇼릴 비디오 태그 검증
    assert "<video" in text
    assert "intro_showreel.mp4" in text

    # 3. 5막 대서사 스토리보드 검증
    assert "story-5acts" in text
    assert "story_act1" in text
    assert "story_act5" in text

    # 4. 3단계 성장 로드맵 및 5대 전문 파트너 검증
    assert "growth-partners" in text
    assert "회계·세무" in text
    assert "특허·법률" in text

    # 5. 3대 서브 탭 검증
    assert "sample-overview" in text
    assert "paywall-preview" in text
    assert "pricing-plan" in text

    # 6. 1분 과제 진단 CTA 클릭 시 /vault?role=subscriber 유입 링크 검증
    assert "/vault?role=subscriber" in text

    # 7. /pricing 요금 안내 페이지 호출
    res_pricing = client.get("/pricing", cookies={"sshai_role": "visitor"})
    assert res_pricing.status_code == 200

    # 8. REQ-046: 사업계획서 대필 허위광고 퇴출 및 공고 요건 분석 본질 환원 검증
    assert "15분 계획서 초안 작성" not in text
    assert "25대 결격사유 1초 사전 검증" in text
    assert "공고마다 사업계획서를 새로 작성하는 번거로움" not in text
    assert "수많은 정부 공고 중 내 기업에 맞는 지원사업을 일일이 탐색하는 피로" in text


# =====================================================================
# [검사 5] UIUX팀 (Persona 2): 유료 사업자(Subscriber) E2E 저니 시뮬레이션
# =====================================================================
def test_round5_subscriber_persona_e2e_journey(client):
    """REQ-042/044 Round 5: 사업자 화면 200 OK, 역할 분리 및 수주 지표 검증."""
    sub_cookies = {"sshai_role": "subscriber"}
    screens = [
        ("/dashboard/biz", "사업자 맞춤 수주 워크스페이스"),
        ("/items", "사업 아이템 프로파일 관리"),
        ("/vault", "Company Vault"),
        ("/projects", "도전 과제"),
        ("/proposals/tailor", "DocuMorph AI"),
        ("/announcements", "공고 아카이브"),
        ("/matches", "알림 발송 이력"),
    ]

    for path, token in screens:
        res = client.get(path, cookies=sub_cookies)
        assert res.status_code == 200, f"{path} 호출 실패: {res.status_code}"
        assert token in res.text, f"{path} 화면에 필수 토큰 '{token}'이(가) 누락되었습니다."
        # 구독자 권한 뱃지 확인
        assert "유료 사업자" in res.text or "사업자 전용" in res.text

    # REQ-044: 사업자 대시보드 내 플랫폼 운영사 매출 통계 0건 영구 삭제 검증
    res_biz = client.get("/dashboard/biz", cookies=sub_cookies)
    assert "월간 구독 수익" not in res_biz.text
    assert "연간 구독 수익" not in res_biz.text
    assert "순수익" not in res_biz.text
    # 4대 수주 지표 확인
    assert "매칭 적합 공고" in res_biz.text
    assert "도전 중인 과제" in res_biz.text
    assert "수주 가능 지원금" in res_biz.text
    assert "기업 금고 완성도" in res_biz.text

    # REQ-046: 사업자 화면 내 '새 계획서 작성' 퇴출 및 '맞춤 공고 탐색' / '요건 분석' 검증
    assert "새 계획서 작성" not in res_biz.text
    assert "맞춤 공고 탐색" in res_biz.text
    assert "공고 요건 정밀 분석 및 자격 진단" in res_biz.text
    assert "사전 자격 진단 완료" in res_biz.text
    assert "요건 분석 확인" in res_biz.text


# =====================================================================
# [검사 6] UIUX팀 (Persona 3): 플랫폼 관리자(Admin) E2E 저니 시뮬레이션
# =====================================================================
def test_round6_admin_persona_e2e_journey(client):
    """REQ-042/044 Round 6: 관리자 화면 200 OK 및 순수 관제 메뉴 바인딩 검증."""
    admin_cookies = {"sshai_role": "admin"}
    screens = [
        ("/admin/platform", "플랫폼 관리자 통합 관제"),
        ("/governance/partner", "전문 파트너"),
        ("/dashboard", "2026년도 정부 R&D/조달 자동 매칭 대시보드"),
        ("/audit", "다각도 시스템 무결성 종합 감사 현황"),
        ("/admin/audit-logs", "감사로그 무결성 검증 콘솔"),
        ("/portals", "포털 연동 및 지자체 지원센터 관리"),
        ("/logs", "실시간 시스템 실행 로그"),
    ]

    for path, token in screens:
        res = client.get(path, cookies=admin_cookies)
        assert res.status_code == 200, f"{path} 호출 실패: {res.status_code}"
        assert token in res.text, f"{path} 화면에 필수 토큰 '{token}'이(가) 누락되었습니다."
        # 관리자 권한 뱃지 확인
        assert "플랫폼 관리자" in res.text


# =====================================================================
# [검사 7] 백엔드팀 (Backend Lead): FastAPI 라우트 & OpenAPI 스키마 전수 검사
# =====================================================================
def test_round7_fastapi_backend_routes_and_openapi(client):
    """REQ-042 Round 7: 76개+ 라우트, OpenAPI 중복 Operation ID 경고 0건, 결측 파라미터 방어."""
    # 1. 76개 이상 라우트 확인
    assert len(app.routes) >= 76, f"등록된 라우트 수가 부족합니다: {len(app.routes)}"

    # 2. OpenAPI 스키마 생성 시 Duplicate Operation ID UserWarning 0건 검증
    with warnings.catch_warnings(record=True) as recorded_warnings:
        warnings.simplefilter("always")
        schema = app.openapi()
        dup_warnings = [
            w for w in recorded_warnings
            if issubclass(w.category, UserWarning) and "Duplicate Operation ID" in str(w.message)
        ]
        assert len(dup_warnings) == 0, f"OpenAPI Duplicate Operation ID 발생: {dup_warnings}"

    # 3. GET/POST 엔드포인트 결측 파라미터 방어 (500 에러 없이 정형 응답 반환)
    # HWPX export
    res_hwpx_get = client.get("/api/export/hwpx")
    assert res_hwpx_get.status_code == 200
    res_hwpx_post = client.post("/api/export/hwpx", json={})
    assert res_hwpx_post.status_code == 200

    # DOCX export
    res_docx_get = client.get("/api/export/docx")
    assert res_docx_get.status_code == 200
    res_docx_post = client.post("/api/export/docx", json={})
    assert res_docx_post.status_code == 200

    # Audit verify
    res_verify_get = client.get("/api/admin/audit/verify")
    assert res_verify_get.status_code == 200
    res_verify_post = client.post("/api/admin/audit/verify", json={})
    assert res_verify_post.status_code == 200

    # Billing checkout & topup with empty json
    res_chk = client.post("/api/billing/checkout", json={})
    assert res_chk.status_code == 200
    res_top = client.post("/api/billing/topup", json={})
    assert res_top.status_code == 200


# =====================================================================
# [검사 8] DB/보안팀 (DB & Security Lead): SQLite 영속성 & 암호화 보안 전수 검사
# =====================================================================
def test_round8_db_persistence_and_aes256_security(client):
    """REQ-042 Round 8: 테넌트 AES-256-GCM 암호화/복호화 센티넬, Zero-Retention, 보안 응답 헤더 5종."""
    # 1. AES-256-GCM 암복호화 및 센티넬 접두어 확인
    crypto = VaultCryptoManager()
    salt = crypto.generate_tenant_salt()
    plain = "비공개 특허 및 연구계획서 핵심 기술 데이터"
    cipher = crypto.encrypt_text(plain, tenant_id="tenant_001", tenant_salt=salt)

    assert cipher.startswith(AESENC_SENTINEL), "암호문은 AESENC:: 센티넬로 시작해야 합니다."
    assert plain not in cipher, "암호문에 원본 평문이 노출되어서는 안 됩니다."
    assert crypto.decrypt_text(cipher, tenant_id="tenant_001", tenant_salt=salt) == plain

    # 2. 타 테넌트 복호화 시도 시 InvalidTag 예외 격리 검증
    with pytest.raises(InvalidTag):
        crypto.decrypt_text(cipher, tenant_id="tenant_002", tenant_salt=crypto.generate_tenant_salt())

    # 3. HTTP 응답 보안 헤더 5종 검증
    res = client.get("/api/status")
    h = res.headers
    assert "max-age=31536000" in h.get("strict-transport-security", "")
    assert "includeSubDomains" in h.get("strict-transport-security", "")
    assert h.get("x-content-type-options") == "nosniff"
    assert h.get("x-frame-options") == "DENY"
    assert h.get("x-xss-protection") == "1; mode=block"
    assert h.get("referrer-policy") == "strict-origin-when-cross-origin"

    # 4. XSS 스크립트 태그 이스케이프 검증
    xss_payload = "<script>alert('pwned')</script>"
    res_xss = client.get(f"/announcements?q={xss_payload}")
    assert res_xss.status_code == 200
    assert xss_payload not in res_xss.text, "XSS 스크립트가 그대로 렌더링되어서는 안 됩니다."


# =====================================================================
# [검사 9] BM엔진 & 수집팀 (BM & Collector Lead): 연도 필터링 & 서킷 브레이커 전수 검사
# =====================================================================
def test_round9_year_filter_and_collector_resilience(client):
    """REQ-042 Round 9: 2026 연도 필터 과거 공고 100% 차단, 서킷 브레이커 상태 전이 검증."""
    # 1. 2026 전용 연도 필터 검증 (2025 공고 차단, 2026 공고 통과)
    yf = YearFilter(target_year=2026)
    notice_2025 = RawNotice("ntis", "2025년도 산학연 콜라보 R&D 지원사업", "org", "중기부", "2025-11-30", "url", "")
    notice_2026 = RawNotice("ntis", "2026년도 초격차 스타트업 육성사업 공고", "org", "중기부", "2026-03-31", "url", "")

    keep_2025, why_2025 = yf.keep(notice_2025)
    assert keep_2025 is False, "2025년 공고는 차단되어야 합니다."
    assert "older_cycle_dropped" in why_2025

    keep_2026, why_2026 = yf.keep(notice_2026)
    assert keep_2026 is True, "2026년 공고는 유지되어야 합니다."
    assert "kept" in why_2026

    # 2. 서킷 브레이커 상태 전이 검증 (CLOSED -> OPEN -> HALF_OPEN -> CLOSED)
    cb = CircuitBreaker("portal_circuit_test", failure_threshold=2, recovery_timeout=0.05)
    assert cb.state == CircuitState.CLOSED.value
    assert cb.can_execute() is True

    # 2회 연속 실패 기록
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN.value
    assert cb.can_execute() is False

    # 타임아웃 경과 후 HALF_OPEN 시험 모드 전이
    time.sleep(0.06)
    assert cb.state == CircuitState.HALF_OPEN.value

    # 복구 성공 시 다시 CLOSED 전이
    cb.record_success()
    assert cb.state == CircuitState.CLOSED.value
    assert cb.can_execute() is True


# =====================================================================
# [검사 10] QA/컴플라이언스팀 (QA Lead): QA Swarm 7대 에이전트 & 회귀 테스트 전수 검사
# =====================================================================
def test_round10_qa_swarm_and_regression_integrity(client):
    """REQ-042 Round 10: QA Swarm 140/140 만점 유지, 복원 DOM ID simNote, simChecks, verify-result 정합성 검증."""
    # 1. 시스템 헬스체크 및 QA Swarm 감사 스코어 확인
    res_stat = client.get("/api/status")
    assert res_stat.status_code == 200
    stat_data = res_stat.json()
    assert stat_data.get("status") == "healthy"
    qa_info = stat_data.get("qa_swarm", {})
    assert qa_info.get("total_score") == 100.0
    assert qa_info.get("all_passed") is True

    # 2. REQ-041에서 복원된 DOM ID 무결성 확인
    # announcements.html: simNote, simChecks
    res_ann = client.get("/announcements")
    assert res_ann.status_code == 200
    assert 'id="simNote"' in res_ann.text
    assert 'id="simChecks"' in res_ann.text
    assert 'id="simResult"' in res_ann.text

    # audit_logs.html: verify-result
    res_audit_logs = client.get("/admin/audit-logs")
    assert res_audit_logs.status_code == 200
    assert 'id="verify-result"' in res_audit_logs.text

    # 3. 원클릭 QA Swarm 감사 엔드포인트 100점 만점 검증
    res_audit = client.post("/api/audit/run")
    assert res_audit.status_code == 200
    audit_data = res_audit.json()
    assert audit_data.get("total_score") == 100.0
    assert audit_data.get("all_passed") is True
    assert "APPROVED" in audit_data.get("status", "")

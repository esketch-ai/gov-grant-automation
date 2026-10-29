"""
FastAPI 기반 웹 관리자 대시보드 서버 (src/web/app.py)

REQ-010 구현:
- 2026년도 공고 현황 및 KPI 대시보드
- SQLite DB(announcements, rfp_chunks, dispatch_history) 실시간 뷰어
- items/ 사업 아이템 프로파일 열람
- 파이프라인 수동 트리거 및 상태 API
- 보안 원칙(최은정 통제): 127.0.0.1 바인딩, 시크릿 마스킹, HTML XSS 방어
"""
from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import yaml
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, Request, Form, BackgroundTasks, Response, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates

from ..common.logging_config import get_logger
from ..common.schemas import resolve_env_refs, RawNotice
from ..common.db import GrantDatabase
from ..common.scheduler import AsyncScheduler
from ..common.deadline import calculate_dday, get_dday_statistics
from ..common.ical_exporter import export_single_notice_ics, export_bundle_calendar_ics
from ..common.item_profile_merger import merge_item_company_specs, COMPANY_SPECS_FIELDS
from ..common.constants import DEFAULT_NOTIFICATION_EMAIL, DEFAULT_MIN_MATCH_SCORE
from ..parser.proposal_parser import ProposalParser
from ..parser.proposal_extractor import ProposalExtractor
from ..matcher.preflight import PreflightService
from ..matcher.vault_preflight import VaultPreflightMatcher
from ..matcher.multi_axis_matcher import classify_notice_track, NoticeTrack

logger = get_logger("web_admin")

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(title="정부지원사업 맞춤형 관리 플랫폼", version="1.5.1")

# REQ-030: 보안 헤더 미들웨어 (최은정 통제)
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

from fastapi.staticfiles import StaticFiles
from .design_system import (
    get_design_context,
    resolve_role,
    ROLE_PORTALS,
    K_HORIZON_2027_TOKENS,
    STITCH_PROJECT_METADATA,
    DESIGN_COUNCIL_5EXPERTS,
)

STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

_raw_templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


class _KHorizonTemplates:
    """모든 TemplateResponse 호출에 K-Horizon 2027 디자인 토큰 및 3대 권한 분리 컨텍스트를 자동 주입."""

    def __getattr__(self, name):
        return getattr(_raw_templates, name)

    def TemplateResponse(self, *args, **kwargs):
        request = kwargs.get("request")
        context = kwargs.get("context")
        if context is None and len(args) >= 2 and isinstance(args[1], dict):
            context = args[1]
        if isinstance(context, dict):
            if request is None and isinstance(context.get("request"), Request):
                request = context.get("request")
            active_page = context.get("active_page", "intro")
            kh_ctx = get_design_context(request, active_page=active_page)
            for k, v in kh_ctx.items():
                context.setdefault(k, v)
        return _raw_templates.TemplateResponse(*args, **kwargs)


templates = _KHorizonTemplates()

# REQ-020: 1초 내 사전 비행점검 서비스 인스턴스(무상태 → 전역 재사용)
_preflight_service = PreflightService()

# 6대 트랙 -> REQ-020 웹 탭 라벨/아이콘 매핑(기술·바우처 탭은 2개 트랙 묶음)
TRACK_TABS: List[dict] = [
    {"key": "ALL", "label": "전체 맞춤 공고", "icon": "fa-list", "tracks": []},
    {"key": "GENERAL_STARTUP", "label": "🚀 창업패키지·청년", "icon": "fa-rocket", "tracks": [NoticeTrack.GENERAL_STARTUP.name, NoticeTrack.DEMOGRAPHIC_FOCUSED.name]},
    {"key": "REGIONAL_LOCAL", "label": "🌊 지역·로컬특화", "icon": "fa-location-dot", "tracks": [NoticeTrack.REGIONAL_LOCAL.name]},
    {"key": "SOCIAL_POLICY", "label": "🏥 사회서비스·복지", "icon": "fa-heart-pulse", "tracks": [NoticeTrack.SOCIAL_POLICY.name]},
    {"key": "DEEP_TECH", "label": "💻 기술R&D·바우처", "icon": "fa-microchip", "tracks": [NoticeTrack.DEEP_TECH_RND.name, NoticeTrack.VOUCHER_BIZ.name]},
]
_TRACK_TO_TAB = {t: tab["key"] for tab in TRACK_TABS for t in (tab["tracks"] or [tab["key"] if tab["key"] != "ALL" else ""]) }


def _profile_from_db() -> dict:
    """저장된 사업주 프로필 조회 (미설정/실패 시 빈 프로필 폴백)."""
    try:
        db = _get_db()
        db.ensure_schema()
        prof = db.get_company_profile()
        if prof:
            # '미설정' 기본행은 company_name 공백으로 판별
            if not any((prof.get(k) or "") for k in ("company_name", "biz_reg_no", "opened_date", "address")):
                return {"__empty__": True}
            return prof
        return {"__empty__": True}
    except Exception as e:
        logger.warning("프로필 DB 조회 실패: %s", e)
        return {"__empty__": True}


async def _run_pipeline_task():
    from ..main import run_daily_pipeline
    return await run_daily_pipeline(PROJECT_ROOT)


scheduler = AsyncScheduler(task_fn=_run_pipeline_task, interval_seconds=1800, enabled=False)


def _get_audit_report() -> dict:
    report_file = PROJECT_ROOT / "storage" / "audit_report.json"
    if report_file.exists():
        try:
            with open(report_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("감사 보고서 JSON 읽기 실패: %s", e)
    # 없을 경우 자동 1회 생성
    try:
        from tests.audit.audit_runner import AuditRunner
        runner = AuditRunner(output_dir=str(PROJECT_ROOT / "storage"))
        return runner.run_all()
    except Exception as e:
        logger.warning("감사 러너 자동 실행 실패: %s", e)
        return {
            "timestamp": "N/A",
            "duration_seconds": 0.0,
            "all_passed": False,
            "total_score": 0.0,
            "max_score": 100.0,
            "status": "UNVERIFIED",
            "results": [],
        }


def _get_db() -> GrantDatabase:
    return GrantDatabase(PROJECT_ROOT / "storage" / "grant_master.db")


def _read_recent_logs(max_lines: int = 150) -> List[str]:
    """최근 N줄의 시스템 로그 안전 추출."""
    log_file = PROJECT_ROOT / "storage" / "app.log"
    if not log_file.exists():
        return ["[SYSTEM] 아직 기록된 로그 파일이 없습니다. 파이프라인 또는 감사를 실행하세요."]
    try:
        lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
        return lines[-max_lines:] if len(lines) > max_lines else lines
    except Exception as e:
        logger.warning("로그 파일 읽기 실패: %s", e)
        return [f"[ERROR] 로그 파일을 읽는 중 오류가 발생했습니다: {e}"]


def _get_items_summary() -> List[dict]:
    items_dir = PROJECT_ROOT / "items"
    items = []
    if not items_dir.exists():
        return items

    # 글로벌 사업주 프로필 로드 (REQ-021 상속 기준)
    stored_profile = _profile_from_db()
    global_p = stored_profile if not stored_profile.get("__empty__") else {}

    for folder in sorted(items_dir.iterdir()):
        if not folder.is_dir():
            continue
        p_path = folder / "profile.yaml"
        prop_path = folder / "proposal.md"
        if not p_path.exists():
            continue
        try:
            raw_text = p_path.read_text(encoding="utf-8")
            data = yaml.safe_load(resolve_env_refs(raw_text)) or {}
            meta = data.get("item_meta", {})
            routing = data.get("domain_routing", {})
            specs = data.get("rnd_and_bid_specs", {})
            item_company_specs = data.get("company_specs", {})
            prop_preview = prop_path.read_text(encoding="utf-8") if prop_path.exists() else ""

            # REQ-021: 글로벌 프로필 상속 및 유효 프로필 산출
            effective_profile = merge_item_company_specs(item_company_specs, global_p)
            try:
                cal = _preflight_service.compute_qualifications(effective_profile)
                qualification_tags = cal.get("tags", [])
                is_female = cal.get("is_female_founder", False)
                is_youth = cal.get("is_youth_39", False)
                region = cal.get("region_name", "")
            except Exception:
                qualification_tags = []
                is_female = bool(effective_profile.get("founder_gender") == "F")
                is_youth = False
                region = ""

            # REQ-047: 바이브코딩 프로토타입 캠페인 연동
            db_inst = _get_db()
            camps = db_inst.list_prototype_campaigns(item_id=meta.get("item_id", folder.name))
            campaign = camps[0] if camps else None

            items.append({
                "id": meta.get("item_id", folder.name),
                "name": meta.get("item_name", folder.name),
                "recipients": meta.get("recipients", []),
                "min_score": routing.get("min_match_score", DEFAULT_MIN_MATCH_SCORE),
                "keywords": routing.get("core_keywords", []),
                "target_trl": specs.get("current_trl_range") or str(specs.get("current_trl", "")),
                "company_specs": item_company_specs,
                "effective_profile": effective_profile,
                "qualification_tags": qualification_tags,
                "is_female_founder": is_female,
                "is_youth_39": is_youth,
                "has_rnd_lab": bool(effective_profile.get("has_rnd_lab", False)),
                "region_name": region,
                "certifications": list(effective_profile.get("certifications", [])),
                "proposal_preview": prop_preview[:150],
                "proposal_full": prop_preview,
                "prototype_url": meta.get("prototype_url") or (campaign["prototype_url"] if campaign else ""),
                "campaign": campaign,
            })
        except Exception as e:
            logger.warning("아이템 프로파일 로드 실패[%s]: %s", folder.name, e)
    return items


@app.get("/", response_class=HTMLResponse)
async def root():
    """REQ-037: 인트로 화면(/intro)을 플랫폼의 진정한 메인 진입점으로 설정."""
    return RedirectResponse(url="/intro")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    db = _get_db()
    db.ensure_schema()
    items = _get_items_summary()

    ann_count = 0
    rfp_count = 0
    dispatch_count = 0
    recent_ann = []

    try:
        with sqlite3.connect(str(db.db_path), timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT COUNT(*) FROM announcements").fetchone()
            ann_count = int(row[0]) if row else 0

            row = conn.execute("SELECT COUNT(*) FROM rfp_chunks").fetchone()
            rfp_count = int(row[0]) if row else 0

            row = conn.execute("SELECT COUNT(*) FROM dispatch_history").fetchone()
            dispatch_count = int(row[0]) if row else 0

            cur = conn.execute(
                "SELECT canonical_id, source_portal, title, ministry, organization, deadline, detail_url, target_year "
                "FROM announcements ORDER BY created_at DESC LIMIT 5"
            )
            recent_ann = [dict(r) for r in cur.fetchall()]
    except Exception as e:
        logger.warning("대시보드 DB 집계 실패: %s", e)

    for a in recent_ann:
        a["dday"] = calculate_dday(a.get("deadline"))

    year_stats = db.get_year_statistics()

    # 2026 공고 전체 대상 마감 현황 분석 및 긴급 마감 임박(D-7 이내) 공고 추출
    all_2026_rows = db.list_announcements(year_filter="2026", limit=500)
    for a in all_2026_rows:
        a["dday"] = calculate_dday(a.get("deadline"))

    dday_stats = get_dday_statistics(all_2026_rows)
    urgent_announcements = [a for a in all_2026_rows if a["dday"]["is_imminent"]][:6]

    # ------------------------------------------------------------------ REQ-020
    # 사업주 프로필 배너 + "내 자격 맞춤 추천" KPI (GREEN 신호등 기준)
    stored = _profile_from_db()
    profile_banner = None
    profile_configured = not stored.get("__empty__")
    if profile_configured:
        try:
            profile_banner = _preflight_service.compute_qualifications(stored)
        except Exception as e:
            logger.warning("대시보드 프로필 배너 계산 실패: %s", e)

    # 프로필 기반 GREEN 추천 + 긴급 D-7 중 GREEN 우선 노출 (무중단 degrade)
    profile_reco_count = 0
    profile_green_urgent = []
    precompute_done = 0
    try:
        active_2026 = [a for a in all_2026_rows if not a["dday"]["is_expired"]]
        # 응답 속도 보호: 최대 N건만 사전 비행점검
        for a in active_2026:
            if precompute_done >= 60:
                break
            precompute_done += 1
            notice = RawNotice(
                portal_id=a.get("source_portal", "portal"),
                title=a.get("title", "") or "",
                organization=a.get("organization", "") or "",
                ministry=a.get("ministry", "") or "",
                deadline=a.get("deadline", "") or "",
                detail_url=a.get("detail_url", "") or "",
                body_text=a.get("title", "") or "",
            )
            if profile_configured:
                res = _preflight_service.run(stored, notice)
            else:
                res = _preflight_service.run({}, notice)
            a["_preflight"] = res
            if res.get("status") == "GREEN":
                profile_reco_count += 1
                if a["dday"]["is_imminent"]:
                    profile_green_urgent.append(a)
        profile_green_urgent = profile_green_urgent[:6]
    except Exception as e:
        logger.warning("대시보드 프로필 추천 계산 실패(degrade): %s", e)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "active_page": "dashboard",
            "stats": {
                "announcements_count": ann_count,
                "rfp_chunks_count": rfp_count,
                "dispatched_count": dispatch_count,
                "year_2026_count": year_stats.get("year_2026_count", 0),
                "compliance_rate_pct": year_stats.get("compliance_rate_pct", 100.0),
                "imminent_count": dday_stats.get("imminent_total", 0),
                "profile_recommendation_count": profile_reco_count,
            },
            "year_stats": year_stats,
            "dday_stats": dday_stats,
            "urgent_announcements": urgent_announcements,
            "items": items,
            "recent_announcements": recent_ann,
            "profile_banner": profile_banner,
            "profile_configured": profile_configured,
            "profile_reco_count": profile_reco_count,
            "profile_green_urgent": profile_green_urgent,
            "preflight_scanned": precompute_done,
        },
    )


@app.get("/announcements", response_class=HTMLResponse)
async def announcements_view(
    request: Request,
    q: str = "",
    portal: str = "",
    year: str = "2026",
    status: str = "",
    tab: str = "ALL",
    track: str = "",
):
    db = _get_db()
    db.ensure_schema()
    rows = db.list_announcements(query=q, portal=portal, year_filter=year)
    for a in rows:
        a["dday"] = calculate_dday(a.get("deadline"))
        a["track"] = classify_notice_track(a.get("title", ""), a.get("body_text", "")).name

    year_stats = db.get_year_statistics()
    items = _get_items_summary()

    all_filtered_rows = db.list_announcements(year_filter=year, limit=500)
    for a in all_filtered_rows:
        if "dday" not in a:
            a["dday"] = calculate_dday(a.get("deadline"))
        a.setdefault("track", classify_notice_track(a.get("title", "")).name)
    dday_stats = get_dday_statistics(all_filtered_rows)

    # 접수기간 상태 필터링 (active: 접수중/진행중, imminent: 마감임박, expired: 마감완료, all: 전체)
    if status == "active":
        display_rows = [a for a in rows if not a["dday"]["is_expired"]]
    elif status == "imminent":
        display_rows = [a for a in rows if a["dday"]["is_imminent"]]
    elif status == "expired":
        display_rows = [a for a in rows if a["dday"]["is_expired"]]
    elif status == "all":
        display_rows = rows
    else:
        # 미지정 시: 2026년 조회는 접수기간 내(active) 공고 우선 표시, 과거(past)/전체(all) 연도는 전체 표시
        if year in ("all", "past"):
            display_rows = rows
        else:
            display_rows = [a for a in rows if not a["dday"]["is_expired"]]

    # REQ-020 다차원 탭(트랙) 필터링
    tracks_wanted = None
    if tab in [t["key"] for t in TRACK_TABS] and tab != "ALL":
        tracks_wanted = set(TRACK_TABS[[t["key"] for t in TRACK_TABS].index(tab)]["tracks"])
    if track:
        tracks_wanted = {track}
    if tracks_wanted is not None:
        display_rows = [a for a in display_rows if a.get("track") in tracks_wanted]

    # REQ-020 사업주 프로필 배너 (자격 태그)
    stored = _profile_from_db()
    if stored.get("__empty__"):
        profile_banner = None
    else:
        try:
            profile_banner = _preflight_service.compute_qualifications(stored)
        except Exception as e:
            logger.warning("프로필 배너 계산 실패: %s", e)
            profile_banner = None

    return templates.TemplateResponse(
        request=request,
        name="announcements.html",
        context={
            "active_page": "announcements",
            "announcements": display_rows,
            "items": items,
            "query": q,
            "portal": portal,
            "year": year,
            "status": status,
            "year_stats": year_stats,
            "dday_stats": dday_stats,
            "track_tabs": TRACK_TABS,
            "current_tab": tab,
            "profile_banner": profile_banner,
            "profile_configured": not stored.get("__empty__"),
        },
    )


@app.get("/api/stats/years")
async def get_year_statistics_api():
    """2026 연도 거버넌스 및 연도별 공고 집계 통계 API."""
    db = _get_db()
    db.ensure_schema()
    stats = db.get_year_statistics()
    return {"status": "success", "stats": stats}


@app.get("/api/announcements/dday-summary")
async def get_announcements_dday_summary(year: str = "2026"):
    """공고 D-Day 긴급도 통계 API."""
    db = _get_db()
    db.ensure_schema()
    try:
        rows = db.list_announcements(year_filter=year, limit=1000)
        stats = get_dday_statistics(rows)
        return {"status": "success", "year": year, "dday_stats": stats}
    except Exception as e:
        logger.exception("D-Day 통계 조회 실패: %s", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/api/calendar/2026.ics")
async def get_all_2026_calendar_ics():
    """2026년도 전체 공고 번들 iCalendar (.ics) 파일 다운로드 및 캘린더 피드."""
    db = _get_db()
    db.ensure_schema()
    try:
        rows = db.list_announcements(year_filter="2026", limit=1000)
        ics_content = export_bundle_calendar_ics(rows, calendar_name="2026 정부지원사업 마감 캘린더")
        return Response(
            content=ics_content,
            media_type="text/calendar; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="gov_grants_2026.ics"'},
        )
    except Exception as e:
        logger.exception("2026 번들 캘린더 생성 실패: %s", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/api/announcements/{canonical_id:path}/calendar.ics")
async def get_announcement_calendar_ics(canonical_id: str):
    """단일 공고의 iCalendar (.ics) 파일 다운로드."""
    db = _get_db()
    db.ensure_schema()
    try:
        with sqlite3.connect(str(db.db_path), timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM announcements WHERE canonical_id=?", (canonical_id,)).fetchone()
            if not row:
                return JSONResponse(status_code=404, content={"status": "error", "message": "공고를 찾을 수 없습니다."})
            ann = dict(row)
            ics_content = export_single_notice_ics(ann)
            clean_id = canonical_id.replace(":", "_").replace("/", "_")
            return Response(
                content=ics_content,
                media_type="text/calendar; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="notice_{clean_id}.ics"'},
            )
    except Exception as e:
        logger.exception("개별 캘린더 .ics 생성 실패: %s", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/api/announcements/{canonical_id:path}")
async def get_announcement_detail(canonical_id: str):
    """공고 상세 정보 및 RFP 청크 목록 조회."""
    db = _get_db()
    db.ensure_schema()
    ann = None
    rfps = []
    try:
        with sqlite3.connect(str(db.db_path), timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM announcements WHERE canonical_id=?", (canonical_id,)).fetchone()
            if not row:
                return JSONResponse(status_code=404, content={"status": "error", "message": "공고를 찾을 수 없습니다."})
            ann = dict(row)

            cur = conn.execute("SELECT * FROM rfp_chunks WHERE canonical_id=?", (canonical_id,))
            rfps = [dict(r) for r in cur.fetchall()]
    except Exception as e:
        logger.exception("공고 상세 조회 실패: %s", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

    items = [{"id": it["id"], "name": it["name"]} for it in _get_items_summary()]
    return {
        "status": "success",
        "announcement": ann,
        "rfp_chunks": rfps,
        "available_items": items,
    }


@app.post("/api/matcher/simulate")
async def simulate_match_api(request: Request):
    """임의의 공고 및 사업 아이템 간 실시간 자격 판정 시뮬레이션."""
    from ..common.schemas import RawNotice
    from ..matcher.hybrid_matcher import HybridMatcher

    data = await request.json()
    item_id = str(data.get("item_id", "")).strip()
    canonical_id = str(data.get("canonical_id", "")).strip()

    if not item_id or not canonical_id:
        return JSONResponse(status_code=400, content={"status": "error", "message": "item_id와 canonical_id는 필수입니다."})

    # Load item profile & proposal
    item_dir = PROJECT_ROOT / "items" / item_id
    if not item_dir.exists():
        return JSONResponse(status_code=404, content={"status": "error", "message": "사업 아이템을 찾을 수 없습니다."})

    p_path = item_dir / "profile.yaml"
    prop_path = item_dir / "proposal.md"
    profile = yaml.safe_load(resolve_env_refs(p_path.read_text(encoding="utf-8"))) if p_path.exists() else {}
    proposal_md = prop_path.read_text(encoding="utf-8") if prop_path.exists() else ""

    # Load announcement & rfp chunk from DB
    db = _get_db()
    db.ensure_schema()
    ann_dict = None
    rfp_chunk = {}
    try:
        with sqlite3.connect(str(db.db_path), timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM announcements WHERE canonical_id=?", (canonical_id,)).fetchone()
            if not row:
                return JSONResponse(status_code=404, content={"status": "error", "message": "공고를 찾을 수 없습니다."})
            ann_dict = dict(row)

            # Pick requested RFP chunk or first available
            rfp_id = data.get("rfp_id")
            if rfp_id:
                rfp_row = conn.execute("SELECT * FROM rfp_chunks WHERE rfp_id=?", (rfp_id,)).fetchone()
                if rfp_row:
                    rfp_chunk = dict(rfp_row)
            if not rfp_chunk:
                rfp_row = conn.execute("SELECT * FROM rfp_chunks WHERE canonical_id=? LIMIT 1", (canonical_id,)).fetchone()
                rfp_chunk = dict(rfp_row) if rfp_row else {
                    "rfp_number": "단일공고",
                    "rfp_title": ann_dict.get("title", ""),
                    "content": ann_dict.get("title", ""),
                }
    except Exception as e:
        logger.exception("시뮬레이션 데이터 조회 오류: %s", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

    # Execute HybridMatcher (offline fallback for fast deterministic simulation)
    matcher = HybridMatcher(offline=True)
    notice_obj = RawNotice(
        portal_id=ann_dict.get("source_portal", "portal"),
        title=ann_dict.get("title", ""),
        organization=ann_dict.get("organization", ""),
        ministry=ann_dict.get("ministry", ""),
        deadline=ann_dict.get("deadline", ""),
        detail_url=ann_dict.get("detail_url", ""),
        body_text=ann_dict.get("title", ""),
    )

    try:
        res = matcher.evaluate_notice(
            profile_dict=profile,
            proposal_md=proposal_md,
            notice=notice_obj,
            rfp_chunk=rfp_chunk,
        )
        sem_res = matcher.semantic_engine.score_item_against_notice(
            proposal_md,
            ann_dict.get("title", ""),
            rfp_chunk.get("content", ""),
        )
        eval_dict = res.model_dump()
        eval_dict["semantic_score"] = sem_res.get("semantic_score", 0.0)
        eval_dict["semantic_shared_terms"] = sem_res.get("shared_terms", [])

        # REQ-021: 아이템 company_specs + 글로벌 프로필 상속 기반 Preflight additive 실행
        stored_profile = _profile_from_db()
        global_p = stored_profile if not stored_profile.get("__empty__") else {}
        effective_profile = merge_item_company_specs(profile.get("company_specs", {}), global_p)
        eval_dict["preflight"] = _preflight_service.run(effective_profile, notice_obj)

        return {
            "status": "success",
            "item_id": item_id,
            "canonical_id": canonical_id,
            "evaluation": eval_dict,
        }
    except Exception as e:
        logger.exception("시뮬레이션 실행 중 예외: %s", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/api/profile")
async def get_profile_api():
    """
    REQ-020 · 저장된 사업주 프로필 및 자동 계산된 자격(배너 태그) 조회.
    - 미설정/실패 시: configured=False (빈 프로필 폴백)
    """
    stored = _profile_from_db()
    if stored.get("__empty__"):
        return {"status": "success", "configured": False, "profile": None, "calculated": None, "tags": []}
    try:
        calc = _preflight_service.compute_qualifications(stored)
        return {"status": "success", "configured": True, "profile": stored, "calculated": calc, "tags": calc["tags"]}
    except Exception as e:
        logger.warning("프로필 자격 계산 실패: %s", e)
        return {"status": "success", "configured": True, "profile": stored, "calculated": None, "tags": []}


@app.post("/api/profile")
async def save_profile_api(request: Request):
    """REQ-020 · 사업주 프로필 저장/갱신 (company_profile 테이블 id=1)."""
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"status": "error", "message": "프로필 JSON을 파싱할 수 없습니다."})

    if not isinstance(data, dict):
        return JSONResponse(status_code=400, content={"status": "error", "message": "프로필은 객체이어야 합니다."})

    db = _get_db()
    db.ensure_schema()
    ok = db.upsert_company_profile(data)
    if not ok:
        return JSONResponse(status_code=500, content={"status": "error", "message": "프로필 저장에 실패했습니다."})

    stored = _profile_from_db()
    try:
        calc = _preflight_service.compute_qualifications(stored) if not stored.get("__empty__") else None
    except Exception as e:
        logger.warning("저장 후 자격 계산 실패: %s", e)
        calc = None

    return {
        "status": "success",
        "message": "사업주 프로필 저장 완료",
        "profile": stored,
        "calculated": calc,
        "tags": calc["tags"] if calc else [],
    }


@app.post("/api/matcher/preflight")
async def preflight_api(request: Request):
    """
    REQ-020 · 사전 비행점검(Pre-Flight).
    요청: {"canonical_id": "<공고ID>", "profile": {...}? (동일 요청 인라인 오버라이드 가능)}
    응답: 신호등(GREEN/YELLOW/RED) 종합판정. 프로필 미존재 시 DB 또는 빈 프로필 폴백(무중단).
    """
    try:
        data = await request.json()
    except Exception:
        data = {}
    if not isinstance(data, dict) or not data.get("canonical_id"):
        return JSONResponse(status_code=400, content={"status": "error", "message": "canonical_id는 필수입니다."})

    canonical_id = str(data["canonical_id"]).strip()
    db = _get_db()
    db.ensure_schema()

    try:
        ann = None
        with sqlite3.connect(str(db.db_path), timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM announcements WHERE canonical_id=?", (canonical_id,)).fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"status": "error", "message": "공고를 찾을 수 없습니다."})
        ann = dict(row)
    except Exception as e:
        logger.exception("비행점검 공고 조회 오류: %s", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

    # 프로필: 인라인 우선, 없으면 DB 저장값, 그도 없으면 빈 프로필 폴백
    inline = data.get("profile")
    if isinstance(inline, dict) and inline:
        profile = inline
    else:
        stored = _profile_from_db()
        profile = stored if not stored.get("__empty__") else {}

    notice = RawNotice(
        portal_id=ann.get("source_portal", "portal"),
        title=ann.get("title", "") or "",
        organization=ann.get("organization", "") or "",
        ministry=ann.get("ministry", "") or "",
        deadline=ann.get("deadline", "") or "",
        detail_url=ann.get("detail_url", "") or "",
        body_text=ann.get("title", "") or "",
    )

    result = _preflight_service.run(profile, notice)
    return {
        "status": "success",
        "canonical_id": canonical_id,
        "announcement": {
            "canonical_id": ann.get("canonical_id"),
            "title": ann.get("title"),
            "source_portal": ann.get("source_portal"),
        },
        "preflight": result,
    }


@app.get("/api/announcements")
async def list_announcements_api(
    q: str = "", portal: str = "", year: str = "2026", tab: str = "ALL", track: str = "",
):
    """
    REQ-020 · 공고 JSON 목록 (대시보드/공고 탭 필터링용).
    - track: 6대 트랙 이름(예: GENERAL_STARTUP) 단건 필터
    - tab: REQ-020 탭 키(ALL/GENERAL_STARTUP/REGIONAL_LOCAL/SOCIAL_POLICY/DEEP_TECH) — 트랙 모음 필터
    """
    db = _get_db()
    db.ensure_schema()
    rows = db.list_announcements(query=q, portal=portal, year_filter=year, limit=500)
    for a in rows:
        a["dday"] = calculate_dday(a.get("deadline"))
        a["track"] = classify_notice_track(a.get("title", ""), a.get("body_text", "")).name

    # 탭/트랙 필터
    tracks_wanted = None
    if tab in [t["key"] for t in TRACK_TABS]:
        tracks_wanted = set(TRACK_TABS[[t["key"] for t in TRACK_TABS].index(tab)]["tracks"])
    elif track:
        tracks_wanted = {track}
    if tracks_wanted is not None:
        rows = [a for a in rows if a["track"] in tracks_wanted]

    return {"status": "success", "count": len(rows), "announcements": rows}


@app.get("/items", response_class=HTMLResponse)
async def items_view(request: Request):
    items = _get_items_summary()
    return templates.TemplateResponse(
        request=request,
        name="items.html",
        context={
            "active_page": "items",
            "items": items,
        },
    )


@app.post("/api/items")
async def create_item_api(request: Request):
    """신규 사업 아이템 및 프로파일 동적 생성."""
    import re
    data = await request.json()
    item_id = str(data.get("item_id", "")).strip()

    # Security check: strict regex against path traversal
    if not item_id or not re.match(r"^[a-zA-Z0-9_\-]+$", item_id):
        return JSONResponse(status_code=400, content={"status": "error", "message": "유효하지 않은 item_id 형식입니다."})

    item_dir = PROJECT_ROOT / "items" / item_id
    if item_dir.exists():
        return JSONResponse(status_code=409, content={"status": "error", "message": "이미 존재하는 item_id입니다."})

    item_dir.mkdir(parents=True, exist_ok=True)

    name = data.get("name", item_id)
    default_recips = [DEFAULT_NOTIFICATION_EMAIL] if DEFAULT_NOTIFICATION_EMAIL else []
    raw_recips = data.get("recipients")
    if raw_recips is None:
        recipients = default_recips
    elif isinstance(raw_recips, str):
        recipients = [r.strip() for r in raw_recips.split(",") if r.strip()]
    elif isinstance(raw_recips, list):
        recipients = [str(r).strip() for r in raw_recips if str(r).strip()]
    else:
        recipients = default_recips

    keywords = data.get("keywords", [])
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(",") if k.strip()]

    min_score = int(data.get("min_score", DEFAULT_MIN_MATCH_SCORE))
    target_trl = str(data.get("target_trl", "6"))
    proposal_text = data.get("proposal_text", f"# {name}\n\n사업 아이템 제안서 본문 요약")
    company_specs = data.get("company_specs", {})
    prototype_url = str(data.get("prototype_url", "")).strip()

    profile_content = {
        "item_meta": {
            "item_id": item_id,
            "item_name": name,
            "recipients": recipients,
            "prototype_url": prototype_url,
        },
        "collection_scope": {
            "selected_bookmarks": ["k_startup", "ntis", "iris", "nipa", "smtech", "g2b"],
            "enable_open_web_discovery": True,
        },
        "eligibility_specs": {
            "entity_type": "법인사업자",
            "business_age_years": 3,
            "headquarters_location": "서울특별시",
        },
        "rnd_and_bid_specs": {
            "current_trl": 6,
            "current_trl_range": target_trl,
        },
        "domain_routing": {
            "core_keywords": keywords,
            "min_match_score": min_score,
        },
        "company_specs": company_specs if isinstance(company_specs, dict) else {},
        "owner_confirmed_policies": {
            "max_acceptable_cash_match_krw": 50000000,
        },
    }

    try:
        with open(item_dir / "profile.yaml", "w", encoding="utf-8") as f:
            yaml.dump(profile_content, f, allow_unicode=True, sort_keys=False)
        with open(item_dir / "proposal.md", "w", encoding="utf-8") as f:
            f.write(proposal_text)

        if (data.get("create_campaign") or data.get("start_campaign")) and prototype_url:
            from src.prototype.validation_engine import PrototypeValidationEngine
            engine = PrototypeValidationEngine(_get_db())
            engine.create_campaign(
                item_id=item_id,
                tenant_id=getattr(request.state, "tenant_id", "tenant_default"),
                prototype_url=prototype_url,
                title=f"{name} 프로토타입 실사용 검증",
                total_budget=int(data.get("total_budget", 100000)),
                fee_per_test=int(data.get("fee_per_test", 2000)),
            )

        return {"status": "success", "message": "사업 아이템 생성 완료", "item_id": item_id}
    except Exception as e:
        logger.exception("사업 아이템 생성 실패: %s", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.put("/api/items/{item_id}")
async def update_item_api(item_id: str, request: Request):
    """기존 사업 아이템 프로파일 수정."""
    import re
    if not item_id or not re.match(r"^[a-zA-Z0-9_\-]+$", item_id):
        return JSONResponse(status_code=400, content={"status": "error", "message": "유효하지 않은 item_id입니다."})

    item_dir = PROJECT_ROOT / "items" / item_id
    if not item_dir.exists():
        return JSONResponse(status_code=404, content={"status": "error", "message": "해당 아이템을 찾을 수 없습니다."})

    data = await request.json()
    p_path = item_dir / "profile.yaml"
    prop_path = item_dir / "proposal.md"

    try:
        current_data = {}
        if p_path.exists():
            current_data = yaml.safe_load(p_path.read_text(encoding="utf-8")) or {}

        if "name" in data:
            current_data.setdefault("item_meta", {})["item_name"] = data["name"]
        if "recipients" in data:
            rec = data["recipients"]
            if isinstance(rec, str):
                rec = [r.strip() for r in rec.split(",") if r.strip()]
            current_data.setdefault("item_meta", {})["recipients"] = rec
        if "keywords" in data:
            kw = data["keywords"]
            if isinstance(kw, str):
                kw = [k.strip() for k in kw.split(",") if k.strip()]
            current_data.setdefault("domain_routing", {})["core_keywords"] = kw
        if "min_score" in data:
            current_data.setdefault("domain_routing", {})["min_match_score"] = int(data["min_score"])
        if "target_trl" in data:
            current_data.setdefault("rnd_and_bid_specs", {})["current_trl_range"] = str(data["target_trl"])
        if "company_specs" in data and isinstance(data["company_specs"], dict):
            current_data["company_specs"] = data["company_specs"]
        if "prototype_url" in data:
            proto_url = str(data["prototype_url"]).strip()
            current_data.setdefault("item_meta", {})["prototype_url"] = proto_url
            if (data.get("create_campaign") or data.get("start_campaign")) and proto_url:
                from src.prototype.validation_engine import PrototypeValidationEngine
                engine = PrototypeValidationEngine(_get_db())
                engine.create_campaign(
                    item_id=item_id,
                    tenant_id=getattr(request.state, "tenant_id", "tenant_default"),
                    prototype_url=proto_url,
                    title=f"{current_data.get('item_meta', {}).get('item_name', item_id)} 프로토타입 실사용 검증",
                    total_budget=int(data.get("total_budget", 100000)),
                    fee_per_test=int(data.get("fee_per_test", 2000)),
                )

        with open(p_path, "w", encoding="utf-8") as f:
            yaml.dump(current_data, f, allow_unicode=True, sort_keys=False)

        if "proposal_text" in data:
            with open(prop_path, "w", encoding="utf-8") as f:
                f.write(data["proposal_text"])

        return {"status": "success", "message": "사업 아이템 수정 완료"}
    except Exception as e:
        logger.exception("사업 아이템 수정 실패: %s", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.post("/api/items/analyze-proposal")
async def analyze_proposal_api(file: UploadFile = File(...)):
    """
    REQ-022: 사업계획서(HWP/HWPX/PDF/DOCX/TXT) 첨부파일 AI 분석 & 폼 Auto-fill API.
    """
    if not file or not file.filename:
        return JSONResponse(status_code=400, content={"status": "error", "message": "업로드된 파일이 없습니다."})

    try:
        content_bytes = await file.read()
        if not content_bytes:
            return JSONResponse(status_code=400, content={"status": "error", "message": "빈 파일입니다."})

        # 1. 텍스트 추출 (순수 파이썬 파서: HWPX/HWP/PDF/DOCX/TXT)
        text = ProposalParser.extract_text(content_bytes, file.filename)
        if not text or not text.strip():
            return JSONResponse(
                status_code=422,
                content={"status": "error", "message": "문서에서 텍스트를 추출할 수 없습니다. 암호화되었거나 지원되지 않는 형식입니다."},
            )

        # 2. 정형 JSON 스펙 추출 (결정론적 고속 실행)
        extractor = ProposalExtractor()
        extracted = extractor.extract_sync(text)

        return {
            "status": "success",
            "filename": file.filename,
            "text_length": len(text),
            "data": extracted,
        }
    except Exception as e:
        logger.exception("사업계획서 분석 실패: %s", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": f"분석 중 오류 발생: {str(e)}"})


@app.delete("/api/items/{item_id}")
async def delete_item_api(item_id: str):
    """사업 아이템 삭제."""
    import re
    import shutil
    if not item_id or not re.match(r"^[a-zA-Z0-9_\-]+$", item_id):
        return JSONResponse(status_code=400, content={"status": "error", "message": "유효하지 않은 item_id입니다."})

    item_dir = PROJECT_ROOT / "items" / item_id
    if not item_dir.exists():
        return JSONResponse(status_code=404, content={"status": "error", "message": "해당 아이템을 찾을 수 없습니다."})

    try:
        shutil.rmtree(item_dir)
        return {"status": "success", "message": f"아이템 {item_id} 삭제 완료"}
    except Exception as e:
        logger.exception("사업 아이템 삭제 실패: %s", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/matches", response_class=HTMLResponse)
async def matches_view(request: Request):
    db = _get_db()
    db.ensure_schema()
    dispatches = []
    try:
        with sqlite3.connect(str(db.db_path), timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT id, item_id, canonical_id, rfp_id, match_score, sent_at "
                "FROM dispatch_history ORDER BY sent_at DESC LIMIT 100"
            )
            dispatches = [dict(r) for r in cur.fetchall()]
    except Exception as e:
        logger.warning("발송 이력 조회 실패: %s", e)

    return templates.TemplateResponse(
        request=request,
        name="matches.html",
        context={
            "active_page": "matches",
            "dispatches": dispatches,
        },
    )


@app.get("/portals", response_class=HTMLResponse)
async def portals_view(request: Request):
    """각 사이트별 크롤링/접속 요건 및 전국 통합공고 종합 관리 뷰어."""
    from src.common.portal_manager import PortalStatusService
    from src.common.master_grant_directory import MasterGrantService
    from src.common.local_centers_directory import LocalCentersService
    from src.common.global_grant_directory import GlobalGrantsService
    service = PortalStatusService(db=_get_db())
    portals = service.get_all_portal_statuses()

    mg_service = MasterGrantService()
    master_programs = mg_service.get_all_programs()
    monthly_timeline = mg_service.get_monthly_timeline()

    lc_service = LocalCentersService()
    local_centers = lc_service.get_centers()

    gg_service = GlobalGrantsService()
    global_programs = gg_service.get_all_programs()
    global_summary = gg_service.get_summary_by_country()

    from src.collector.notebooklm_sync import NotebookLMSyncService
    nl_service = NotebookLMSyncService(db=_get_db())
    notebook_sync_status = nl_service.get_sync_status()

    return templates.TemplateResponse(
        request=request,
        name="portals.html",
        context={
            "active_page": "portals",
            "portals": portals,
            "master_programs": master_programs,
            "monthly_timeline": monthly_timeline,
            "local_centers": local_centers,
            "global_programs": global_programs,
            "global_summary": global_summary,
            "notebook_sync_status": notebook_sync_status,
        },
    )


@app.get("/api/portals/status")
async def get_portals_status_api():
    """전체 포털 운영/인증/헬스 상태 JSON 반환 API."""
    from src.common.portal_manager import PortalStatusService
    service = PortalStatusService(db=_get_db())
    portals = service.get_all_portal_statuses()
    return {
        "status": "success",
        "count": len(portals),
        "portals": portals,
    }


@app.post("/api/portals/ping/{portal_id}")
async def ping_single_portal_api(portal_id: str):
    """특정 포털 실시간 핑(Ping) 진단 API."""
    from src.common.portal_manager import PortalStatusService
    service = PortalStatusService(db=_get_db())
    res = await service.ping_portal(portal_id)
    return res


@app.post("/api/portals/ping-all")
async def ping_all_portals_api():
    """전체 포털 일괄 병렬 핑(Ping) 진단 API."""
    from src.common.portal_manager import PortalStatusService
    service = PortalStatusService(db=_get_db())
    results = await service.ping_all_portals()
    return {
        "status": "success",
        "count": len(results),
        "results": results,
    }


@app.get("/api/portals/master-grants")
async def get_master_grants_api(
    region: Optional[str] = None,
    agency: Optional[str] = None,
    category: Optional[str] = None,
    month: Optional[int] = None,
    q: Optional[str] = None,
):
    """중앙부처 및 전국 지자체 통합공고 총람 과제 목록 검색 API."""
    from src.common.master_grant_directory import MasterGrantService
    mg_service = MasterGrantService()
    programs = mg_service.get_all_programs(
        region=region,
        agency=agency,
        category=category,
        month=month,
        keyword=q,
    )
    return {
        "status": "success",
        "count": len(programs),
        "programs": programs,
    }


@app.get("/api/portals/master-grants/timeline")
async def get_master_grants_timeline_api():
    """월별(1~12월/수시) 공고 예정 타임라인 캘린더 API."""
    from src.common.master_grant_directory import MasterGrantService
    mg_service = MasterGrantService()
    timeline = mg_service.get_monthly_timeline()
    return {
        "status": "success",
        "timeline": timeline,
    }


@app.get("/api/portals/master-grants/recommend/{item_id}")
async def recommend_master_grants_api(item_id: str):
    """사업 아이템 프로필에 기반한 연간 추천 과제 로드맵 도출 API."""
    from src.common.master_grant_directory import MasterGrantService
    item_dir = PROJECT_ROOT / "items" / item_id
    if not item_dir.exists():
        return JSONResponse(status_code=404, content={"status": "error", "message": "해당 아이템을 찾을 수 없습니다."})

    profile_file = item_dir / "profile.yaml"
    profile_data = {}
    if profile_file.exists():
        profile_data = yaml.safe_load(profile_file.read_text(encoding="utf-8")) or {}

    mg_service = MasterGrantService()
    recommendations = mg_service.recommend_roadmap_for_item(profile_data)
    return {
        "status": "success",
        "item_id": item_id,
        "count": len(recommendations),
        "recommendations": recommendations,
    }


@app.get("/api/portals/local-centers")
async def get_local_centers_api(
    region: Optional[str] = None,
    category: Optional[str] = None,
    office_only: bool = False,
    grants_only: bool = False,
    q: Optional[str] = None,
):
    """전국 지자체별 과제 및 사무실(입주) 지원센터 검색 API."""
    from src.common.local_centers_directory import LocalCentersService
    lc_service = LocalCentersService()
    centers = lc_service.get_centers(
        region=region,
        category=category,
        office_only=office_only,
        grants_only=grants_only,
        keyword=q,
    )
    return {
        "status": "success",
        "count": len(centers),
        "centers": centers,
        "regions_summary": lc_service.get_regions_summary(),
    }


@app.get("/api/portals/global-grants")
async def get_global_grants_api(
    country: Optional[str] = None,
    field: Optional[str] = None,
    visa_required: Optional[bool] = None,
    q: Optional[str] = None,
):
    """해외 주요 선진국 및 거점 도시 특화 유치 지원사업 검색 API."""
    from src.common.global_grant_directory import GlobalGrantsService
    gg_service = GlobalGrantsService()
    programs = gg_service.get_all_programs(
        country=country,
        field=field,
        visa_required=visa_required,
        q=q,
    )
    return {
        "status": "success",
        "count": len(programs),
        "programs": programs,
    }


@app.get("/api/portals/global-grants/summary")
async def get_global_grants_summary_api():
    """국가별 거점 지원사업 통계 및 핵심 혜택 요약 API."""
    from src.common.global_grant_directory import GlobalGrantsService
    gg_service = GlobalGrantsService()
    return {
        "status": "success",
        "summary": gg_service.get_summary_by_country(),
    }


# --------------------------------------------------------------------------
# Google NotebookLM 지속 동기화 (국내외 지원사업 자동 수집/수정/반영) API
# --------------------------------------------------------------------------
@app.get("/api/portals/notebooklm/status")
async def get_notebooklm_sync_status_api():
    """NotebookLM 노트북 연동 상태 및 최근 동기화 통계 조회 API."""
    from src.collector.notebooklm_sync import NotebookLMSyncService
    service = NotebookLMSyncService(db=_get_db())
    return {
        "status": "success",
        "sync_status": service.get_sync_status(),
    }


@app.post("/api/portals/notebooklm/sync")
async def trigger_notebooklm_sync_api(request: Request):
    """NotebookLM 노트북으로부터 국내외 과제 최신 데이터를 수집하여 포털에 자동 반영."""
    payload = {}
    try:
        payload = await request.json()
    except Exception:
        pass

    from src.collector.notebooklm_sync import NotebookLMSyncService
    service = NotebookLMSyncService(db=_get_db())
    notebook_id = (payload or {}).get("notebook_id") or service.notebook_id

    raw_content = (payload or {}).get("raw_content")
    if raw_content:
        parsed_items = service.parse_raw_content(raw_content)
        result = service.reconcile_and_persist(parsed_items, target_notebook_id=notebook_id)
        return {
            "status": "success",
            "message": "원시 데이터를 파싱하여 과제 포털에 즉시 동기화했습니다.",
            "sync_result": result,
        }

    status_info = service.get_sync_status()
    return {
        "status": "success",
        "message": "NotebookLM 동기화 상태가 확인되었습니다.",
        "sync_status": status_info,
    }


@app.post("/api/portals/notebooklm/import")
async def import_notebooklm_data_api(request: Request):
    """NotebookLM에서 내보낸 과제 데이터(JSON/Markdown/Text)를 즉시 파싱하여
    국내외 포털 및 마스터 데이터베이스에 추가/수정(Reconcile) 반영.
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "유효한 JSON 요청 본문이 필요합니다."},
        )

    if not isinstance(payload, dict):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "JSON 객체 형태의 페이로드가 필요합니다."},
        )

    raw_content = payload.get("raw_content") or payload.get("data") or payload.get("programs")
    if not raw_content:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "동기화할 raw_content 데이터가 제공되지 않았습니다."},
        )

    from src.collector.notebooklm_sync import NotebookLMSyncService
    service = NotebookLMSyncService(db=_get_db())
    target_notebook_id = payload.get("notebook_id") or service.notebook_id
    parsed_items = service.parse_raw_content(raw_content)

    if not parsed_items:
        return JSONResponse(
            status_code=422,
            content={"status": "error", "message": "입력 데이터에서 유효한 과제 항목을 파싱하지 못했습니다. JSON 또는 Markdown 형식을 확인해 주세요."},
        )

    result = service.reconcile_and_persist(parsed_items, target_notebook_id=target_notebook_id)
    return {
        "status": "success",
        "message": f"동기화 완료: 신규 {result['added_count']}건 추가, 기존 {result['updated_count']}건 수정 반영",
        "result": result,
    }


@app.get("/api/portals/notebooklm/history")
async def get_notebooklm_history_api(limit: int = 15):
    """NotebookLM 동기화 감사 로그 이력 조회 API."""
    from src.collector.notebooklm_sync import NotebookLMSyncService
    service = NotebookLMSyncService(db=_get_db())
    history = service.get_sync_history(limit=limit)
    return {
        "status": "success",
        "count": len(history),
        "history": history,
    }



@app.get("/audit", response_class=HTMLResponse)
async def audit_view(request: Request):
    """QA Swarm 다각도 품질 감사 리포트 뷰어."""
    audit_data = _get_audit_report()
    return templates.TemplateResponse(
        request=request,
        name="audit.html",
        context={
            "active_page": "audit",
            "audit_data": audit_data,
        },
    )


@app.post("/api/audit/run")
async def trigger_audit_api():
    """QA Swarm 5대 에이전트 종합 감사를 웹에서 비동기 즉시 실행."""
    from tests.audit.audit_runner import AuditRunner
    try:
        runner = AuditRunner(output_dir=str(PROJECT_ROOT / "storage"))
        report = runner.run_all()
        return report
    except Exception as e:
        logger.exception("QA 스웜 감사 실행 오류: %s", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/api/audit/download/{fmt}")
async def download_audit_report(fmt: str):
    """QA Swarm 종합 감사 보고서 다운로드 (md / json)."""
    storage_dir = PROJECT_ROOT / "storage"
    if fmt == "md":
        target_file = storage_dir / "audit_report.md"
        media_type = "text/markdown; charset=utf-8"
        filename = "audit_report.md"
    elif fmt == "json":
        target_file = storage_dir / "audit_report.json"
        media_type = "application/json; charset=utf-8"
        filename = "audit_report.json"
    else:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "지원하지 않는 포맷입니다. (md 또는 json 가능)"},
        )

    if not target_file.exists():
        from tests.audit.audit_runner import AuditRunner
        AuditRunner(output_dir=str(storage_dir)).run_all()

    return FileResponse(
        path=str(target_file),
        media_type=media_type,
        filename=filename,
    )


@app.get("/logs", response_class=HTMLResponse)
async def logs_view(request: Request):
    """시스템 실행 로그 실시간 터미널 뷰어."""
    lines = _read_recent_logs(200)
    return templates.TemplateResponse(
        request=request,
        name="logs.html",
        context={
            "active_page": "logs",
            "lines": lines,
        },
    )


@app.get("/api/logs")
async def get_logs_api(lines: int = 150):
    """최근 시스템 로그 JSON 반환 API."""
    lines_limit = min(500, max(10, lines))
    log_lines = _read_recent_logs(lines_limit)
    return {
        "status": "success",
        "count": len(log_lines),
        "lines": log_lines,
    }


@app.post("/api/pipeline/run")
async def trigger_pipeline_api():
    """웹에서 파이프라인을 비동기로 수동 실행 및 상세 요약 반환."""
    try:
        res = await scheduler.trigger_now()
        items = res.get("items", []) if isinstance(res, dict) else []
        total_items = len(items)
        total_collected = sum(it.get("collected", 0) for it in items)
        total_evaluated = sum(it.get("evaluated", 0) for it in items)
        total_matched = sum(it.get("matched", 0) for it in items)
        total_dispatched = sum(it.get("dispatched", 0) for it in items)
        total_skipped_dup = sum(it.get("skipped_dup", 0) for it in items)

        detail_items = []
        for it in items:
            m_details = it.get("matched_details", [])
            detail_items.append({
                "item_id": it.get("item_id", ""),
                "evaluated": it.get("evaluated", 0),
                "matched": it.get("matched", 0),
                "dispatched": it.get("dispatched", 0),
                "matches": m_details,
            })

        summary_msg = (
            f"아이템 {total_items}개 분석 완료: "
            f"공고 {total_evaluated}건 평가 중 적합 공고 {total_matched}건 발견 "
            f"(신규 등록/발송: {total_dispatched}건, 기존 중복: {total_skipped_dup}건)"
        )

        return {
            "status": "success",
            "message": summary_msg,
            "total_items": total_items,
            "total_collected": total_collected,
            "total_evaluated": total_evaluated,
            "total_matched": total_matched,
            "total_dispatched": total_dispatched,
            "total_skipped_dup": total_skipped_dup,
            "detail_items": detail_items,
            "summary": res,
        }
    except Exception as e:
        logger.exception("웹 수동 파이프라인 실행 오류: %s", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/api/scheduler/status")
async def scheduler_status_api():
    """백그라운드 자동 스케줄러 상태 조회."""
    return scheduler.get_status()


@app.post("/api/scheduler/toggle")
async def scheduler_toggle_api():
    """백그라운드 자동 스케줄러 활성화/비활성화 토글."""
    is_active = scheduler.toggle()
    status = scheduler.get_status()
    status["message"] = f"스케줄러 {'활성화됨' if is_active else '비활성화됨'}"
    return status


# ==============================================================================
# REQ-027: DocuMorph AI - 사업계획서 맞춤 변환 및 코파일럿 엔드포인트
# ==============================================================================
def _get_item_detail(item_id: str) -> Dict[str, Any]:
    """아이템 ID에 대응하는 전체 프로필 및 제안서 본문 로드."""
    items_dir = PROJECT_ROOT / "items" / item_id
    item_dict: Dict[str, Any] = {
        "id": item_id,
        "name": item_id,
        "summary": "",
        "keywords": [],
        "trl": 4,
        "target_stage": "초기창업",
        "proposal_text": "",
        "company_specs": {},
    }
    if not items_dir.exists():
        all_items = _get_items_summary()
        if all_items:
            first_id = all_items[0]["id"]
            if first_id != item_id:
                return _get_item_detail(first_id)
        return item_dict

    p_path = items_dir / "profile.yaml"
    prop_path = items_dir / "proposal.md"

    if p_path.exists():
        try:
            data = yaml.safe_load(resolve_env_refs(p_path.read_text(encoding="utf-8"))) or {}
            meta = data.get("item_meta", {})
            routing = data.get("domain_routing", {})
            specs = data.get("rnd_and_bid_specs", {})
            comp = data.get("company_specs", {})
            item_dict["name"] = meta.get("item_name", item_id)
            item_dict["summary"] = meta.get("summary") or meta.get("description", "")
            item_dict["keywords"] = routing.get("core_keywords", [])
            trl_val = specs.get("current_trl") or specs.get("current_trl_range") or 4
            try:
                item_dict["trl"] = int(str(trl_val)[0])
            except Exception:
                item_dict["trl"] = 4
            item_dict["target_stage"] = specs.get("target_stage", "초기창업")
            item_dict["company_specs"] = comp
        except Exception as e:
            logger.warning("profile.yaml 읽기 실패: %s", e)

    if prop_path.exists():
        try:
            item_dict["proposal_text"] = prop_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning("proposal.md 읽기 실패: %s", e)

    return item_dict


@app.get("/proposals/tailor", response_class=HTMLResponse)
async def proposal_tailor_view(
    request: Request,
    item_id: Optional[str] = None,
    announcement_id: Optional[str] = None,
    template_id: Optional[str] = None,
    project_id: Optional[str] = None,
):
    """사업계획서 맞춤 변환 및 코파일럿 스튜디오 화면. (REQ-029: project_id 이어쓰기 지원)"""
    from ..generator.template_schemas import get_template, detect_template_for_announcement
    from ..generator.gap_analyzer import ProposalGapAnalyzer

    # REQ-029: 도전 과제(project) 이어쓰기 — 테넌트 격리로 project → announcement/template 해석
    if project_id:
        tenant, _ = _tenant_service.get_current_session(request)
        proj = _get_db().get_grant_project(project_id, tenant["id"])
        if proj:
            announcement_id = proj.get("announcement_id") or announcement_id
            template_id = proj.get("template_id") or template_id

    all_items = _get_items_summary()
    active_item_id = item_id or (all_items[0]["id"] if all_items else "default_item")
    item_detail = _get_item_detail(active_item_id)

    db = _get_db()
    announcement = None
    if announcement_id:
        try:
            with sqlite3.connect(str(db.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT canonical_id, title, organization, ministry, deadline FROM announcements WHERE canonical_id = ?",
                    (announcement_id,),
                ).fetchone()
                if row:
                    announcement = dict(row)
        except Exception as e:
            logger.warning("공고 상세 조회 실패: %s", e)

    if template_id:
        tpl = get_template(template_id)
    elif announcement:
        tpl = detect_template_for_announcement(announcement.get("title", ""), announcement.get("ministry", ""))
    else:
        tpl = get_template("PSST")

    analyzer = ProposalGapAnalyzer()
    gap_result = analyzer.analyze(item_detail, tpl)

    return templates.TemplateResponse(
        request=request,
        name="tailor.html",
        context={
            "active_page": "tailor",
            "all_items": all_items,
            "current_item": item_detail,
            "template": tpl,
            "announcement": announcement,
            "gap_analysis": gap_result,
        },
    )


@app.get("/api/proposals/templates")
async def api_proposals_templates():
    """제공 중인 표준 계획서 템플릿 목록 반환."""
    from ..generator.template_schemas import get_all_templates
    return {"status": "success", "templates": get_all_templates()}


@app.post("/api/proposals/gap-analysis")
async def api_proposals_gap_analysis(request: Request):
    """마스터 계획서와 타깃 템플릿 간 갭 분석 수행 API."""
    from ..generator.template_schemas import get_template
    from ..generator.gap_analyzer import ProposalGapAnalyzer

    data = await request.json()
    item_id = data.get("item_id", "")
    template_id = data.get("template_id", "PSST")

    item_detail = _get_item_detail(item_id)
    tpl = get_template(template_id)
    analyzer = ProposalGapAnalyzer()
    gap_result = analyzer.analyze(item_detail, tpl)

    return {"status": "success", "gap_analysis": gap_result}


@app.post("/api/proposals/generate-section")
async def api_proposals_generate_section(request: Request):
    """코파일럿 공고 요건 대응 가이드 도출 API."""
    from ..generator.template_schemas import get_template
    from ..generator.gap_analyzer import ProposalGapAnalyzer
    from ..generator.doc_morpher import DocMorpher

    data = await request.json()
    item_id = data.get("item_id", "")
    template_id = data.get("template_id", "PSST")
    section_id = data.get("section_id", "")
    user_facts = data.get("user_facts", {})

    item_detail = _get_item_detail(item_id)
    tpl = get_template(template_id)
    target_sec = next((s for s in tpl.sections if s.section_id == section_id), None)
    if not target_sec:
        return JSONResponse(status_code=404, content={"status": "error", "message": "존재하지 않는 문항 ID입니다."})

    analyzer = ProposalGapAnalyzer()
    gap_data = analyzer.analyze(item_detail, tpl)
    sec_gap = next((s for s in gap_data["sections"] if s["section_id"] == section_id), None)
    master_context = sec_gap.get("matched_master_text", "") if sec_gap else ""

    morpher = DocMorpher()
    draft = await morpher.generate_section_draft(
        section=target_sec,
        template=tpl,
        master_context=master_context,
        user_facts=user_facts,
        item_meta=item_detail,
    )

    return {
        "status": "success",
        "section_id": section_id,
        "draft": draft,
    }


@app.post("/api/proposals/export")
async def api_proposals_export(request: Request):
    """전체 완성된 계획서 마크다운 취합본 생성 API."""
    from ..generator.template_schemas import get_template
    from ..generator.doc_morpher import DocMorpher

    data = await request.json()
    item_id = data.get("item_id", "")
    template_id = data.get("template_id", "PSST")
    section_drafts = data.get("section_drafts", {})

    item_detail = _get_item_detail(item_id)
    tpl = get_template(template_id)
    morpher = DocMorpher()
    full_content = morpher.assemble_full_document(item_detail, tpl, section_drafts)

    return {
        "status": "success",
        "content": full_content,
        "filename": f"{item_id}_{template_id}_사업계획서.md",
    }


# ==============================================================================
# REQ-028: Multi-Tenant & Company Vault (기업 지식 데이터 룸)
# ==============================================================================
from ..tenant.tenant_service import TenantService, COOKIE_SESSION_NAME
_tenant_service = TenantService()


@app.get("/vault", response_class=HTMLResponse)
async def vault_view(request: Request):
    """기업 지식 데이터 룸 (Company Vault) 화면."""
    tenant, user = _tenant_service.get_current_session(request)
    summary = _tenant_service.get_vault_summary(tenant["id"])
    return templates.TemplateResponse(
        request=request,
        name="vault.html",
        context={
            "active_page": "vault",
            "current_tenant": tenant,
            "current_user": user,
            "vault_summary": summary,
        },
    )


@app.post("/api/vault/upload")
async def api_vault_upload(
    request: Request,
    file: UploadFile = File(...),
    category: str = Form("PROPOSAL"),
):
    """지식 데이터 룸에 파일 업로드 및 자동 AI 스펙 추출."""
    tenant, user = _tenant_service.get_current_session(request)
    file_bytes = await file.read()
    asset = await _tenant_service.ingest_vault_file(
        tenant_id=tenant["id"],
        filename=file.filename or "unknown.pdf",
        file_bytes=file_bytes,
        category=category,
    )
    return {"status": "success", "asset": asset}


@app.get("/api/vault/assets")
async def api_vault_list_assets(request: Request, category: Optional[str] = None):
    """테넌트의 지식 자산 목록 조회."""
    tenant, user = _tenant_service.get_current_session(request)
    assets = _tenant_service.db.list_tenant_assets(tenant["id"], category)
    return {"status": "success", "count": len(assets), "assets": assets}


@app.delete("/api/vault/assets/{asset_id}")
async def api_vault_delete_asset(request: Request, asset_id: str):
    """지식 자산 삭제."""
    tenant, user = _tenant_service.get_current_session(request)
    success = _tenant_service.db.delete_tenant_asset(asset_id, tenant["id"])
    if not success:
        return JSONResponse(status_code=404, content={"status": "error", "message": "자산을 찾을 수 없거나 삭제 권한이 없습니다."})
    return {"status": "success"}


@app.post("/api/auth/social-login")
async def api_auth_social_login(request: Request):
    """소셜 로그인(카카오, 구글) 또는 데모 계정 간이 전환 API."""
    data = await request.json()
    provider = data.get("provider", "demo")
    email = data.get("email", "user@demo.kr")
    name = data.get("name", "사업자")
    company_name = data.get("company_name", "(주)자사명")
    biz_reg_no = data.get("biz_reg_no", "")

    tenant, user, token = _tenant_service.login_social_or_demo(
        provider=provider,
        email=email,
        name=name,
        company_name=company_name,
        biz_reg_no=biz_reg_no,
    )

    resp = JSONResponse(content={
        "status": "success",
        "tenant": tenant,
        "user": user,
    })
    resp.set_cookie(
        key=COOKIE_SESSION_NAME,
        value=token,
        max_age=2592000,
        httponly=True,
        samesite="lax",
    )
    return resp


@app.post("/api/auth/logout")
async def api_auth_logout():
    """로그아웃 처리."""
    resp = JSONResponse(content={"status": "success"})
    resp.delete_cookie(key=COOKIE_SESSION_NAME)
    return resp


# =========================================================
# 11.5b. REQ-029 · 도전자 프로젝트 워크스페이스 (/projects) + Vault 매칭
# =========================================================
_vault_matcher: Optional[VaultPreflightMatcher] = None


def _get_vault_matcher() -> VaultPreflightMatcher:
    global _vault_matcher
    if _vault_matcher is None:
        _vault_matcher = VaultPreflightMatcher(_get_db())
    return _vault_matcher


def _announcement_by_id(canonical_id: Optional[str]) -> Optional[dict]:
    if not canonical_id:
        return None
    db = _get_db()
    try:
        with sqlite3.connect(str(db.db_path), timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM announcements WHERE canonical_id = ?", (canonical_id,)).fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.warning("공고 조회 실패: %s", e)
        return None


def _notices_from_db(limit: int = 40) -> List[RawNotice]:
    """DB 최신 2026 공고를 매칭 대상 RawNotice 리스트로 변환."""
    out: List[RawNotice] = []
    db = _get_db()
    try:
        with sqlite3.connect(str(db.db_path), timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM announcements WHERE target_year = 2026 ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            for row in rows:
                d = dict(row)
                out.append(RawNotice(
                    portal_id=d.get("canonical_id", d.get("source_portal", "portal")),
                    title=d.get("title", ""),
                    organization=d.get("organization", ""),
                    ministry=d.get("ministry", ""),
                    deadline=d.get("deadline", ""),
                    detail_url=d.get("detail_url", ""),
                    body_text=d.get("title", ""),
                ))
    except Exception as e:
        logger.warning("매칭용 공고 조회 실패: %s", e)
    return out


def _decorate_project(project: dict) -> dict:
    """도전 과제 행에 마감 D-Day 배지 + 공고를 붙임."""
    p = dict(project)
    ann = _announcement_by_id(p.get("announcement_id"))
    info = calculate_dday(ann.get("deadline") if ann else None)
    p["dday"] = info or {"d_day": None, "status": "UNKNOWN",
                         "badge_text": "D-?", "badge_class": "bg-slate-100 text-slate-500 border"}
    if ann and not p.get("announcement_title"):
        p["announcement_title"] = ann.get("title", "")
    return p


@app.get("/projects", response_class=HTMLResponse)
async def projects_view(request: Request):
    """도전 과제 프로젝트 워크스페이스 (/projects, 테넌트 격리)."""
    tenant, user = _tenant_service.get_current_session(request)
    db = _get_db()
    projects = [_decorate_project(p) for p in db.list_grant_projects(tenant["id"])]

    active = len(projects)
    avg_progress = round(sum(p.get("progress_pct", 0) or 0 for p in projects) / active, 1) if active else 0.0
    urgent = 0
    for p in projects:
        d = p["dday"]
        st = d.get("status")
        dd = d.get("d_day")
        if st in ("TODAY", "CRITICAL", "WARNING") or (dd is not None and dd <= 7):
            urgent += 1

    recommendations = _get_vault_matcher().match(tenant["id"], _notices_from_db())[:10]

    return templates.TemplateResponse(
        request=request,
        name="projects.html",
        context={
            "active_page": "projects",
            "current_tenant": tenant,
            "current_user": user,
            "projects": projects,
            "kpi": {"count": active, "avg_progress": avg_progress, "urgent": urgent},
            "recommendations": recommendations,
        },
    )


@app.get("/api/vault/match")
async def vault_match_api(request: Request):
    """Vault 자산 기반 초정밀 권장 공고 목록 (RED 자동제거, Match Score 정렬)."""
    tenant, user = _tenant_service.get_current_session(request)
    recommendations = _get_vault_matcher().match(tenant["id"], _notices_from_db())
    return {
        "status": "success",
        "tenant_id": tenant["id"],
        "count": len(recommendations),
        "recommendations": recommendations[:15],
    }


@app.get("/api/projects")
async def list_projects_api(request: Request):
    """테넌트의 도전 과제 프로젝트 목록 (진행률, 마감 D-Day, 템플릿 포함)."""
    tenant, user = _tenant_service.get_current_session(request)
    db = _get_db()
    projects = [_decorate_project(p) for p in db.list_grant_projects(tenant["id"])]
    return {
        "status": "success",
        "tenant_id": tenant["id"],
        "projects": projects,
        "kpi": {
            "count": len(projects),
            "avg_progress": round(sum((p.get("progress_pct", 0) or 0) for p in projects) / len(projects), 1) if projects else 0.0,
        },
    }


@app.post("/api/projects")
async def create_project_api(request: Request):
    """[🎯 도전 과제 등록] canonical_id + template_id로 신규 도전 과제 생성 (테넌트 격리)."""
    import re
    tenant, user = _tenant_service.get_current_session(request)
    data = await request.json()
    canonical_id = str(data.get("canonical_id", "")).strip()
    if not canonical_id or not re.match(r"^[a-zA-Z0-9_\-:.]+$", canonical_id):
        return JSONResponse(status_code=400, content={"status": "error", "message": "유효하지 않은 canonical_id 형식입니다."})

    ann = _announcement_by_id(canonical_id)
    if not ann:
        return JSONResponse(status_code=404, content={"status": "error", "message": "해당 공고를 찾을 수 없습니다."})

    template_id = str(data.get("template_id", "")).strip() or "PSST"
    pid = _get_db().create_grant_project({
        "tenant_id": tenant["id"],
        "announcement_id": canonical_id,
        "announcement_title": ann.get("title", ""),
        "template_id": template_id,
        "status": "INIT",
        "progress_pct": 0,
    })
    return {"status": "success", "project_id": pid, "announcement_title": ann.get("title", "")}


@app.patch("/api/projects/{project_id}")
async def update_project_api(project_id: str, request: Request):
    """도전 과제 상태/진행률 수정 (테넌트 격리, 타 테넌트 편집 차단)."""
    tenant, user = _tenant_service.get_current_session(request)
    data = await request.json()
    fields: dict = {}
    if str(data.get("status", "")).strip():
        fields["status"] = str(data["status"]).strip()
    for key in ("progress_pct", "progress"):
        if key in data and data[key] is not None:
            try:
                fields["progress_pct"] = max(0, min(100, int(data[key])))
            except (ValueError, TypeError):
                pass
            break
    found = _get_db().update_grant_project(project_id, tenant["id"], **fields)
    if not found:
        return JSONResponse(status_code=404, content={"status": "error", "message": "프로젝트를 찾을 수 없습니다."})
    return {"status": "success", "project_id": project_id, "updated": fields}


@app.delete("/api/projects/{project_id}")
async def delete_project_api(project_id: str, request: Request):
    """도전 과제 프로젝트 삭제 (테넌트 격리, 타 테넌트 삭제 차단)."""
    tenant, user = _tenant_service.get_current_session(request)
    deleted = _get_db().delete_grant_project(project_id, tenant["id"])
    if not deleted:
        return JSONResponse(status_code=404, content={"status": "error", "message": "프로젝트를 찾을 수 없습니다."})
    return {"status": "success", "deleted": project_id}


@app.get("/api/status")
async def api_status():
    """시스템 건강도, 통계, QA Swarm, 서킷 브레이커 및 자동 스케줄러 상태 API."""
    from ..common.resilience import get_all_circuit_statuses

    db = _get_db()
    db.ensure_schema()
    items = _get_items_summary()
    audit_data = _get_audit_report()
    ann_count = 0
    with sqlite3.connect(str(db.db_path)) as conn:
        row = conn.execute("SELECT COUNT(*) FROM announcements").fetchone()
        ann_count = int(row[0]) if row else 0
    return {
        "status": "healthy",
        "version": app.version,
        "year_policy": "2026_strict",
        "registered_items": len(items),
        "persisted_announcements": ann_count,
        "database_connected": True,
        "scheduler": scheduler.get_status(),
        "circuits": get_all_circuit_statuses(),
        "qa_swarm": {
            "total_score": audit_data.get("total_score", 0.0),
            "max_score": audit_data.get("max_score", 100.0),
            "status": audit_data.get("status", "UNVERIFIED"),
            "all_passed": audit_data.get("all_passed", False),
            "timestamp": audit_data.get("timestamp", ""),
        },
    }


# ==============================================================================
# REQ-034 Round 1: New routes + security headers
# ==============================================================================

@app.get("/intro", response_class=HTMLResponse)
async def intro(request: Request):
    """REQ-034 /intro: 인트로 페이지 렌더링 (동료 창업자 기획·웹·앱 라운지 큐레이션 6선 포함)."""
    db = _get_db()
    db.ensure_schema()
    all_active = db.list_prototype_campaigns(status="ACTIVE")
    active_campaigns = all_active[:6]  # 인트로 화면에는 엄선된 6개만 큐레이션 노출
    tester_summary = db.get_tester_rewards_summary(tester_id="tester_default")
    return templates.TemplateResponse(
        request=request,
        name="intro.html",
        context={
            "active_page": "intro",
            "active_campaigns": active_campaigns,
            "total_campaigns_count": len(all_active),
            "tester_summary": tester_summary,
        },
    )


@app.get("/feedback-lounge", response_class=HTMLResponse)
@app.get("/prototypes", response_class=HTMLResponse)
async def feedback_lounge_view(
    request: Request,
    type: Optional[str] = None,
    category: Optional[str] = None,
):
    """독립 단독 메뉴: 동료 창업자 기획·웹·앱 체험 & 피드백 라운지 (무료/유료 듀얼 트랙)."""
    db = _get_db()
    db.ensure_schema()
    req_type = type if type and type in ("FREE", "PAID") else None
    cat = category if category and category != "ALL" else None
    campaigns = db.list_prototype_campaigns(
        status="ACTIVE",
        request_type=req_type,
        category=cat,
    )
    tester_summary = db.get_tester_rewards_summary(tester_id="tester_default")
    all_camps = db.list_prototype_campaigns(status=None)
    total_projects = len(all_camps)
    total_testers = sum(c.get("completed_testers", 0) for c in all_camps)
    total_rewards_paid = sum(
        c.get("completed_testers", 0) * c.get("tester_reward", 0) for c in all_camps
    )
    return templates.TemplateResponse(
        request=request,
        name="feedback_lounge.html",
        context={
            "active_page": "feedback_lounge",
            "campaigns": campaigns,
            "tester_summary": tester_summary,
            "selected_type": type or "ALL",
            "selected_category": category or "ALL",
            "stats": {
                "total_projects": total_projects,
                "total_testers": total_testers,
                "total_rewards_paid": total_rewards_paid,
            },
        },
    )


@app.get("/pricing", response_class=HTMLResponse)
async def pricing(request: Request):
    """REQ-034 /pricing: 요금제 페이지 렌더링."""
    db = _get_db()
    db.ensure_schema()
    all_active = db.list_prototype_campaigns(status="ACTIVE")
    active_campaigns = all_active[:6]
    tester_summary = db.get_tester_rewards_summary(tester_id="tester_default")
    return templates.TemplateResponse(
        request=request,
        name="intro.html",
        context={
            "active_page": "pricing",
            "active_campaigns": active_campaigns,
            "total_campaigns_count": len(all_active),
            "tester_summary": tester_summary,
        },
    )


@app.get("/dashboard/biz", response_class=HTMLResponse)
async def dashboard_biz(request: Request):
    """REQ-044 /dashboard/biz: 사업주 관점 맞춤 수주 워크스페이스 대시보드 렌더링."""
    db = _get_db()
    db.ensure_schema()

    # 현재 테넌트 정보 (세션 또는 기본값)
    tenant = getattr(request.state, 'tenant', None) or {
        "id": "tenant_001",
        "company_name": "(주)마음숲테크",
        "biz_model": "ict_deeptech",
        "subscription_tier": "growth",
    }

    # REQ-044: 사업주에게 필요한 4대 핵심 수주 지표 (플랫폼 운영 매출 MRR/ARR 제거)
    founder_kpi = {
        "matched_grants_count": 14,
        "green_count": 8,
        "active_projects_count": 2,
        "max_grant_potential": "최대 3억 5,000만 원",
        "vault_readiness_score": 85,
    }

    # REQ-047: 바이브코딩 동료 프로토타입 체험 캠페인 & 테스터 적립금 요약
    active_campaigns = db.list_prototype_campaigns(status="ACTIVE")
    tester_summary = db.get_tester_rewards_summary(tester_id="tester_default")

    return templates.TemplateResponse(
        request=request,
        name="biz_dashboard.html",
        context={
            "active_page": "dashboard_biz",
            "founder_kpi": founder_kpi,
            "tenant": tenant,
            "active_campaigns": active_campaigns,
            "tester_summary": tester_summary,
        },
    )


# Convenience aliases for business workspace routes
@app.get("/biz/dashboard")
async def redirect_biz_dashboard():
    return RedirectResponse(url="/dashboard/biz", status_code=307)


@app.get("/biz/vault")
async def redirect_biz_vault():
    return RedirectResponse(url="/vault", status_code=307)


@app.get("/biz/projects")
async def redirect_biz_projects():
    return RedirectResponse(url="/projects", status_code=307)


@app.get("/biz/tailor")
async def redirect_biz_tailor():
    return RedirectResponse(url="/proposals/tailor", status_code=307)


@app.get("/biz/announcements")
async def redirect_biz_announcements():
    return RedirectResponse(url="/announcements", status_code=307)


def _get_prototype_engine() -> Any:
    from src.prototype.validation_engine import PrototypeValidationEngine
    db = _get_db()
    db.ensure_schema()
    return PrototypeValidationEngine(db)


# ---------------------------------------------------------------------- REQ-047 기획·웹·앱 검증 엔진 & 피드백 라운지 API (무료/유료 트랙)
@app.post("/api/prototype/campaigns")
async def api_create_prototype_campaign(request: Request):
    """신규 기획·웹·앱 검증 캠페인 개설 (무료 품앗이 및 유료 보증 트랙 지원)."""
    data = await request.json()
    item_id = str(data.get("item_id", "")).strip()
    prototype_url = str(data.get("prototype_url", "")).strip()
    title = str(data.get("title", data.get("item_name", item_id))).strip()
    description = str(data.get("description", "")).strip()
    request_type = str(data.get("request_type", "PAID")).upper()
    category = str(data.get("category", "일반")).strip()
    target_goal = str(data.get("target_goal", "")).strip()
    total_budget = int(data.get("total_budget", data.get("budget", 100000)))
    fee_per_test = int(data.get("fee_per_test", data.get("fee_per_tester", 2000)))
    target_testers = int(data.get("target_testers", 0)) if data.get("target_testers") else None

    if not item_id or not prototype_url:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "아이템 ID와 기획안/프로토타입 URL은 필수 입력입니다."},
        )

    engine = _get_prototype_engine()
    tenant_id = getattr(request.state, "tenant_id", "tenant_default")
    campaign = engine.create_campaign(
        item_id=item_id,
        tenant_id=tenant_id,
        prototype_url=prototype_url,
        title=title or item_id,
        total_budget=total_budget,
        fee_per_test=fee_per_test,
        description=description,
        request_type=request_type,
        category=category,
        target_goal=target_goal,
        target_testers=target_testers,
    )
    return {"status": "success", "campaign": campaign}


@app.get("/api/prototype/campaigns")
async def api_list_prototype_campaigns(
    status: Optional[str] = None,
    item_id: Optional[str] = None,
    request_type: Optional[str] = None,
    category: Optional[str] = None,
    limit: Optional[int] = None,
):
    """프로토타입 검증 캠페인 목록 조회 (트랙별/분야별 필터링)."""
    db = _get_db()
    db.ensure_schema()
    campaigns = db.list_prototype_campaigns(
        status=status,
        item_id=item_id,
        request_type=request_type,
        category=category,
        limit=limit,
    )
    return {"status": "success", "count": len(campaigns), "campaigns": campaigns}


@app.get("/api/prototype/campaigns/{campaign_id}")
async def api_get_prototype_campaign(campaign_id: str):
    """단일 프로토타입 검증 캠페인 상세 조회."""
    db = _get_db()
    db.ensure_schema()
    campaign = db.get_prototype_campaign(campaign_id)
    if not campaign:
        return JSONResponse(status_code=404, content={"status": "error", "message": "캠페인을 찾을 수 없습니다."})
    return {"status": "success", "campaign": campaign}


@app.post("/api/prototype/sessions/start")
async def api_start_prototype_session(request: Request):
    """테스터 실사용 체험 세션 발급."""
    data = await request.json()
    campaign_id = str(data.get("campaign_id", "")).strip()
    tester_id = str(data.get("tester_id", "tester_default")).strip()

    if not campaign_id:
        return JSONResponse(status_code=400, content={"status": "error", "message": "campaign_id는 필수입니다."})

    engine = _get_prototype_engine()
    try:
        session = engine.start_session(campaign_id=campaign_id, tester_id=tester_id)
        return {"status": "success", "session_id": session["id"], "session": session}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})


@app.post("/api/prototype/sessions/heartbeat")
async def api_prototype_heartbeat(request: Request):
    """Page Visibility 기반 체류 시간 갱신."""
    data = await request.json()
    session_id = str(data.get("session_id", "")).strip()
    active_delta = int(data.get("active_delta", data.get("active_increment", 3)))
    is_visible = bool(data.get("is_visible", True))
    visible_increment = int(data.get("visible_increment", active_delta))

    if not session_id:
        return JSONResponse(status_code=400, content={"status": "error", "message": "session_id는 필수입니다."})

    engine = _get_prototype_engine()
    try:
        result = engine.record_heartbeat(
            session_id=session_id,
            active_delta=active_delta,
            active_increment=active_delta,
            visible_increment=visible_increment,
            is_visible=is_visible,
        )
        return {"status": "success", **result}
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})


@app.post("/api/prototype/feedback/submit")
async def api_submit_prototype_feedback(request: Request):
    """3단계 구조화 피드백 제출 및 70% 리워드 적립."""
    data = await request.json()
    session_id = str(data.get("session_id", "")).strip()
    tester_id = str(data.get("tester_id", "tester_default")).strip()
    tester_alias = str(data.get("tester_alias", "")).strip()
    ux_score = int(data.get("ux_score", 5))
    functionality_score = int(data.get("functionality_score", data.get("func_score", 5)))
    willingness_to_pay = int(data.get("willingness_to_pay", data.get("wtp_score", 5)))
    nps_recommend_score = int(data.get("nps_recommend_score", data.get("nps_score", 10)))
    blocker_category = str(data.get("blocker_category", "기타")).strip()
    qualitative_feedback = str(data.get("qualitative_feedback", data.get("qualitative_text", ""))).strip()

    engine = _get_prototype_engine()
    try:
        res = engine.submit_feedback(
            session_id=session_id,
            tester_id=tester_id,
            tester_alias=tester_alias,
            ux_score=ux_score,
            functionality_score=functionality_score,
            willingness_to_pay=willingness_to_pay,
            nps_recommend_score=nps_recommend_score,
            blocker_category=blocker_category,
            qualitative_feedback=qualitative_feedback,
        )
        return res
    except ValueError as ve:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(ve)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"서버 오류: {e}"})


@app.get("/api/prototype/reports/{campaign_id}")
async def api_get_prototype_report(campaign_id: str):
    """심사위원 제출용 검증 보고서 통계 JSON."""
    engine = _get_prototype_engine()
    try:
        report = engine.generate_validation_report(campaign_id)
        return {"status": "success", "report": report}
    except ValueError as ve:
        return JSONResponse(status_code=404, content={"status": "error", "message": str(ve)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/prototype/report/{campaign_id}", response_class=HTMLResponse)
async def prototype_report_view(request: Request, campaign_id: str):
    """심사위원 제출용 공식 A4 규격 검증 및 피드백 보고서 웹/인쇄 뷰."""
    engine = _get_prototype_engine()
    try:
        report = engine.generate_validation_report(campaign_id)
    except Exception as e:
        return HTMLResponse(f"<h3>보고서를 불러올 수 없습니다: {e}</h3>", status_code=404)

    return templates.TemplateResponse(
        request=request,
        name="prototype_report.html",
        context={
            "active_page": "prototype_report",
            "campaign": report["campaign"],
            "report": report,
        },
    )


@app.get("/admin/platform", response_class=HTMLResponse)
async def admin_platform(request: Request):
    """REQ-034 /admin/platform: 플랫폼 관리자 대시보드 렌더링."""
    from src.common.db import GrantDatabase
    from src.billing.commercial_service import CommercialService

    db = _get_db()
    db.ensure_schema()
    svc = CommercialService(db)

    tenants = svc.list_all_tenants() if hasattr(svc, 'list_all_tenants') else []
    kpi = svc.get_5kpi(tenant_id="admin") if hasattr(svc, 'get_5kpi') else {"mrr": 0, "arr": 0, "credit_balance": 0, "subscription_tier": "free"}

    return templates.TemplateResponse(
        request=request,
        name="admin_platform.html",
        context={
            "active_page": "admin_platform",
            "tenants": tenants,
            "kpi": kpi,
        },
    )


@app.get("/governance/partner", response_class=HTMLResponse)
async def governance_partner_view(request: Request):
    """REQ-037 Google Stitch Screen 3: 거버넌스 공공/파트너 대시보드 렌더링."""
    incubated_enterprises = [
        {
            "name": "(주)딥센스바이오",
            "sector": "AI 융합 헬스케어",
            "announcement_title": "2027 범부처 초격차 1000+ 바이오헬스 R&D",
            "department": "중소벤처기업부 (TIPA)",
            "stage": "심사위원 Q&A 검토",
            "stage_badge": "violet",
            "partner_name": "삼일PwC 공공 R&D 회계팀",
            "updated_at": "2027.02.18",
            "status": "검토 중",
        },
        {
            "name": "(주)에이아이옵틱스",
            "sector": "ICT 딥테크",
            "announcement_title": "TIPS 창업성장기술개발사업(딥테크 팁스)",
            "department": "중소벤처기업부",
            "stage": "예산 산출 중",
            "stage_badge": "cyan",
            "partner_name": "삼일PwC 공공 R&D 회계팀",
            "updated_at": "2027.02.17",
            "status": "진행 중",
        },
        {
            "name": "(주)넥스트머티리얼즈",
            "sector": "첨단 신소재",
            "announcement_title": "소재부품장비 혁신기술개발사업",
            "department": "산업통상자원부 (KEIT)",
            "stage": "공고 요건 분석",
            "stage_badge": "slate",
            "partner_name": "특허법인 K-LEADER 선행기술팀",
            "updated_at": "2027.02.18",
            "status": "분석 중",
        },
        {
            "name": "(주)로컬스마트스토어",
            "sector": "지역특화 플랫폼",
            "announcement_title": "스마트상점 공정혁신 R&D 바우처",
            "department": "소상공인시장진흥공단",
            "stage": "제출 완료",
            "stage_badge": "emerald",
            "partner_name": "법무법인 율촌 R&D 법률지원",
            "updated_at": "2027.02.16",
            "status": "완료",
        },
        {
            "name": "(주)하이퍼로보틱스",
            "sector": "제조 자동화",
            "announcement_title": "제조공정 디지털전환 실증지원 과제",
            "department": "과학기술정보통신부 (IITP)",
            "stage": "심사위원 Q&A 검토",
            "stage_badge": "violet",
            "partner_name": "미배정 (자문 신청 대기)",
            "updated_at": "2027.02.18",
            "status": "배정 대기",
        },
        {
            "name": "(주)클린에너지솔루션",
            "sector": "기후테크/ESG",
            "announcement_title": "탄소중립 선도기술개발 지원사업",
            "department": "환경부·산업부",
            "stage": "공고 요건 분석",
            "stage_badge": "slate",
            "partner_name": "특허법인 K-LEADER 선행기술팀",
            "updated_at": "2027.02.15",
            "status": "분석 중",
        },
    ]

    governance_metrics = {
        "incubated_count": 24,
        "active_grants": 12,
        "reviewed_proposals": 8,
        "deadline_d7": 3,
        "partner_institutions": 18,
        "active_consultations": 9,
    }

    partner_streams = [
        {"role": "회계법인", "task": "연구비 예산 적정성 및 CAPEX 검증", "partner": "삼일PwC 공공정산팀", "active_count": 4, "badge": "cyan"},
        {"role": "특허사무소", "task": "선행기술조사 및 회피설계 자문", "partner": "특허법인 K-LEADER", "active_count": 3, "badge": "violet"},
        {"role": "마케팅·수출 바우처", "task": "사업화 검증 전문가 매칭", "partner": "글로벌 엑셀러레이터 네트워크", "active_count": 2, "badge": "emerald"},
    ]

    return templates.TemplateResponse(
        request=request,
        name="governance_partner.html",
        context={
            "active_page": "governance_partner",
            "incubated_enterprises": incubated_enterprises,
            "metrics": governance_metrics,
            "partner_streams": partner_streams,
        },
    )


@app.get("/admin/audit-logs", response_class=HTMLResponse)
async def admin_audit_logs(request: Request):
    """REQ-034 /admin/audit-logs: 감사로그 뷰어 렌더링."""
    from src.common.db import GrantDatabase
    import sqlite3

    db = _get_db()
    db.ensure_schema()

    audit_logs = []
    try:
        with sqlite3.connect(str(db.db_path), timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100").fetchall()
            audit_logs = [dict(r) for r in rows]
    except Exception as e:
        logger.warning("감사로그 조회 실패: %s", e)

    return templates.TemplateResponse(
        request=request,
        name="audit_logs.html",
        context={
            "active_page": "admin_audit_logs",
            "audit_logs": audit_logs,
        },
    )


@app.post("/api/billing/checkout")
async def api_billing_checkout(request: Request):
    """REQ-034 POST /api/billing/checkout: 구독/결제 실행."""
    from src.common.db import GrantDatabase
    from src.billing.commercial_service import CommercialService

    try:
        data = await request.json()
    except Exception:
        data = {}
    tier = data.get("tier", "growth")
    cycle = data.get("cycle", "monthly")
    biz_reg_no = data.get("biz_reg_no", "")

    db = _get_db()
    db.ensure_schema()
    svc = CommercialService(db)

    result = svc.subscribe(
        tenant_id=biz_reg_no or "test_biz_reg_001",
        tier=tier,
        cycle=cycle,
        actor="web_admin",
    )
    return {"status": "success", "ok": result.get("ok", False), **result}


@app.post("/api/billing/topup")
async def api_billing_topup(request: Request):
    """REQ-045 POST /api/billing/topup: 멤버십 플랜 및 바우처 옵션 충전 (하위 호환 유지)."""
    from src.common.db import GrantDatabase
    from src.billing.commercial_service import CommercialService

    try:
        data = await request.json()
    except Exception:
        data = {}
    amount = data.get("amount", 10000)
    tenant_id = data.get("tenant_id", "tenant_001")

    db = _get_db()
    db.ensure_schema()
    svc = CommercialService(db)

    # amount를 pack으로 변환 (단순화: always use first pack)
    pack = {"id": "pack_300", "credits": 300, "total_krw": 19000}
    result = svc.topup_credits(tenant_id=tenant_id, pack=pack)
    return {"status": "success", "ok": result.get("ok", False), **result}


@app.get("/api/export/hwpx", operation_id="export_hwpx")
@app.post("/api/export/hwpx", operation_id="export_hwpx_post")
async def api_export_hwpx(request: Request):
    """REQ-034 GET+POST /api/export/hwpx: HWPX 내보내기."""
    from src.billing.commercial_service import export_hwpx_bytes
    from fastapi.responses import JSONResponse

    # POST 데이터 또는 GET 쿼리 파라미터 처리
    data = {}
    if request.method == "POST":
        try:
            data = await request.json()
        except Exception:
            data = {}
    else:
        data = dict(request.query_params)

    title = data.get("title", "test_title")
    sections = data.get("sections", [
        {"section_id": "sec_1", "title": "문제인식", "content": "본 연구는 기술 개발을 목적으로 합니다."},
    ])

    try:
        result = export_hwpx_bytes(title, sections)
        return JSONResponse(content={"status": "success", "bytes": len(result), "filename": f"{title}.hwpx"})
    except Exception as e:
        return JSONResponse(status_code=422, content={"status": "error", "message": str(e)})


@app.get("/api/export/docx", operation_id="export_docx")
@app.post("/api/export/docx", operation_id="export_docx_post")
async def api_export_docx(request: Request):
    """REQ-034 GET+POST /api/export/docx: DOCX 내보내기."""
    from src.billing.commercial_service import export_docx_bytes
    from fastapi.responses import JSONResponse

    # POST 데이터 또는 GET 쿼리 파라미터 처리
    data = {}
    if request.method == "POST":
        try:
            data = await request.json()
        except Exception:
            data = {}
    else:
        data = dict(request.query_params)

    title = data.get("title", "test_docx")
    sections = data.get("sections", [
        {"section_id": "sec_1", "title": "문제인식", "content": "본 연구는 기술 개발을 목적으로 합니다."},
    ])

    try:
        result = export_docx_bytes(title, sections)
        return JSONResponse(content={"status": "success", "bytes": len(result), "filename": f"{title}.docx"})
    except Exception as e:
        return JSONResponse(status_code=422, content={"status": "error", "message": str(e)})


@app.get("/api/admin/audit/verify", operation_id="admin_audit_verify")
@app.post("/api/admin/audit/verify", operation_id="admin_audit_verify_post")
async def api_admin_audit_verify(request: Request):
    """REQ-034 GET+POST /api/admin/audit/verify: 감사로드 체인 verify."""
    from src.common.db import GrantDatabase
    import sqlite3

    db = _get_db()
    db.ensure_schema()

    verified_count = 0
    rows = []
    ok = True

    try:
        with sqlite3.connect(str(db.db_path), timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM audit_logs ORDER BY id").fetchall()
            rows = [dict(r) for r in rows]

        # 간단한 체인 검증 (실제 verify_audit_chain 로직 재구현)
        if len(rows) > 1:
            for i in range(1, len(rows)):
                prev_hash = rows[i-1].get("curr_hash", "")
                curr_hash = rows[i].get("prev_hash", "")
                if prev_hash != curr_hash:
                    ok = False
                    break
            verified_count = len(rows) if ok else 0
        else:
            verified_count = len(rows)

    except Exception as e:
        logger.warning("감사로드 verify 실패: %s", e)
        ok = False
        verified_count = 0

    return {
        "status": "success",
        "ok": ok,
        "verified_count": verified_count,
        "logs": rows if rows else [],
    }


@app.post("/api/admin/tenants")
async def api_admin_tenants(request: Request):
    """REQ-034 POST /api/admin/tenants: 테넌트 생성/상태 변경."""
    from src.common.db import GrantDatabase
    from src.billing.commercial_service import CommercialService

    data = await request.json()
    biz_reg_no = data.get("biz_reg_no", "")
    tier = data.get("tier", "growth")
    action = data.get("action", "create")  # create, activate, suspend, past_due

    db = _get_db()
    db.ensure_schema()
    svc = CommercialService(db)

    if action == "create":
        result = svc.subscribe(
            tenant_id=biz_reg_no or "new_tenant_001",
            tier=tier,
            cycle="monthly",
            actor="super_admin",
        )
    elif action in ("activate", "suspend", "past_due"):
        with db._connect() as conn:
            conn.execute(
                "UPDATE tenants SET status = ? WHERE biz_reg_no = ?",
                (action, biz_reg_no or "new_tenant_001"),
            )
            conn.commit()
        result = {"ok": True, "action": action, "tenant_id": biz_reg_no}
    else:
        result = {"ok": False, "message": "알 수 없는 액션입니다."}

    return {"status": "success", "ok": result.get("ok", False), **result}




@app.post("/api/auth/role")
async def api_switch_role(request: Request):
    """REQ-037: 3대 권한(visitor / subscriber / admin) 분리 서비스 전환 API."""
    try:
        data = await request.json()
    except Exception:
        data = {}
    role = (data.get("role") or "visitor").strip().lower()
    if role not in ROLE_PORTALS:
        return JSONResponse(status_code=400, content={"status": "error", "ok": False, "message": "유효하지 않은 권한입니다."})
    portal = ROLE_PORTALS[role]
    resp = JSONResponse(
        content={
            "status": "success",
            "ok": True,
            "role": role,
            "badge": portal["badge"],
            "home_url": portal["home_url"],
            "nav_items": portal["nav_items"],
        }
    )
    resp.set_cookie(key="sshai_role", value=role, path="/", max_age=86400 * 30, samesite="lax")
    return resp


@app.get("/api/design-system")
async def api_design_system():
    """REQ-037: Google Stitch & K-Horizon 2027 디자인 토큰·5인 전문가·3대 권한 포털 명세 API."""
    return {
        "status": "success",
        "ok": True,
        "design_system": K_HORIZON_2027_TOKENS,
        "stitch": STITCH_PROJECT_METADATA,
        "council": DESIGN_COUNCIL_5EXPERTS,
        "role_portals": ROLE_PORTALS,
    }


def run_server(host: str = "127.0.0.1", port: int = 8080):
    import uvicorn
    # 127.0.0.1 바인딩 강제 (최은정 보안 원칙)
    port = int(os.environ.get("WEB_PORT") or port)
    uvicorn.run("src.web.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run_server()

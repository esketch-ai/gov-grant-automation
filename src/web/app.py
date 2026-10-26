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

from fastapi import FastAPI, Request, Form, BackgroundTasks, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates

from ..common.logging_config import get_logger
from ..common.schemas import resolve_env_refs, RawNotice
from ..common.db import GrantDatabase
from ..common.scheduler import AsyncScheduler
from ..common.deadline import calculate_dday, get_dday_statistics
from ..common.ical_exporter import export_single_notice_ics, export_bundle_calendar_ics
from ..matcher.preflight import PreflightService
from ..matcher.multi_axis_matcher import classify_notice_track, NoticeTrack

logger = get_logger("web_admin")

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(title="SSHAI-CWA 2026 관리자 대시보드", version="1.5.0")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

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
            prop_preview = prop_path.read_text(encoding="utf-8") if prop_path.exists() else ""
            items.append({
                "id": meta.get("item_id", folder.name),
                "name": meta.get("item_name", folder.name),
                "recipients": meta.get("recipients", []),
                "min_score": routing.get("min_match_score", 75),
                "keywords": routing.get("core_keywords", []),
                "target_trl": specs.get("current_trl_range") or str(specs.get("current_trl", "")),
                "proposal_preview": prop_preview[:150],
                "proposal_full": prop_preview,
            })
        except Exception as e:
            logger.warning("아이템 프로파일 로드 실패[%s]: %s", folder.name, e)
    return items


@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/dashboard")


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
    recipients = data.get("recipients", ["admin@company.com"])
    if isinstance(recipients, str):
        recipients = [r.strip() for r in recipients.split(",") if r.strip()]

    keywords = data.get("keywords", [])
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(",") if k.strip()]

    min_score = int(data.get("min_score", 75))
    target_trl = str(data.get("target_trl", "6"))
    proposal_text = data.get("proposal_text", f"# {name}\n\n사업 아이템 제안서 본문 요약")

    profile_content = {
        "item_meta": {
            "item_id": item_id,
            "item_name": name,
            "recipients": recipients,
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
        "owner_confirmed_policies": {
            "max_acceptable_cash_match_krw": 50000000,
        },
    }

    try:
        with open(item_dir / "profile.yaml", "w", encoding="utf-8") as f:
            yaml.dump(profile_content, f, allow_unicode=True, sort_keys=False)
        with open(item_dir / "proposal.md", "w", encoding="utf-8") as f:
            f.write(proposal_text)
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

        with open(p_path, "w", encoding="utf-8") as f:
            yaml.dump(current_data, f, allow_unicode=True, sort_keys=False)

        if "proposal_text" in data:
            with open(prop_path, "w", encoding="utf-8") as f:
                f.write(data["proposal_text"])

        return {"status": "success", "message": "사업 아이템 수정 완료"}
    except Exception as e:
        logger.exception("사업 아이템 수정 실패: %s", e)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


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
    """웹에서 파이프라인을 비동기로 수동 실행."""
    try:
        res = await scheduler.trigger_now()
        return {"status": "success", "message": "파이프라인 실행 완료", "summary": res}
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
        "version": "1.4.0",
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


def run_server(host: str = "127.0.0.1", port: int = 8080):
    import uvicorn
    # 127.0.0.1 바인딩 강제 (최은정 보안 원칙)
    port = int(os.environ.get("WEB_PORT") or port)
    uvicorn.run("src.web.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run_server()

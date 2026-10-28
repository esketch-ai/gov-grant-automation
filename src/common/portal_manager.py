"""
포털 운영 관리 및 상태 진단 서비스 (PortalStatusService)
REQ-026: 각 사이트별 수집 방식, 인증/접속 요건, 실시간 헬스 및 핑 진단.
"""
from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
import yaml

from src.common.db import GrantDatabase
from src.common.logging_config import get_logger
from src.common.resilience import get_circuit_breaker

logger = get_logger("portal_manager")
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class PortalStatusService:
    """각 기관 포털의 크롤링 방식, 접속/인증 요건 및 네트워크 도달성을 진단하는 서비스."""

    PORTAL_METADATA_EXTRAS = {
        "k_startup": {
            "auth_type": "API_KEY_REQUIRED",
            "auth_type_label": "공공데이터포털 API Key 필요",
            "required_env_key": "DATA_GO_KR_KEY",
            "login_required_for_web": False,
            "crawling_method": "OpenAPI REST (TypeA)",
            "description": "중소벤처기업부/창업진흥원 공식 창업지원 포털 (OpenAPI 지원)",
            "api_signup_url": "https://www.data.go.kr/data/15012586/openapi.do",
        },
        "g2b": {
            "auth_type": "LOGIN_CERT_REQUIRED",
            "auth_type_label": "조달청 공동인증서 로그인 / API Key 필요",
            "required_env_key": "G2B_API_KEY",
            "login_required_for_web": True,
            "crawling_method": "OpenAPI REST (TypeB) + 차세대 딥링크",
            "description": "조달청 국가종합전자조달 (웹 직접검색은 로그인 필요, OpenAPI 수집 권장)",
            "api_signup_url": "https://www.data.go.kr/data/15058815/openapi.do",
        },
        "iris": {
            "auth_type": "PUBLIC_BOARD",
            "auth_type_label": "공개 게시판 (인증 불필요)",
            "required_env_key": None,
            "login_required_for_web": False,
            "crawling_method": "헤드리스 브라우저 스크래핑 (TypeC)",
            "description": "범부처통합연구지원시스템 국가 R&D 공고 (공개 웹 접근 가능)",
            "api_signup_url": None,
        },
        "ntis": {
            "auth_type": "PUBLIC_BOARD",
            "auth_type_label": "공개 게시판 (인증 불필요)",
            "required_env_key": None,
            "login_required_for_web": False,
            "crawling_method": "헤드리스 브라우저 스크래핑 (TypeC)",
            "description": "국가과학기술지식정보서비스 국가 R&D 통합 조회",
            "api_signup_url": None,
        },
        "nipa": {
            "auth_type": "PUBLIC_BOARD",
            "auth_type_label": "공개 게시판 (인증 불필요)",
            "required_env_key": None,
            "login_required_for_web": False,
            "crawling_method": "기관 게시판 스크래핑 (TypeD)",
            "description": "정보통신산업진흥원 ICT/AI 지원사업 공고",
            "api_signup_url": None,
        },
        "keit": {
            "auth_type": "PUBLIC_BOARD",
            "auth_type_label": "공개 게시판 (인증 불필요)",
            "required_env_key": None,
            "login_required_for_web": False,
            "crawling_method": "기관 게시판 스크래핑 (TypeD)",
            "description": "산업기술R&D 정보포털(이로움) 산업부 전용 공고",
            "api_signup_url": None,
        },
        "smtech": {
            "auth_type": "PUBLIC_BOARD",
            "auth_type_label": "공개 게시판 (인증 불필요)",
            "required_env_key": None,
            "login_required_for_web": False,
            "crawling_method": "기관 게시판 스크래핑 (TypeD)",
            "description": "중소기업기술개발사업 종합관리시스템 (중기부 R&D)",
            "api_signup_url": None,
        },
        "khidi": {
            "auth_type": "PUBLIC_BOARD",
            "auth_type_label": "공개 게시판 (인증 불필요)",
            "required_env_key": None,
            "login_required_for_web": False,
            "crawling_method": "기관 게시판 스크래핑 (TypeD)",
            "description": "한국보건산업진흥원 바이오·의료기기 지원 공고",
            "api_signup_url": None,
        },
        "rndia": {
            "auth_type": "PUBLIC_BOARD",
            "auth_type_label": "공개 게시판 (인증 불필요)",
            "required_env_key": None,
            "login_required_for_web": False,
            "crawling_method": "기관 게시판 스크래핑 (TypeD)",
            "description": "한국산업기술진흥협회 민간 기업연구소/기술 바우처",
            "api_signup_url": None,
        },
        "modoo": {
            "auth_type": "PUBLIC_BOARD",
            "auth_type_label": "공개 게시판 (인증 불필요)",
            "required_env_key": None,
            "login_required_for_web": False,
            "crawling_method": "기관 게시판 스크래핑 (TypeD)",
            "description": "스타트업 지원사업 종합 포털",
            "api_signup_url": None,
        },
        "songpa_se": {
            "auth_type": "PUBLIC_BOARD",
            "auth_type_label": "공개 게시판 (인증 불필요)",
            "required_env_key": None,
            "login_required_for_web": False,
            "crawling_method": "레거시 ASP 세션 우회 (TypeE)",
            "description": "지자체(송파구) 사회적경제지원센터 공고",
            "api_signup_url": None,
        },
        "bizinfo": {
            "auth_type": "PUBLIC_BOARD",
            "auth_type_label": "공개 게시판 (인증 불필요)",
            "required_env_key": None,
            "login_required_for_web": False,
            "crawling_method": "기관 게시판 스크래핑 (TypeD)",
            "description": "중소벤처기업부 기업마당 전국 정책·융자·보증 통합 정보",
            "api_signup_url": None,
        },
        "smes": {
            "auth_type": "PUBLIC_BOARD",
            "auth_type_label": "공개 게시판 (인증 불필요)",
            "required_env_key": None,
            "login_required_for_web": False,
            "crawling_method": "기관 게시판 스크래핑 (TypeD)",
            "description": "중소벤처24 기업확인서 발급 및 통합 행정 서비스",
            "api_signup_url": None,
        },
        "rnd24": {
            "auth_type": "PUBLIC_BOARD",
            "auth_type_label": "공개 게시판 (인증 불필요)",
            "required_env_key": None,
            "login_required_for_web": False,
            "crawling_method": "헤드리스 브라우저 스크래핑 (TypeC)",
            "description": "국가R&D 통합로그인 및 범부처 연구자 단일 인증(SSO)",
            "api_signup_url": None,
        },
        "open_web": {
            "auth_type": "API_KEY_REQUIRED",
            "auth_type_label": "Tavily AI Search Key 필요",
            "required_env_key": "TAVILLY_API_KEY",
            "login_required_for_web": False,
            "crawling_method": "AI 오픈웹 자율 탐색 (TypeF)",
            "description": "미등록 지자체 및 부처 신규 공고 웹 전역 탐색",
            "api_signup_url": "https://tavily.com",
        },
        # =========================================================================
        # 해외 거점 정부 및 글로벌 특화 유치 포털 5대 메타데이터
        # =========================================================================
        "uk_dbt_gep": {
            "auth_type": "PUBLIC_BOARD",
            "auth_type_label": "글로벌 정부 포털 (인증 불필요)",
            "required_env_key": None,
            "login_required_for_web": False,
            "crawling_method": "해외 정부 포털 연계 (TypeG)",
            "description": "영국 기업통상부(DBT) GEP 딜메이커 1:1 전담 & 혁신가 창업자 비자(3년 후 영주권) 연계",
            "api_signup_url": "https://www.great.gov.uk/",
            "is_global": True,
            "country": "영국",
            "region_hub": "런던",
            "specialized_fields": "AI, 딥테크, SaaS, 클라우드, 빅데이터",
            "key_benefits": "딜메이커 24인 1:1 멘토링, 비자 공식보증(최소투자금 요건 0원), 3년만 영주권",
        },
        "fr_cite_stationf": {
            "auth_type": "PUBLIC_BOARD",
            "auth_type_label": "글로벌 정부 포털 (인증 불필요)",
            "required_env_key": None,
            "login_required_for_web": False,
            "crawling_method": "해외 정부 포털 연계 (TypeG)",
            "description": "파리국제예술공동체(Cité) 레지던시(삼성/프랑스문화원) & Station F 라 프렌치 텍 유치",
            "api_signup_url": "https://www.citedesarts.net/",
            "is_global": True,
            "country": "프랑스",
            "region_hub": "파리",
            "specialized_fields": "시각예술, 문학, 디지털창작(VR), 비디오게임, AI, 뷰티테크",
            "key_benefits": "40m² 스튜디오/체재비 전액지원(6개월), Station F 데스크, French Tech Visa",
        },
        "au_austrade_landing": {
            "auth_type": "PUBLIC_BOARD",
            "auth_type_label": "글로벌 정부 포털 (인증 불필요)",
            "required_env_key": None,
            "login_required_for_web": False,
            "crawling_method": "해외 정부 포털 연계 (TypeG)",
            "description": "호주 Austrade 호스피탈리티/F&B 바이어 매칭 & DFAT 한호재단 랜딩패드 주간",
            "api_signup_url": "https://www.austrade.gov.au/",
            "is_global": True,
            "country": "호주",
            "region_hub": "퍼스 / 시드니",
            "specialized_fields": "호스피탈리티, F&B, CleanTech, AgriTech, HealthTech, AI",
            "key_benefits": "West Tech Fest 참가 항공·숙박 전액지원, HORECA/리테일 바이어 매칭, 데모데이",
        },
        "uae_hub71_adgm": {
            "auth_type": "PUBLIC_BOARD",
            "auth_type_label": "글로벌 정부 포털 (인증 불필요)",
            "required_env_key": None,
            "login_required_for_web": False,
            "crawling_method": "해외 정부 포털 연계 (TypeG)",
            "description": "아부다비 ADGM Hub71 Access Program (Ghadan 21 정부 500억 디르함 펀드 기반)",
            "api_signup_url": "https://www.hub71.com/",
            "is_global": True,
            "country": "UAE",
            "region_hub": "아부다비",
            "specialized_fields": "AI, 핀테크, 헬스테크, 기후테크, Web3",
            "key_benefits": "최대 750,000 AED(한화 약 2.8억, 현금+현물), WeWork/고급주거/건강보험, 10년 골든비자",
        },
        "kr_ksc_global": {
            "auth_type": "PUBLIC_BOARD",
            "auth_type_label": "중기부 공식 글로벌 포털",
            "required_env_key": None,
            "login_required_for_web": False,
            "crawling_method": "공공 API 및 글로벌 거점 연계 (TypeA)",
            "description": "중기부·창진원·중진공 K-스타트업 센터 글로벌 7대 거점형/프로그램형 해외 진출 지원",
            "api_signup_url": "https://www.k-startup.go.kr/",
            "is_global": True,
            "country": "대한민국",
            "region_hub": "실리콘밸리 / 파리 / 싱가포르 / 도쿄 / 뉴욕 / 중동",
            "specialized_fields": "AI, 바이오, 친환경, 스마트시티, 로봇, 핀테크",
            "key_benefits": "기업당 6,000만 원 진출자금, 현지 거점 공유오피스 무상입주, 14주 탑티어 AC 멘토링",
        },
    }

    def __init__(self, config_path: Optional[Path] = None, db: Optional[GrantDatabase] = None) -> None:
        self.config_path = config_path or (PROJECT_ROOT / "config" / "master_portals.yaml")
        self.db = db or GrantDatabase(PROJECT_ROOT / "storage" / "grant_master.db")
        self._portals_cfg: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                return data.get("portals", {})
        except Exception as e:
            logger.error("포털 설정 로드 실패: %s", e)
            return {}

    def _get_db_counts(self) -> Dict[str, int]:
        """DB에 보관된 포털별 공고 건수 집계."""
        counts = {}
        try:
            with self.db._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT source_portal, count(*) FROM announcements GROUP BY source_portal")
                for row in cursor.fetchall():
                    if row[0]:
                        counts[row[0]] = row[1]
        except Exception as e:
            logger.warning("DB 공고 수 집계 실패: %s", e)
        return counts

    def get_all_portal_statuses(self) -> List[Dict[str, Any]]:
        """전체 포털의 종합 운영/인증/헬스 상태 리스트 반환."""
        db_counts = self._get_db_counts()
        portals_list: List[Dict[str, Any]] = []

        # 1. master_portals.yaml 기반 포털
        for pid, cfg in self._portals_cfg.items():
            meta = self.PORTAL_METADATA_EXTRAS.get(pid, {})
            req_key = meta.get("required_env_key")
            has_key = bool(os.environ.get(req_key, "").strip()) if req_key else True
            cb = get_circuit_breaker(pid)
            cb_state = str(cb.state) if cb else "CLOSED"

            # 운영 상태 판정
            if cb_state == "OPEN":
                status = "CIRCUIT_OPEN"
                status_label = "서킷 차단 (장애 격리)"
                status_color = "red"
            elif req_key and not has_key:
                status = "BLOCKED_AUTH"
                status_label = "API 키 미설정 (설계상 폴백)"
                status_color = "amber"
            elif meta.get("login_required_for_web") and not has_key:
                status = "LOGIN_REQUIRED"
                status_label = "웹 로그인/인증서 필요"
                status_color = "blue"
            else:
                status = "ACTIVE"
                status_label = "정상 가동 가능 (OpenAPI)" if req_key else "정상 가동 가능"
                status_color = "emerald"

            portals_list.append({
                "portal_id": pid,
                "name": cfg.get("name", pid),
                "adapter_type": cfg.get("adapter_type", "Unknown"),
                "crawling_method": meta.get("crawling_method", cfg.get("adapter_type", "스크래핑")),
                "base_url": cfg.get("base_url", ""),
                "api_endpoint": cfg.get("api_endpoint"),
                "ministry": cfg.get("ministry", "중앙부처/지자체"),
                "auth_type": meta.get("auth_type", "PUBLIC_BOARD"),
                "auth_type_label": meta.get("auth_type_label", "공개 게시판"),
                "required_env_key": req_key,
                "is_auth_configured": has_key,
                "login_required_for_web": meta.get("login_required_for_web", False),
                "operational_status": status,
                "operational_status_label": status_label,
                "operational_status_color": status_color,
                "circuit_state": cb_state,
                "announcements_count": db_counts.get(pid, 0),
                "description": meta.get("description", ""),
                "api_signup_url": meta.get("api_signup_url"),
                "is_global": meta.get("is_global", cfg.get("is_global", False)),
                "country": meta.get("country", cfg.get("country", "대한민국")),
                "region_hub": meta.get("region_hub", cfg.get("region_hub", "국내")),
                "specialized_fields": meta.get("specialized_fields", ""),
                "key_benefits": meta.get("key_benefits", ""),
            })

        # 2. 오픈웹 탐색(Tavily) 포털 추가
        open_web_meta = self.PORTAL_METADATA_EXTRAS.get("open_web", {})
        has_tavily_key = bool(os.environ.get("TAVILLY_API_KEY", "").strip())
        portals_list.append({
            "portal_id": "open_web",
            "name": "오픈웹 AI 탐색 엔진",
            "adapter_type": "TypeF_OpenWeb",
            "crawling_method": open_web_meta.get("crawling_method", "AI 검색 API"),
            "base_url": "https://api.tavily.com",
            "api_endpoint": "https://api.tavily.com/search",
            "ministry": "전 부처/오픈웹",
            "auth_type": open_web_meta.get("auth_type", "API_KEY_REQUIRED"),
            "auth_type_label": open_web_meta.get("auth_type_label", "Tavily API Key 필요"),
            "required_env_key": "TAVILLY_API_KEY",
            "is_auth_configured": has_tavily_key,
            "login_required_for_web": False,
            "operational_status": "ACTIVE" if has_tavily_key else "BLOCKED_AUTH",
            "operational_status_label": "정상 가동 가능" if has_tavily_key else "API 키 미설정 (폴백)",
            "operational_status_color": "emerald" if has_tavily_key else "amber",
            "circuit_state": "CLOSED",
            "announcements_count": db_counts.get("open_web", 0),
            "description": open_web_meta.get("description", ""),
            "api_signup_url": open_web_meta.get("api_signup_url"),
        })

        return portals_list

    async def ping_portal(self, portal_id: str, timeout_sec: float = 3.5) -> Dict[str, Any]:
        """특정 포털에 비동기 HTTP 핑을 전송하여 도달성 및 지연시간 측정."""
        portals = {p["portal_id"]: p for p in self.get_all_portal_statuses()}
        target = portals.get(portal_id)

        if not target:
            return {
                "portal_id": portal_id,
                "is_reachable": False,
                "status_code": 0,
                "latency_ms": 0,
                "error": f"등록되지 않은 포털 ID: {portal_id}",
            }

        url = target.get("base_url") or target.get("api_endpoint")
        if not url:
            return {
                "portal_id": portal_id,
                "is_reachable": False,
                "status_code": 0,
                "latency_ms": 0,
                "error": "핑 대상 URL 부재",
            }

        start_time = time.perf_counter()
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        }
        try:
            async with httpx.AsyncClient(timeout=timeout_sec, follow_redirects=True, verify=False) as client:
                resp = await client.get(url, headers=headers)
                elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 1)
                is_ok = resp.status_code in (200, 301, 302, 403)  # 403(공공 WAF)은 서버 활성으로 간주
                return {
                    "portal_id": portal_id,
                    "target_url": url,
                    "is_reachable": is_ok,
                    "status_code": resp.status_code,
                    "latency_ms": elapsed_ms,
                    "error": None if is_ok else f"HTTP {resp.status_code}",
                }
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 1)
            return {
                "portal_id": portal_id,
                "target_url": url,
                "is_reachable": False,
                "status_code": 0,
                "latency_ms": elapsed_ms,
                "error": str(e)[:100],
            }

    async def ping_all_portals(self, timeout_sec: float = 3.5) -> List[Dict[str, Any]]:
        """전체 포털에 비동기 병렬 핑을 수행하여 결과 수집."""
        portals = self.get_all_portal_statuses()
        tasks = [self.ping_portal(p["portal_id"], timeout_sec=timeout_sec) for p in portals]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results

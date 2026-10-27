"""
5대 수집 어댑터 + 광역 웹 탐색 (src/collector/multi_collector.py)

- TypeA_OpenAPI_Scrape : K-Startup 공공데이터 API
- TypeB_G2B_API        : 나라장터 입찰공고 API
- TypeC_RndAggregator  : NTIS / IRIS (동적 게시판)
- TypeD_AgencyBoard    : NIPA / KEIT / SMTECH / KHIDI / RNDIA / Modoo
- TypeE_LegacyASP      : songpase(bbs.asp?) 세션난수 우회
- enable_open_web_discovery : 오픈 웹 광역 탐색(Tavily / Google CSE)

설계 원칙 (최은정·박준호 통제 포인트 반영):
- 모든 외부 I/O는 try/except + logging, 타임아웃 30s.
- API Key/네트워크 실패 -> WARN 로깅 후 빈 리스트 반환(파이프라인 미중단).
- 첨부 다운로드는 건수 단위 실패를 허용하는 부분 실패 정책.
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import List

import httpx

from ..common.logging_config import get_logger
from ..common.schemas import RawNotice
from ..common.resilience import get_circuit_breaker, CircuitBreakerOpenException

logger = get_logger(__name__)

# 공고번호 정규식 공용 (dedup 과 동일 참조 원칙)
NOTICE_NO_REGEX = re.compile(r"(제\s*\d{4}\s*-\s*\d+\s*호)")


class MultiPortalCollector:
    def __init__(self, download_root: Path, timeout: float = 300.0):
        self.download_root = Path(download_root)
        self.download_root.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    async def collect_for_item(self, item_profile: dict, master_portals: dict) -> List[RawNotice]:
        scope = item_profile.get("collection_scope", {})
        selected_ids = scope.get("selected_bookmarks", [])
        keywords = item_profile.get("domain_routing", {}).get("core_keywords", [])
        results: List[RawNotice] = []

        for pid in selected_ids:
            cfg = master_portals.get("portals", {}).get(pid)
            if not cfg:
                logger.warning("미등록 포털 건너뜀: %s", pid)
                continue

            cb = get_circuit_breaker(pid, failure_threshold=3, recovery_timeout=30.0)
            if not cb.can_execute():
                logger.warning("포털[%s] 서킷 OPEN 상태 -> 빠른 격리(Fast-Fail) 및 수집 건너뜀", pid)
                continue

            adapter = cfg.get("adapter_type")
            try:
                portal_notices: List[RawNotice] = []
                if adapter == "TypeA_OpenAPI_Scrape":
                    portal_notices = await self._collect_kstartup(pid, cfg, keywords)
                elif adapter == "TypeB_G2B_API":
                    portal_notices = await self._collect_g2b(pid, cfg, keywords, item_profile)
                elif adapter in ("TypeC_RndAggregator", "TypeD_AgencyBoard"):
                    portal_notices = await self._collect_playwright_board(pid, cfg)
                elif adapter == "TypeE_LegacyASP":
                    portal_notices = await self._collect_legacy_asp(pid, cfg)
                else:
                    logger.warning("미지원 adapter_type: %s", adapter)

                results.extend(portal_notices)
                cb.record_success()
            except Exception as e:  # 한 포털 실패가 다른 포털/전체를 멈추지 않음
                cb.record_failure()
                logger.exception("포털[%s] 수집 실패: %s (건너뜀)", pid, e)

        if scope.get("enable_open_web_discovery", False):
            try:
                results.extend(await self._discover_open_web(keywords))
            except Exception as e:
                logger.exception("오픈웹 탐색 실패: %s (건너뜀)", e)

        logger.info("총 수집 완료: %d 건", len(results))
        return results

    # ------------------------------------------------------------------ OpenAPI
    async def _collect_kstartup(self, pid: str, cfg: dict, keywords: List[str]) -> List[RawNotice]:
        import os
        import urllib.parse

        service_key = os.environ.get("DATA_GO_KR_KEY", "").strip()
        if not service_key:
            logger.warning("K-Startup 수집 건너뜀: DATA_GO_KR_KEY 미설정")
            return []
        if "%" in service_key:
            service_key = urllib.parse.unquote(service_key)

        notices: List[RawNotice] = []
        endpoint = cfg.get("api_endpoint", "")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for kw in keywords[:3]:
                    params = {
                        "serviceKey": service_key,
                        "pageNo": 1,
                        "numOfRows": 20,
                        "returnType": "json",
                        "searchWord": kw,
                    }
                    resp = await client.get(endpoint, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    items = _safe_items(data)  # response.items.item[]
                    for it in items:
                        pbanc_sn = it.get("pbancSn") or it.get("announcementId") or it.get("pbancId")
                        if pbanc_sn:
                            direct_url = f"https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn={pbanc_sn}"
                        else:
                            direct_url = str(it.get("url") or it.get("detailUrl") or cfg.get("base_url", ""))

                        notice = RawNotice(
                            portal_id=pid,
                            title=str(it.get("title") or it.get("noticeTitle") or "제목없음").strip(),
                            organization=it.get("adminOrg") or cfg.get("name", "K-Startup"),
                            ministry=it.get("ministerDept") or "중소벤처기업부",
                            deadline=str(it.get("applicationDeadline") or "상세공고 참조"),
                            detail_url=direct_url,
                            body_text="",
                            attachment_urls=[],
                        )
                        if notice.title:
                            notices.append(notice)
        except Exception as e:
            logger.warning("K-Startup API 실패: %s", e)
        return notices

    async def _collect_g2b(self, pid: str, cfg: dict, keywords: List[str], profile: dict) -> List[RawNotice]:
        import os
        import urllib.parse
        from datetime import datetime, timedelta

        # 조달청 나라장터 Open API 인증키 (G2B_API_KEY 또는 공공데이터포털 통합 DATA_GO_KR_KEY 호환)
        service_key = (
            os.environ.get("G2B_API_KEY", "").strip()
            or os.environ.get("DATA_GO_KR_KEY", "").strip()
        )
        if not service_key:
            logger.warning("G2B 수집 건너뜀: G2B_API_KEY 미설정")
            return []
        if "%" in service_key:
            service_key = urllib.parse.unquote(service_key)

        notices: List[RawNotice] = []
        endpoint = cfg.get("api_endpoint", "")
        if not endpoint:
            # 기술가이드 기본: 조달청 나라장터 용역 입찰공고 서비스
            endpoint = "http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc"

        license_codes = profile.get("rnd_and_bid_specs", {}).get("g2b_license_codes", [])

        # 기술가이드(BidPublicInfoService) 필수 파라미터:
        # inqryDiv='1' (공고게시일시 기준), inqryBgnDt / inqryEndDt (YYYYMMDDHHMM 12자리, 최대 1개월 이내 준수)
        now = datetime.now()
        bgn_dt = (now - timedelta(days=28)).strftime("%Y%m%d0000")
        end_dt = now.strftime("%Y%m%d2359")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for kw in keywords[:3]:
                    params = {
                        "serviceKey": service_key,
                        "numOfRows": 25,
                        "pageNo": 1,
                        "type": "json",
                        "inqryDiv": "1",
                        "inqryBgnDt": bgn_dt,
                        "inqryEndDt": end_dt,
                        "bidNtceNm": kw,
                    }
                    resp = await client.get(endpoint, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    for row in _safe_items(data):
                        # 과업지시서 및 규격서 첨부파일 목록 수집 (stdNtceDocUrl + ntceSpecDocUrl1~5)
                        attachments: List[str] = []
                        if row.get("stdNtceDocUrl"):
                            attachments.append(str(row["stdNtceDocUrl"]).strip())
                        for i in range(1, 6):
                            spec_url = row.get(f"ntceSpecDocUrl{i}")
                            if spec_url and str(spec_url).strip():
                                attachments.append(str(spec_url).strip())

                        bid_no = str(row.get("bidNtceNo") or row.get("bidno") or "").strip()
                        bid_seq = str(row.get("bidNtceOrd") or row.get("bidseq") or "00").strip()
                        if bid_no:
                            # 차세대 나라장터 딥링크
                            direct_url = f"https://www.g2b.go.kr#PNPE027_01?bidPbancNo={bid_no}&bidPbancOrd={bid_seq}"
                        else:
                            direct_url = str(row.get("bidNtceDtlUrl") or row.get("bidNtceUrcNm") or "https://www.g2b.go.kr#PNPE001_01")

                        dminstt_nm = str(row.get("dminsttNm") or "").strip()
                        ntce_instt_nm = str(row.get("ntceInsttNm") or "").strip()
                        org_name = dminstt_nm or ntce_instt_nm or "한국조달청"

                        deadline_raw = str(row.get("bidClseDt") or row.get("bidNtceEndDt") or "").strip()
                        deadline = deadline_raw if deadline_raw else "상세공고 참조"

                        # 메타데이터 본문 요약 (수요기관, 배정예산, 추정가격, 계약방법)
                        meta_items = []
                        if dminstt_nm:
                            meta_items.append(f"수요기관: {dminstt_nm}")
                        if row.get("asignBdgtAmt"):
                            meta_items.append(f"배정예산: {row.get('asignBdgtAmt')}원")
                        if row.get("presmptPrce"):
                            meta_items.append(f"추정가격: {row.get('presmptPrce')}원")
                        if row.get("cntrctCnclsMthdNm") or row.get("bidMethdNm"):
                            mthd = row.get("cntrctCnclsMthdNm") or row.get("bidMethdNm")
                            meta_items.append(f"계약방식: {mthd}")
                        body_meta = " | ".join(meta_items)

                        notices.append(
                            RawNotice(
                                portal_id=pid,
                                title=str(row.get("bidNtceNm") or "제목없음").strip(),
                                organization=org_name,
                                ministry="조달청 (공공입찰)",
                                deadline=deadline,
                                detail_url=direct_url,
                                body_text=body_meta,
                                attachment_urls=attachments,
                            )
                        )
            if notices and license_codes:
                logger.info("G2B 면허코드 필터 예정: %s (검증은 matcher 계층이 담당)", license_codes)
        except Exception as e:
            logger.warning("G2B API 실패: %s", e)
        return notices

    # ------------------------------------------------------------------ Playwright
    async def _collect_playwright_board(self, pid: str, cfg: dict) -> List[RawNotice]:
        notices: List[RawNotice] = []
        try:
            from playwright.async_api import async_playwright
        except Exception:
            logger.warning("Playwright 미설치 -> %s 보드 수집 건너뜀", pid)
            return []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(cfg["base_url"], wait_until="networkidle", timeout=self.timeout * 1000)
                rows = await page.locator(
                    "table tbody tr, ul.board-list li, div.bbs_list tr"
                ).all()
                for row in rows[:10]:
                    text_content = (await row.inner_text()).strip()
                    link_el = row.locator("a").first
                    if await link_el.count() > 0:
                        href = await link_el.get_attribute("href") or ""
                        full = (
                            href
                            if href.startswith("http")
                            else cfg.get("base_url", "") + "/" + href.lstrip("/")
                        )
                        notices.append(
                            RawNotice(
                                portal_id=pid,
                                title=" ".join(text_content.split("\n"))[:120] or "제목없음",
                                organization=cfg.get("name", "기관 게시판"),
                                ministry=cfg.get("ministry", "범부처/기타"),
                                deadline="상세공고 참조",
                                detail_url=full,
                            )
                        )
            finally:
                await browser.close()
        return notices

    async def _collect_legacy_asp(self, pid: str, cfg: dict) -> List[RawNotice]:
        """songpase(bbs.asp) 등 세션난수(s=...) 우회. 실패 시 폴백 URL로 재진입."""
        notices: List[RawNotice] = []
        try:
            from playwright.async_api import async_playwright
        except Exception:
            logger.warning("Playwright 미설치 -> %s 레거시 수집 건너뜀", pid)
            return []

        base_url = cfg.get("base_url", "")
        pc_val = cfg.get("static_params", {}).get("pc", "n01")
        root_domain = "/".join(base_url.split("/")[:3])

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(root_domain, wait_until="domcontentloaded", timeout=self.timeout * 1000)

                target_link = page.locator(f"a[href*='pc={pc_val}']").first
                if await target_link.count() > 0:
                    valid_href = await target_link.get_attribute("href")
                    full_url = valid_href if valid_href.startswith("http") else f"{root_domain}/{valid_href.lstrip('/')}"
                    await page.goto(full_url, wait_until="domcontentloaded")
                else:
                    await page.goto(f"{base_url}?pc={pc_val}", wait_until="domcontentloaded")

                rows = await page.locator("table tr").all()
                for row in rows:
                    row_text = (await row.inner_text()).strip()
                    if len(row_text) > 15 and any(k in row_text for k in ("공고", "모집", "지원")):
                        notices.append(
                            RawNotice(
                                portal_id=pid,
                                title=" ".join(row_text.split())[:120],
                                organization=cfg.get("name", "지자체/산하기관"),
                                ministry="지자체/산하기관",
                                deadline="본문 확인",
                                detail_url=page.url,
                            )
                        )
            finally:
                await browser.close()
        return notices

    # ------------------------------------------------------------------ Open Web
    async def _discover_open_web(self, keywords: List[str]) -> List[RawNotice]:
        import os
        from datetime import datetime

        api_key = os.environ.get("TAVILLY_API_KEY", "")
        if not api_key:
            logger.info("TAVILLY_API_KEY 미설정 -> 오픈웹 탐색 폴백(빈 결과)")
            return []
        if len(keywords) < 2:
            logger.warning("오픈웹 탐색 키워드가 부족함(>=2 필요), 건너뜀")
            return []

        year = datetime.now().year
        query = f'("{keywords[0]}" OR "{keywords[1]}") ("모집공고" OR "지원사업") "{year}"'
        notices: List[RawNotice] = []
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={"api_key": api_key, "query": query, "max_results": 10},
                )
                resp.raise_for_status()
                for r in resp.json().get("results", []):
                    title = r.get("title", "")
                    if not title:
                        continue
                    notices.append(
                        RawNotice(
                            portal_id="open_web",
                            title=title,
                            organization=r.get("publish_date", "웹 검색"),
                            ministry="광역 탐색",
                            deadline="상세 확인",
                            detail_url=r.get("url", ""),
                            body_text=r.get("content", ""),
                        )
                    )
        except Exception as e:
            logger.warning("오픈웹 탐색 실패: %s", e)
        return notices


# ------------------------------------------------------------------ 유틸
def _safe_items(data: dict) -> list:
    """공공데이터포털 XML/JSON 응답의 items 배열을 안전하게 추출."""
    out: list = []
    if not isinstance(data, dict):
        return out

    # 1. response.body.items (조달청/중기부 data.go.kr 표준 JSON 구조)
    resp = data.get("response")
    if isinstance(resp, dict):
        body = resp.get("body")
        if isinstance(body, dict):
            items_field = body.get("items")
            if isinstance(items_field, list):
                out.extend([x for x in items_field if isinstance(x, dict)])
            elif isinstance(items_field, dict):
                sub = items_field.get("item", [])
                if isinstance(sub, list):
                    out.extend([x for x in sub if isinstance(x, dict)])
                elif isinstance(sub, dict):
                    out.append(sub)
            if not out and "item" in body:
                sub = body.get("item")
                if isinstance(sub, list):
                    out.extend([x for x in sub if isinstance(x, dict)])
                elif isinstance(sub, dict):
                    out.append(sub)

        # 2. response 내부 기타 하위 dict fallback
        if not out:
            for candidate in resp.values():
                if isinstance(candidate, dict):
                    sub = candidate.get("item") or candidate.get("items")
                    if isinstance(sub, list):
                        out.extend([x for x in sub if isinstance(x, dict)])
                    elif isinstance(sub, dict):
                        out.append(sub)

    # 3. 루트 레벨 list / items fallback
    if isinstance(data.get("items"), list):
        out.extend([x for x in data["items"] if isinstance(x, dict)])
    if isinstance(data.get("list"), list):
        out.extend([x for x in data["list"] if isinstance(x, dict)])
    return out

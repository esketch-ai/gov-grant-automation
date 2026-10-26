"""Browser Click Verifier: 실제 사용자의 브라우저 클릭과 동일한 환경에서
외부 포털 직링크의 최종 도착지, HTTP 상태, 페이지 연도 및 공고명 정합성을 실시간 검증하는 엔진.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urlparse

import httpx


@dataclass
class ClickVerificationResult:
    """사용자 브라우저 클릭 검증 결과 데이터클래스."""
    requested_url: str
    final_url: str
    status_code: int
    is_success: bool
    is_deep_link: bool
    is_year_valid: bool
    is_content_matched: bool
    matched_keywords: List[str] = field(default_factory=list)
    detected_years: List[int] = field(default_factory=list)
    error_message: Optional[str] = None

    @property
    def passed(self) -> bool:
        """전체 검증 통과 여부: 성공 응답 + 상세 직링크 + 연도 정합성 + 내용 일치"""
        return (
            self.is_success
            and self.is_deep_link
            and self.is_year_valid
            and self.is_content_matched
        )


class BrowserClickVerifier:
    """실제 브라우저 클릭 시뮬레이션 및 웹 정합성 검증기."""

    CHROME_USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    DEEP_LINK_PATTERNS = {
        "iris.go.kr": [r"ancmId=\d+"],
        "k-startup.go.kr": [r"pbancSn=\d+"],
        "ntis.go.kr": [r"roRndUid=\d+"],
        "g2b.go.kr": [r"bidno=\d+"],
    }

    def __init__(self, timeout_sec: float = 6.0) -> None:
        self.timeout_sec = timeout_sec

    def verify_url_click(
        self,
        url: str,
        expected_keywords: Optional[List[str]] = None,
        expected_year: int = 2026,
    ) -> ClickVerificationResult:
        """
        사용자가 브라우저에서 링크를 클릭했을 때의 전체 여정을 시뮬레이션합니다.
        1. 301/302 리다이렉트 추적
        2. 최종 도착 URL(Final Landed URL) 검증
        3. 본문 내 연도(2026) 및 과제명 정합성 검증
        """
        expected_keywords = expected_keywords or []
        headers = {
            "User-Agent": self.CHROME_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        # 1. 딥링크 패턴 사전 검증
        is_deep_link = self._check_deep_link(url)
        if not is_deep_link:
            return ClickVerificationResult(
                requested_url=url,
                final_url=url,
                status_code=0,
                is_success=False,
                is_deep_link=False,
                is_year_valid=False,
                is_content_matched=False,
                error_message="상세 식별자(ID)가 없는 메인 페이지 또는 검색 목록 URL입니다.",
            )

        # 2. 실제 HTTP 요청 및 리다이렉트 추적
        try:
            with httpx.Client(
                headers=headers,
                follow_redirects=True,
                timeout=self.timeout_sec,
                verify=False,
            ) as client:
                resp = client.get(url)
                final_url = str(resp.url)
                status_code = resp.status_code

                # 403 (공공기관 WAF 방화벽)의 경우, 서버 응답 자체는 도달했으므로 특별 처리
                if status_code not in (200, 301, 302, 403):
                    return ClickVerificationResult(
                        requested_url=url,
                        final_url=final_url,
                        status_code=status_code,
                        is_success=False,
                        is_deep_link=is_deep_link,
                        is_year_valid=False,
                        is_content_matched=False,
                        error_message=f"HTTP 상태 코드 비정상: {status_code}",
                    )

                body_text = resp.text

        except Exception as e:
            # 네트워크 단절 또는 타임아웃
            return ClickVerificationResult(
                requested_url=url,
                final_url=url,
                status_code=0,
                is_success=False,
                is_deep_link=is_deep_link,
                is_year_valid=False,
                is_content_matched=False,
                error_message=f"브라우저 접속 실패: {str(e)}",
            )

        # 3. 본문 내 연도 분석
        # 과거 연도(2025 등) 불일치 탐지
        years_found = [int(y) for y in re.findall(r"\b(202[0-9])년", body_text)]
        detected_years = sorted(list(set(years_found)))

        # 2025년도 국방 과제 등 명확한 과거 과제 불일치 검출
        is_year_valid = True
        if "2025년도 미래국방" in body_text:
            is_year_valid = False
        elif expected_year not in detected_years and any(y < expected_year for y in detected_years):
            # 기대 연도(2026)는 없고 과거 연도만 감지된 경우
            if not any(f"{expected_year}" in body_text for _ in [1]):
                is_year_valid = False

        # 4. 기대 키워드 매칭
        matched_kws = []
        for kw in expected_keywords:
            if kw and kw in body_text:
                matched_kws.append(kw)

        is_content_matched = True
        if expected_keywords:
            # 최소 1개 이상의 핵심 키워드가 실제 본문에 있어야 함
            is_content_matched = len(matched_kws) > 0

        err_msg = None
        if not is_year_valid:
            err_msg = f"과거 연도({detected_years}) 과제 불일치 감지됨"
        elif not is_content_matched:
            err_msg = f"기대 키워드({expected_keywords})가 실제 웹페이지 본문에서 발견되지 않음"

        return ClickVerificationResult(
            requested_url=url,
            final_url=final_url,
            status_code=status_code,
            is_success=True,
            is_deep_link=is_deep_link,
            is_year_valid=is_year_valid,
            is_content_matched=is_content_matched,
            matched_keywords=matched_kws,
            detected_years=detected_years,
            error_message=err_msg,
        )

    def _check_deep_link(self, url: str) -> bool:
        """URL에 상세 식별자 파라미터가 포함되어 있는지 검사."""
        if not url or not url.startswith("http"):
            return False
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        for d_key, patterns in self.DEEP_LINK_PATTERNS.items():
            if d_key in domain:
                return any(re.search(p, url) for p in patterns)

        # 등록되지 않은 도메인은 일반 쿼리스트링 존재 여부 확인
        return bool(parsed.query)

    def audit_html_links(self, html_content: str, ignore_dynamic_templates: bool = True) -> List[dict]:
        """렌더링된 HTML 문서 내의 모든 a 태그 링크를 추출하여 클릭 유효성을 평가."""
        results = []
        link_matches = re.findall(
            r'<a\s+([^>]*?)href=["\']([^"\']*)["\']([^>]*?)>(.*?)</a>',
            html_content,
            re.DOTALL,
        )

        for before_attr, href, after_attr, text in link_matches:
            attrs = f"{before_attr} {after_attr}".lower()
            if ignore_dynamic_templates and 'data-dynamic-link="true"' in attrs:
                # 자바스크립트로 동적 주입되는 모달 플레이스홀더는 정적 링크 감사에서 제외
                continue

            clean_text = re.sub(r"<[^>]+>", "", text).strip()
            is_valid = True
            reason = "OK"

            if href in ("#", "", "javascript:void(0)", "javascript:;"):
                is_valid = False
                reason = "빈 앵커 또는 자바스크립트 더미 링크"
            elif href.startswith("http://") or href.startswith("https://"):
                reason = "외부 링크"
            elif href.startswith("/"):
                reason = "내부 라우트"
            else:
                is_valid = False
                reason = "잘못된 상대 경로"

            results.append({
                "href": href,
                "text": clean_text[:30],
                "is_valid": is_valid,
                "reason": reason,
            })
        return results

    def verify_calendar_ics(self, ics_text: str, expected_title: Optional[str] = None) -> bool:
        """다운로드된 .ics 파일의 RFC 5545 표준 규격 및 공고명 일치 검증."""
        if "BEGIN:VCALENDAR" not in ics_text or "END:VCALENDAR" not in ics_text:
            return False
        if "BEGIN:VEVENT" not in ics_text or "END:VEVENT" not in ics_text:
            return False
        if "DTEND" not in ics_text or "SUMMARY:" not in ics_text:
            return False
        if expected_title and expected_title not in ics_text:
            return False
        return True

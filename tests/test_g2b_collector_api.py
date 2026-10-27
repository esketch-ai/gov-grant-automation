"""
tests/test_g2b_collector_api.py
조달청 나라장터 입찰공고정보서비스 (BidPublicInfoService) 기술가이드 규격 및 수집 어댑터 단위 테스트.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.collector.multi_collector import MultiPortalCollector, _safe_items
from src.common.schemas import RawNotice


def test_safe_items_standard_and_variations():
    """공공데이터포털(data.go.kr) 표준 응답 및 변형 스키마로부터 items 정상 추출 검증."""
    # 1. 표준 최신 JSON 구조 (response.body.items: list)
    sample_modern = {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
            "body": {
                "items": [
                    {"bidNtceNo": "20261009120", "bidNtceNm": "2026년 지능형 전력망 용역"},
                    {"bidNtceNo": "20261009121", "bidNtceNm": "2026년 에너지 AX/DX 구축"},
                ],
                "numOfRows": 10,
                "pageNo": 1,
                "totalCount": 2,
            },
        }
    }
    items_modern = _safe_items(sample_modern)
    assert len(items_modern) == 2
    assert items_modern[0]["bidNtceNo"] == "20261009120"

    # 2. 레거시 단일 item 래핑 구조 (response.body.items.item: list)
    sample_legacy = {
        "response": {
            "body": {
                "items": {
                    "item": [
                        {"bidNtceNo": "20260000001", "bidNtceNm": "레거시 공고"},
                    ]
                }
            }
        }
    }
    items_legacy = _safe_items(sample_legacy)
    assert len(items_legacy) == 1
    assert items_legacy[0]["bidNtceNo"] == "20260000001"

    # 3. 루트 레벨 fallback
    sample_root = {"items": [{"bidNtceNo": "999"}]}
    assert len(_safe_items(sample_root)) == 1


@pytest.mark.asyncio
async def test_collect_g2b_technical_guide_conformance(tmp_path: Path):
    """
    기술가이드문서 기반 _collect_g2b 파라미터 및 필드 정합성 검증:
    - inqryDiv: '1' (공고게시일시 기준 필수)
    - inqryBgnDt / inqryEndDt (12자리 YYYYMMDDHHMM 필수)
    - stdNtceDocUrl + ntceSpecDocUrl1~5 규격서/과업지시서 첨부파일 추출
    - 차세대 나라장터 딥링크 생성
    """
    collector = MultiPortalCollector(download_root=tmp_path)
    cfg = {
        "api_endpoint": "http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc"
    }
    profile = {
        "rnd_and_bid_specs": {"g2b_license_codes": ["1468"]}
    }
    keywords = ["지능형 전력망"]

    mock_resp_json = {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
            "body": {
                "items": [
                    {
                        "bidNtceNo": "20261009120",
                        "bidNtceOrd": "00",
                        "bidNtceNm": "2026년 지능형 전력망 및 에너지 AX/DX 플랫폼 구축 조달 용역",
                        "dminsttNm": "한국전력공사",
                        "ntceInsttNm": "조달청",
                        "bidClseDt": "2026-11-20 18:00",
                        "asignBdgtAmt": 950000000,
                        "presmptPrce": 863636364,
                        "bidMethdNm": "협상에의한계약",
                        "cntrctCnclsMthdNm": "제한경쟁",
                        "stdNtceDocUrl": "https://www.g2b.go.kr/spec/std_doc.pdf",
                        "ntceSpecDocUrl1": "https://www.g2b.go.kr/spec/task_specification.hwp",
                        "ntceSpecDocUrl2": "https://www.g2b.go.kr/spec/rfp.docx",
                    }
                ]
            },
        }
    }

    captured_params = {}

    class MockResponse:
        def __init__(self):
            self.status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return mock_resp_json

    async def mock_get(url, params=None, **kwargs):
        nonlocal captured_params
        captured_params = params
        return MockResponse()

    with patch("os.environ.get", side_effect=lambda k, default="": "TEST_G2B_KEY" if k == "G2B_API_KEY" else ""):
        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            notices = await collector._collect_g2b("g2b", cfg, keywords, profile)

    # 1. 기술가이드 필수 파라미터 전달 검증
    assert captured_params["serviceKey"] == "TEST_G2B_KEY"
    assert captured_params["inqryDiv"] == "1"
    assert len(captured_params["inqryBgnDt"]) == 12  # YYYYMMDDHHMM
    assert len(captured_params["inqryEndDt"]) == 12  # YYYYMMDDHHMM
    assert captured_params["type"] == "json"
    assert captured_params["bidNtceNm"] == "지능형 전력망"

    # 2. 수집된 Notice 필드 검증
    assert len(notices) == 1
    notice = notices[0]
    assert isinstance(notice, RawNotice)
    assert notice.portal_id == "g2b"
    assert "지능형 전력망" in notice.title
    assert notice.organization == "한국전력공사"
    assert notice.deadline == "2026-11-20 18:00"

    # 3. 차세대 나라장터 딥링크 검증
    assert notice.detail_url == "https://www.g2b.go.kr#PNPE027_01?bidPbancNo=20261009120&bidPbancOrd=00"

    # 4. 규격서 + 과업지시서 첨부파일 3건 정상 취합 검증
    assert len(notice.attachment_urls) == 3
    assert "https://www.g2b.go.kr/spec/std_doc.pdf" in notice.attachment_urls
    assert "https://www.g2b.go.kr/spec/task_specification.hwp" in notice.attachment_urls
    assert "https://www.g2b.go.kr/spec/rfp.docx" in notice.attachment_urls

    # 5. 메타데이터(예산, 계약방식) 본문 요약 포함 검증
    assert "배정예산: 950000000원" in notice.body_text
    assert "수요기관: 한국전력공사" in notice.body_text


@pytest.mark.asyncio
async def test_collect_g2b_data_go_kr_key_fallback(tmp_path: Path):
    """G2B_API_KEY가 없고 DATA_GO_KR_KEY만 설정되어 있어도 자동 fallback 호환 검증."""
    collector = MultiPortalCollector(download_root=tmp_path)
    cfg = {"api_endpoint": "http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc"}

    with patch("os.environ.get", side_effect=lambda k, default="": "COMMON_DATA_GO_KR_KEY" if k == "DATA_GO_KR_KEY" else ""):
        # httpx 호출 전 파라미터 serviceKey 확인
        captured_key = None

        async def mock_get(url, params=None, **kwargs):
            nonlocal captured_key
            captured_key = params.get("serviceKey")
            m = AsyncMock()
            m.raise_for_status = lambda: None
            m.json = lambda: {"response": {"body": {"items": []}}}
            return m

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            await collector._collect_g2b("g2b", cfg, ["테스트"], {})

    assert captured_key == "COMMON_DATA_GO_KR_KEY"


@pytest.mark.asyncio
async def test_collect_g2b_unquotes_encoded_key(tmp_path: Path):
    """Encoding 키(URL 인코딩 특수문자 포함) 입력 시 httpx 이중 인코딩 방지를 위해 자동 unquote 검증."""
    collector = MultiPortalCollector(download_root=tmp_path)
    cfg = {"api_endpoint": "http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc"}

    with patch("os.environ.get", side_effect=lambda k, default="": "ENCODED_KEY%2BTEST%3D%3D" if k == "G2B_API_KEY" else ""):
        captured_key = None

        async def mock_get(url, params=None, **kwargs):
            nonlocal captured_key
            captured_key = params.get("serviceKey")
            m = AsyncMock()
            m.raise_for_status = lambda: None
            m.json = lambda: {"response": {"body": {"items": []}}}
            return m

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            await collector._collect_g2b("g2b", cfg, ["테스트"], {})

    assert captured_key == "ENCODED_KEY+TEST=="

"""이메일 노티피에이터 + 보안 단위 테스트 (최은정 계층). 발송은 mock."""
from __future__ import annotations

import zipfile
from pathlib import Path

from src.common.schemas import RawNotice, GrantEvaluationResult
from src.notifier.email_notifier import GrantEmailNotifier


def _smtp_cfg(**over) -> dict:
    cfg = {
        "smtp": {
            "host": "smtp.gmail.com",
            "port": 587,
            "username": "bot@company.com",
            "password": "x",
            "sender_name": "매칭 에이전트",
            "max_attachment_size_mb": 2,
        }
    }
    cfg["smtp"].update(over)
    return cfg


def _notice() -> RawNotice:
    return RawNotice("k", "제목A", "기관", "과기부", "마감", "https://x/1", body_text="")


def _result():
    return GrantEvaluationResult.model_validate(
        {
            "is_eligible": True,
            "match_score": 90,
            "target_rfp_info": "RFP-01",
            "support_scale_and_period": "3억/6개월(2025-06-30)",
            "condition_checks": [
                {"criterion": "업력", "status": "PASS", "requirement_summary": "1년+",
                 "company_status": "5년", "evidence_quote": "3p"}
            ],
            "owner_inquiries": [
                {"urgency": "HIGH", "category": "현금매칭",
                 "requirement_source": "5p", "question_to_owner": "5억 매칭 수용 가능?",
                 "profile_update_key": "owner_confirmed_policies.max_acceptable_cash_match_krw"}
            ],
            "proposal_alignment_strategy": "강점 강조",
            "note": "",
        }
    )


def test_no_send_when_no_match():
    notif = GrantEmailNotifier(_smtp_cfg())
    # matched_results 비어 -> no-op(예외 없음)
    notif.send_item_digest({"item_meta": {"item_id": "i1", "item_name": "N", "recipients": ["a@x.com"]}}, [])


def test_build_message_contains_owner_inquiry_box():
    notif = GrantEmailNotifier(_smtp_cfg())
    msg = notif.build_message(
        {"item_meta": {"item_id": "i1", "item_name": "음성AI", "recipients": ["a@x.com"]}},
        [(_notice(), _result())],
    )
    html_parts = [p for p in msg.walk() if p.get_content_type() == "text/html"]
    assert html_parts, "html 부재"
    body = html_parts[0].get_payload(decode=True).decode("utf-8")
    assert "사업주 확인" in body
    assert "5억 매칭" in body
    assert "90점" in body or "적합도" in body
    # XSS escape: 사용자 입력 문자열 <script>가 그대로 렌더되지 않아야 함
    assert "<script>" not in body


def test_attachments_zipped_when_over_limit(tmp_path):
    # 2개의 큰 파일(총 > 2MB)
    f1 = tmp_path / "a.pdf"
    f2 = tmp_path / "b.pdf"
    f1.write_bytes(b"x" * (1500 * 1024))
    f2.write_bytes(b"y" * (1500 * 1024))
    n = _notice()
    n.downloaded_files = [f1, f2]

    notif = GrantEmailNotifier(_smtp_cfg(max_attachment_size_mb=2))
    msg = notif.build_message(
        {"item_meta": {"item_id": "i1", "item_name": "음성AI", "recipients": ["a@x.com"]}},
        [(n, _result())],
    )
    # 압축 아카이브 하나로 줄어듦
    parts = list(msg.walk())
    zips = [p for p in parts if p.get_filename() and p.get_filename().endswith(".zip")]
    assert len(zips) == 1
    # 압축 내 2개 파일 포함
    zbytes = zips[0].get_payload(decode=True)
    import io
    zf = zipfile.ZipFile(io.BytesIO(zbytes))
    names = zf.namelist()
    assert {"a.pdf", "b.pdf"}.issubset(set(names))


def test_no_attachments_when_valid_files_empty():
    notif = GrantEmailNotifier(_smtp_cfg())
    msg = notif.build_message(
        {"item_meta": {"item_id": "i1", "item_name": "N", "recipients": ["a@x.com"]}},
        [(_notice(), _result())],
    )
    # 본문(plain/html)만 있고 application 첨부 0건
    apps = [p for p in msg.walk() if p.get_content_type() and p.get_content_type().startswith("application/")]
    assert apps == []


def test_missing_credentials_raise_on_transmit():
    notif = GrantEmailNotifier({"smtp": {"host": "x", "port": 587}})
    msg = notif.build_message(
        {"item_meta": {"item_id": "i1", "item_name": "N", "recipients": ["a@x.com"]}},
        [(_notice(), _result())],
    )
    try:
        notif._transmit(msg, ["a@x.com"])
        assert False, "예외가 던져졌어야 함"
    except RuntimeError:
        pass

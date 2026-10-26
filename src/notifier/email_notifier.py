"""
사업주 확인 요청 박스 + 원본 첨부파일 패키징 메일 발송기
(src/notifier/email_notifier.py)

- 매칭 결과(item별)를 HTML 리포트로 렌더. 최상단: [사업주 확인 및 의사결정 요청] 박스.
- 하단: 자격 요건 성립 근거 표 + 제안서 연계 전략.
- 원본 첨부가 20MB 초과 시 자동 ZIP 압축(_attach_files_safely).
- SMTP STARTTLS 발송 + 인증 실패/타임아웃 시 1회 재시도.
- **보안(최은정)**: 비밀정보 100% 외부화(.env / mail_config.yaml 변수), XSS escape.
"""
from __future__ import annotations

import html
import smtplib
import ssl
import zipfile
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Tuple
from datetime import datetime

from ..common.logging_config import get_logger
from ..common.schemas import GrantEvaluationResult, RawNotice

logger = get_logger(__name__)


class GrantEmailNotifier:
    def __init__(self, smtp_cfg: dict, max_send_retry: int = 1):
        # cfg 는 mail_config.yaml 로드 + ${VAR} 치환된 dict 의 'smtp' 블록
        self.cfg = smtp_cfg.get("smtp", {}) if isinstance(smtp_cfg, dict) else {}
        self.max_retry = max_send_retry
        # 비밀정보 하드코딩 방지: 부재 시 명확히 실패하게
        if not self.cfg.get("username"):
            logger.warning("SMTP username 미설정(.env SMTP_USERNAME 필요) - 발송 불가")

    # ------------------------------------------------------------- API
    def send_item_digest(
        self, item_profile: dict, matched_results: List[Tuple[RawNotice, GrantEvaluationResult]]
    ) -> None:
        if not matched_results:
            logger.info("매칭 0건 -> 메일 발송 건너뜀: %s",
                        item_profile.get("item_meta", {}).get("item_id"))
            return

        item_name = item_profile["item_meta"]["item_name"]
        recipients = list(item_profile["item_meta"]["recipients"])
        msg = self.build_message(item_profile, matched_results)

        logger.info("발송 시작: %s / %d건 수신자=%s",
                    item_name, len(matched_results), recipients)

        last_error: str | None = None
        for attempt in range(1 + self.max_retry):
            try:
                self._transmit(msg, recipients)
                logger.info("이메일 발송 성공: %s", item_name)
                return
            except Exception as e:
                last_error = f"attempt {attempt + 1}: {e}"
                logger.warning("이메일 발송 실패 %s", last_error)

        logger.error("이메일 발송 최종 실패[%s]: %s", item_name, last_error)
        # 파이프라인을 멈추지 않음. 다만 실패가 '발송되지 않았다'는 사실은 명시.

    def build_message(
        self, item_profile: dict, matched_results: List[Tuple[RawNotice, GrantEvaluationResult]]
    ) -> MIMEMultipart:
        item_name = item_profile["item_meta"]["item_name"]
        item_id = item_profile["item_meta"]["item_id"]
        recipients = list(item_profile["item_meta"]["recipients"])
        today = datetime.now().strftime("%Y-%m-%d")
        sender_name = self.cfg.get("sender_name", "정부과제 AI 매칭 에이전트")

        msg = MIMEMultipart()
        msg["Subject"] = f"[과제매칭리포트] {item_name} - 신청 가능 과제 {len(matched_results)}건 발굴 ({today})"
        msg["From"] = f"{sender_name} <{self.cfg.get('username', 'unknown@company.com')}>"
        msg["To"] = ", ".join(recipients)
        # charset=utf-8 지정으로 본문이 base64 대신 가독성 있는 UTF-8 텍스트로 렌더

        html_body = self._render_html_report(item_name, matched_results)
        msg.attach(MIMEText("이 메일은 HTML 뷰어에서만 정상 표시됩니다.", "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # 원본 첨부파일
        all_files: List[Path] = []
        for notice, _ in matched_results:
            all_files.extend(notice.downloaded_files or [])
        self._attach_files_safely(msg, all_files, item_id)
        return msg

    # ------------------------------------------------------------- render
    def _render_html_report(self, item_name: str, matched_results: list) -> str:
        sections = [
            "<div style='font-family: Pretendard, sans-serif; color:#222; line-height:1.6;'>"
            f"<h3>[{html.escape(item_name)}] 일일 정부과제·R&D 매칭 리포트</h3>"
            f"<p>금일 수집·정밀 자격대조를 통과한 총 {len(matched_results)}건 결과입니다.</p><hr/>"
        ]

        for idx, (notice, eval_res) in enumerate(matched_results, start=1):
            sections.append(
                f"<h4>{idx}. {html.escape(notice.title)} "
                f"<small>(적합도 {eval_res.match_score}점)</small></h4>"
            )
            sections.append(
                "<ul>"
                f"<li>주관기관/소관부처: {html.escape(notice.organization)} "
                f"({html.escape(notice.ministry)})</li>"
                f"<li>타겟 세부과제(RFP): {html.escape(eval_res.target_rfp_info)}</li>"
                f"<li>지원규모/신청기간: {html.escape(eval_res.support_scale_and_period)}</li>"
                f"<li>원본 공고 링크: <a href='{html.escape(notice.detail_url)}'>"
                f"{html.escape(notice.detail_url)}</a></li>"
                "</ul>"
            )

            # [사업주 확인 및 의사결정 요청] 박스 — 최상단 강조
            if eval_res.owner_inquiries:
                sections.append(
                    "<div style='background-color:#fff8e6; border-left:5px solid #e6a100; "
                    "padding:12px; margin:12px 0;'>"
                    "<p style='margin-top:0; font-weight:bold; color:#b36b00;'>"
                    "[사업주 확인 및 의사결정 요청 사항]</p><ol>"
                )
                for inq in eval_res.owner_inquiries:
                    sections.append(
                        f"<li>[{html.escape(str(inq.urgency))}/{html.escape(inq.category)}] "
                        f"{html.escape(inq.question_to_owner)}<br/>"
                        "<span style='font-size:0.9em; color:#555;'>"
                        f"- 공고 근거: {html.escape(inq.requirement_source)} "
                        f"(프로파일 반영키: {html.escape(inq.profile_update_key)})</span></li>"
                    )
                sections.append("</ol></div>")

            # 자격 요건 성립 검증 근거 표
            sections.append(
                "<table border='1' cellpadding='6' cellspacing='0' "
                "style='border-collapse:collapse; width:100%; font-size:0.92em;'>"
                "<tr style='background-color:#f2f4f8;'>"
                "<th>검증 항목</th><th>판정</th><th>공고 요구 기준</th>"
                "<th>현재 상태</th><th>공고문 발췌 근거</th></tr>"
            )
            for chk in eval_res.condition_checks:
                sections.append(
                    f"<tr><td>{html.escape(chk.criterion)}</td>"
                    f"<td>{html.escape(str(chk.status))}</td>"
                    f"<td>{html.escape(chk.requirement_summary)}</td>"
                    f"<td>{html.escape(chk.company_status)}</td>"
                    f"<td>{html.escape(chk.evidence_quote)}</td></tr>"
                )
            sections.append("</table>")
            sections.append(
                f"<p>제안서 연계 전략: {html.escape(eval_res.proposal_alignment_strategy)}</p><hr/>"
            )

        sections.append("</div>")
        return "\n".join(sections)

    # ------------------------------------------------------------- attach
    def _attach_files_safely(self, msg: MIMEMultipart, files: List[Path], item_id: str) -> None:
        valid_files = [f for f in files if f and Path(f).exists()]
        if not valid_files:
            return

        total_mb = sum(f.stat().st_size for f in valid_files) / (1024 * 1024)
        max_mb = float(self.cfg.get("max_attachment_size_mb", 20))

        if total_mb > max_mb:
            zip_path = valid_files[0].parent / f"{item_id}_attachments.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in valid_files:
                    zf.write(f, arcname=f.name)
            logger.info("첨부용량 초과(%.1fMB > %dMB) -> %s 압축", total_mb, max_mb, zip_path.name)
            valid_files = [zip_path]

        for fpath in valid_files:
            try:
                with open(fpath, "rb") as fp:
                    raw = fp.read()
                part = MIMEApplication(raw, Name=fpath.name)
                part["Content-Disposition"] = f'attachment; filename="{fpath.name}"'
                msg.attach(part)
            except Exception as e:
                logger.warning("첨부 추가 실패[%s]: %s", fpath.name, e)

    # ------------------------------------------------------------- send
    def _transmit(self, msg: "MIMEMultipart", recipients: list) -> None:
        host = self.cfg.get("host")
        port = int(self.cfg.get("port", 587))
        user = self.cfg.get("username")
        pwd = self.cfg.get("password")
        if not user or not pwd:
            raise RuntimeError("SMTP 인증정보(username/password)가 주입되지 않았습니다.")

        msg_bytes = msg.as_string()
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(user, pwd)
            server.sendmail(user, recipients, msg_bytes)

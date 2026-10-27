"""
일일 자동화 오케스트레이터 (src/main.py)

items/ 폴더를 순회하며 아이템별로:
  1. 수집(collector) -> 2. 중복제거(dedup) -> 3. RFP 분할(parser)
  -> 4. 자격 검증(matcher) -> 5. 이메일 발송(notifier)

설계 원칙(박준호 통제):
- 각 단계·각 아이템·각 공고는 try/except 로 격리 => 한 건 실패가 전체를 멈추지 않음.
- LLM 어댑터는 로컬 Ollama 1순위(build_llm_client).
- 매칭은 min_match_score 이상이고 is_eligible=True 인 건만 발송 대상.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import sys
import yaml
from pathlib import Path
from datetime import datetime

from .common.logging_config import get_logger, setup_logging
from .common.schemas import resolve_env_refs, RawNotice
from .common.llm import build_llm_client
from .common.constants import DEFAULT_MIN_MATCH_SCORE
from .common.db import GrantDatabase
from .collector.multi_collector import MultiPortalCollector
from .collector.year_filter import YearFilter
from .deduplicator.dedup import CrossPortalDeduplicator
from .parser.doc_parser import AttachmentAndRfpParser
from .matcher.eligibility_matcher import EligibilityMatcher
from .matcher.hybrid_matcher import HybridMatcher
from .notifier.email_notifier import GrantEmailNotifier

logger = get_logger("main")


def _load_yaml(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    # ${VAR} 참조를 환경변수로 치환(비밀정보 외부화)
    return yaml.safe_load(resolve_env_refs(text)) or {}


def _canonical_id(notice) -> str:
    """중복제거 후 동일 공고의 안정적 키(소스 무관). portal_id + md5(제목+본문)."""
    sig = hashlib.md5(
        f"{notice.portal_id}|{notice.title}|{notice.body_text}".encode("utf-8")
    ).hexdigest()[:12]
    return f"{notice.portal_id}:{sig}"


async def run_daily_pipeline(root_dir: Path, llm_client=None) -> dict:
    root_dir = Path(root_dir)
    master_portals = _load_yaml(root_dir / "config/master_portals.yaml")
    mail_cfg = _load_yaml(root_dir / "config/mail_config.yaml")

    collector = MultiPortalCollector(download_root=root_dir / "storage/downloads")
    deduplicator = CrossPortalDeduplicator()
    parser = AttachmentAndRfpParser()
    if "StubMatcher" in str(EligibilityMatcher):
        matcher = EligibilityMatcher()
    else:
        matcher = HybridMatcher(llm_client=llm_client, offline=(llm_client is None and bool(os.environ.get("LLM_OFFLINE"))))
    notifier = GrantEmailNotifier(smtp_cfg=mail_cfg)

    # REQ-009 · 연도 필터 게이트 (config/year_filter.yaml; env TARGET_YEAR 로 오버라이드 가능)
    year_cfg = _load_yaml(root_dir / "config/year_filter.yaml")
    yf = year_cfg.get("year_filter", {})
    yf["target_year"] = int(os.environ.get("TARGET_YEAR", yf.get("target_year", 2026)))
    year_filter = YearFilter.from_config(yf)

    # REQ-003 · DB 영속화 + 중복발송 방지
    db = GrantDatabase(root_dir / "storage" / "grant_master.db")
    db.ensure_schema()

    items_dir = root_dir / "items"
    summary = {"run_at": datetime.now().isoformat(), "items": []}

    if not items_dir.exists():
        logger.error("items/ 디렉터리가 없습니다: %s", items_dir)
        return summary

    for item_folder in sorted(items_dir.iterdir()):
        if not item_folder.is_dir():
            continue
        profile_path = item_folder / "profile.yaml"
        proposal_path = item_folder / "proposal.md"
        if not (profile_path.exists() and proposal_path.exists()):
            logger.warning("item 프로파일/제안서 미비 -> 건너뜀: %s", item_folder.name)
            continue

        item_summary = {
            "item_id": item_folder.name,
            "collected": 0,
            "unique": 0,
            "year_dropped": 0,
            "year_kept": 0,
            "evaluated": 0,
            "persistence": 0,
            "matched": 0,
            "dispatched": 0,
            "skipped_dup": 0,
            "errors": 0,
            "matched_details": [],
        }
        try:
            profile = _load_yaml(profile_path)
            proposal_md = proposal_path.read_text(encoding="utf-8")
            min_score = profile.get("domain_routing", {}).get("min_match_score", DEFAULT_MIN_MATCH_SCORE)

            # 1) 수집
            raw_notices = await collector.collect_for_item(profile, master_portals)
            item_summary["collected"] = len(raw_notices)

            # 2) 중복 제거
            unique_notices = deduplicator.deduplicate(raw_notices)
            item_summary["unique"] = len(unique_notices)

            # 2.5) REQ-009 · 2026 전용 연도 필터 (정제 계층 집중 게이트)
            year_kept = year_filter.apply(unique_notices)
            item_summary["year_kept"] = len(year_kept)
            item_summary["year_dropped"] = len(unique_notices) - len(year_kept)

            # 2.6) 평가 대상 공고 풀 구성: 신규 수집 공고 + DB 기보관 2026 공고 (신규 아이템 매칭 보장)
            eval_notices_map = {}
            for n in year_kept:
                cid = _canonical_id(n)
                eval_notices_map[cid] = (n, cid)

            # DB의 2026 공고 풀 병합 (외부 수집이 0건이어도 기존 2026 공고들에 대한 평가 보장)
            try:
                db_rows = db.list_announcements(year_filter="2026", limit=500)
                for r in db_rows:
                    cid = r.get("canonical_id") or ""
                    if cid and cid not in eval_notices_map:
                        rn = RawNotice(
                            portal_id=r.get("source_portal", "db"),
                            title=r.get("title", ""),
                            organization=r.get("organization", ""),
                            ministry=r.get("ministry", ""),
                            deadline=r.get("deadline", ""),
                            detail_url=r.get("detail_url", ""),
                            body_text=r.get("body_text", "") or "",
                        )
                        eval_notices_map[cid] = (rn, cid)
            except Exception as e:
                logger.warning("DB 공고 풀 병합 실패(degrade): %s", e)

            item_summary["evaluated"] = len(eval_notices_map)
            matched_candidates = []   # (notice, eval_res, canonical_id, rfp_id)
            seen_in_item: set = set()

            for canonical_id, (notice, _) in eval_notices_map.items():
                # 3) RFP 파싱/분할
                try:
                    rfp_chunks = parser.extract_and_split_rfps(notice.downloaded_files)
                except Exception as e:
                    logger.exception("RFP 파싱 실패[%s]: %s", notice.title, e)
                    item_summary["errors"] += 1
                    rfp_chunks = []
                is_new_parsed = bool(rfp_chunks)
                if not rfp_chunks:
                    existing_chunks = db.get_rfp_chunks(canonical_id)
                    if existing_chunks:
                        rfp_chunks = existing_chunks
                    else:
                        rfp_chunks = [
                            {"rfp_number": "단일공고", "rfp_title": notice.title,
                             "content": notice.body_text or notice.title}
                        ]

                # 3.5) DB 영속화(announcements, REQ-003)
                if db.upsert_announcement(notice, canonical_id):
                    item_summary["persistence"] += 1

                # 4) 자격 검증 + 역질문 (한 공고는 최고점 chunk 1건만 채택)
                for ch_idx, chunk in enumerate(rfp_chunks):
                    rfp_id = chunk.get("rfp_id") or f"{canonical_id}::{chunk.get('rfp_number','single')}#{ch_idx}"
                    if is_new_parsed:
                        db.upsert_rfp_chunk(chunk, canonical_id, rfp_id)
                    try:
                        eval_res = matcher.evaluate_notice(
                            profile, proposal_md, notice, chunk
                        )
                    except Exception as e:
                        logger.exception("매칭 평가 예외[%s]: %s", notice.title, e)
                        item_summary["errors"] += 1
                        continue
                    if eval_res.is_eligible and eval_res.match_score >= min_score:
                        if canonical_id not in seen_in_item:
                            seen_in_item.add(canonical_id)
                            matched_candidates.append((notice, eval_res, canonical_id, rfp_id))

            item_summary["matched"] = len(matched_candidates)
            item_summary["matched_details"] = [
                {
                    "canonical_id": sid,
                    "title": n.title,
                    "score": er.match_score,
                    "rfp_id": rid,
                }
                for n, er, sid, rid in matched_candidates
            ]

            # 5) 중복발송 방지(REQ-005) + 발송 + DB 기록(REQ-003)
            final_for_email = []
            for notice, eval_res, sid, rid in matched_candidates:
                # is_dispatched: True=이미 발송 / False=새건 / None=DB degrade
                dup = db.is_dispatched(item_summary["item_id"], sid, rid)
                if dup is not False:
                    item_summary["skipped_dup"] += 1
                    if dup is None:
                        logger.warning("DB degrade -> 발송 건너뜀(%s/%s)", sid, rid)
                    continue

                # 신규 매칭 건은 DB에 즉시 영속화 (이메일 발송 여부와 무관하게 시스템 매칭 이력 보장)
                if db.record_dispatch(item_summary["item_id"], sid, rid, eval_res.match_score):
                    item_summary["dispatched"] += 1
                final_for_email.append((notice, eval_res))

            if final_for_email:
                try:
                    notifier.send_item_digest(profile, final_for_email)
                except Exception as e:
                    logger.exception("이메일 발송 예외[%s]: %s", item_folder.name, e)
                    item_summary["errors"] += 1
        except Exception as e:
            logger.exception("item 처리 실패[%s]: %s (건너뜀)", item_folder.name, e)
            item_summary["errors"] += 1

        summary["items"].append(item_summary)
        logger.info(
            "완료 item=%s collected=%d unique=%d year_kept=%d evaluated=%d dropped=%d persisted=%d "
            "matched=%d dispatched=%d skipped_dup=%d errors=%d",
            item_folder.name,
            item_summary["collected"],
            item_summary["unique"],
            item_summary["year_kept"],
            item_summary["evaluated"],
            item_summary["year_dropped"],
            item_summary["persistence"],
            item_summary["matched"],
            item_summary["dispatched"],
            item_summary["skipped_dup"],
            item_summary["errors"],
        )

    logger.info("일일 파이프라인 종료: %s", summary)
    return summary


def main() -> None:
    setup_logging()
    if "--web" in sys.argv:
        from .web.app import run_server
        port = 8080
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                try:
                    port = int(sys.argv[i + 1])
                except ValueError:
                    pass
        if os.environ.get("WEB_PORT"):
            try:
                port = int(os.environ["WEB_PORT"])
            except ValueError:
                pass
        logger.info("웹 관리자 대시보드 서버 시작: http://127.0.0.1:%s", port)
        run_server(host="127.0.0.1", port=port)
        return

    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        root_dir = Path(sys.argv[1])
    elif Path("config/master_portals.yaml").exists():
        root_dir = Path(".")
    else:
        root_dir = Path("gov-grant-automation")
    llm = None
    if os.environ.get("LLM_OFFLINE") != "1":
        try:
            llm = build_llm_client()
            # 사전 워밍업: 모델 메모리 상주(keep_alive=1h)로 첫 요청 지연/재로드 방지
            if os.environ.get("WARMUP", "1") != "0" and hasattr(llm, "warmup"):
                llm.warmup()
        except Exception as e:
            logger.warning("LLM 클라이언트 실패 -> offline degrade: %s", e)
    asyncio.run(run_daily_pipeline(root_dir, llm_client=llm))


if __name__ == "__main__":
    main()

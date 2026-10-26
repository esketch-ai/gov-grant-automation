"""
REQ-003 · SQLite DB 영속화 계층 (박준호/정민재 담당)

파이프라인 단계별 영속화 + 중복발송 방지(REQ-005 연계)를 위한 안전 degrade 레퍼런스.
- announcements            : 수집·중복제거 후 canonical 공고 영속화
- rfp_chunks               : 분할된 RFP 청크 영속화
- dispatch_history         : 발송 건(중복발송 방지, UNIQUE(item_id,canonical_id,rfp_id))

설계 원칙(최은정/박준호):
- DB 연동 실패는 **파이프라인을 멈추지 않는다**. 모든 공개 메서드는 try/except로 감싸
  예외 시 WARN 로그 + 무해한 반환값(degrade sentinel)을 제공한다.
- 스키마는 idempotent(CREATE TABLE IF NOT EXISTS)으로 db.py가 스스로 보강한다.
"""
from __future__ import annotations

import re
import json
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

from .logging_config import get_logger
from .schemas import RawNotice

logger = get_logger("db")


class GrantDatabase:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)

    # ------------------------------------------------------------------ schema
    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def ensure_schema(self) -> None:
        """idempotent 스키마 보강(스스로 self-sufficient하게)."""
        try:
            with self._connect() as conn:
                conn.executescript(
                    """
                CREATE TABLE IF NOT EXISTS announcements (
                    canonical_id TEXT PRIMARY KEY,
                    official_notice_no TEXT,
                    title TEXT NOT NULL,
                    organization TEXT,
                    ministry TEXT,
                    deadline TEXT,
                    source_portal TEXT,
                    detail_url TEXT,
                    local_attachment_dir TEXT,
                    target_year INTEGER DEFAULT 2026,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS rfp_chunks (
                    rfp_id TEXT PRIMARY KEY,
                    canonical_id TEXT,
                    rfp_number TEXT,
                    rfp_title TEXT,
                    target_trl TEXT,
                    budget_info TEXT,
                    markdown_content TEXT,
                    FOREIGN KEY(canonical_id) REFERENCES announcements(canonical_id)
                );
                CREATE TABLE IF NOT EXISTS site_selectors (
                    domain TEXT PRIMARY KEY,
                    row_selector TEXT,
                    title_selector TEXT,
                    date_selector TEXT,
                    link_selector TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS dispatch_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id TEXT,
                    canonical_id TEXT,
                    rfp_id TEXT,
                    match_score INTEGER,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(item_id, canonical_id, rfp_id)
                );
                CREATE TABLE IF NOT EXISTS company_profile (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    company_name TEXT,
                    biz_reg_no TEXT,
                    opened_date TEXT,
                    founder_birth TEXT,
                    founder_gender TEXT,
                    address TEXT,
                    debt_ratio_pct REAL,
                    has_rnd_lab INTEGER DEFAULT 0,
                    is_capital_impaired INTEGER DEFAULT 0,
                    has_tax_arrears INTEGER DEFAULT 0,
                    current_pi_projects INTEGER DEFAULT 0,
                    current_member_projects INTEGER DEFAULT 0,
                    registered_patents_count INTEGER DEFAULT 0,
                    available_cash_fund INTEGER DEFAULT 0,
                    prior_grant_history TEXT,
                    certifications TEXT,
                    tags TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
                )
                # company_profile 단일행(id=1) 기본행 확보(프로필 부재 시 빈 상태 반환 방지)
                conn.execute("INSERT OR IGNORE INTO company_profile (id) VALUES (1);")
                # 기존 테이블 마이그레이션: target_year 컬럼 유무 점검 및 추가
                cols = [r["name"] for r in conn.execute("PRAGMA table_info(announcements)").fetchall()]
                if "target_year" not in cols:
                    conn.execute("ALTER TABLE announcements ADD COLUMN target_year INTEGER DEFAULT 2026;")
                conn.commit()
        except Exception as e:
            logger.warning("DB 스키마 보강 실패(degrade): %s", e)

    # ------------------------------------------------------------------ 영속화
    def upsert_announcement(self, notice: RawNotice, canonical_id: str,
                            official_notice_no: str = "", target_year: Optional[int] = None) -> bool:
        """
        canonical_id 기준으로 INSERT OR REPLACE. 실패 시 False(return)·파이프라인 미중단.
        target_year가 지정되지 않은 경우 공고 텍스트에서 4자리 연도를 자동 추정하여 저장.
        """
        try:
            detected_year = target_year
            if detected_year is None:
                text_to_search = f"{notice.title} {official_notice_no} {notice.deadline}"
                found_years = [int(y) for y in re.findall(r"\b(202\d)\b", text_to_search)]
                detected_year = max(found_years) if found_years else 2026

            with self._connect() as conn:
                cur = conn.execute(
                    """INSERT OR REPLACE INTO announcements
                       (canonical_id, official_notice_no, title, organization,
                        ministry, deadline, source_portal, detail_url, local_attachment_dir, target_year)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (
                        canonical_id,
                        official_notice_no,
                        notice.title,
                        notice.organization,
                        notice.ministry,
                        notice.deadline,
                        notice.portal_id,
                        notice.detail_url,
                        str(notice.downloaded_files[0]) if notice.downloaded_files else "",
                        detected_year,
                    ),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.warning("upsert_announcement 실패[%s]: %s", canonical_id, e)
            return False

    def upsert_rfp_chunk(self, rfp_chunk: dict, canonical_id: str, rfp_id: str) -> bool:
        try:
            with self._connect() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO rfp_chunks
                       (rfp_id, canonical_id, rfp_number, rfp_title, target_trl,
                        budget_info, markdown_content)
                       VALUES (?,?,?,?,?,?,?)""",
                    (
                        rfp_id,
                        canonical_id,
                        rfp_chunk.get("rfp_number", ""),
                        rfp_chunk.get("rfp_title", ""),
                        rfp_chunk.get("target_trl", ""),
                        rfp_chunk.get("budget_info", ""),
                        rfp_chunk.get("content", ""),
                    ),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.warning("upsert_rfp_chunk 실패[%s]: %s", rfp_id, e)
            return False

    # ------------------------------------------------------------------ 발송 통제
    def is_dispatched(self, item_id: str, canonical_id: str, rfp_id: str) -> Optional[bool]:
        """
        이미 발송됐는지 확인.
        - True/False: DB 확인 결과(확정)
        - None: DB 접근 실패(degrade) — 호출측은 None 시 '안보존적으로 발송 건너뜀'
        """
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT 1 FROM dispatch_history WHERE item_id=? AND canonical_id=? AND rfp_id=?",
                    (item_id, canonical_id, rfp_id),
                ).fetchone()
            return row is not None
        except Exception as e:
            logger.warning("is_dispatched 확인 실패(degrade): %s", e)
            return None

    def record_dispatch(self, item_id: str, canonical_id: str, rfp_id: str,
                        match_score: int) -> Optional[bool]:
        """
        발송 기록. **새로운 건이면 True, 중복이면 False(DB UNIQUE제약+재확인).**
        DB 실패 시 None(degrade).
        """
        # 선재확인으로 중복 차단(UNIQUE 제약과 이중 안전장치)
        exists = self.is_dispatched(item_id, canonical_id, rfp_id)
        if exists is True:
            return False
        if exists is None:
            return None  # 확정 불가: degrade sentinel
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO dispatch_history (item_id, canonical_id, rfp_id, match_score) "
                    "VALUES (?,?,?,?)",
                    (item_id, canonical_id, rfp_id, match_score),
                )
                conn.commit()
            return True
        except Exception as e:
            # UNIQUE 제약 충돌(동시재입력)이면 중복으로 취급
            logger.warning("record_dispatch 실패[%s/%s]: %s", canonical_id, rfp_id, e)
            if "UNIQUE" in str(e):
                return False
            return None

    # ------------------------------------------------------------------ 조회
    def count_dispatched(self, item_id: Optional[str] = None) -> int:
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT COUNT(*) FROM dispatch_history"
                    + (" WHERE item_id=?" if item_id else ""),
                    (item_id,) if item_id else (),
                ).fetchone()
                return int(row[0]) if row else 0
        except Exception as e:
            logger.warning("count_dispatched 실패: %s", e)
            return 0

    # ------------------------------------------------------------------ 사이트 셀렉터 자가치유
    def get_site_selector(self, domain: str) -> Optional[dict]:
        """도메인별 크롤링 셀렉터 조회."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT domain, row_selector, title_selector, date_selector, link_selector, updated_at "
                    "FROM site_selectors WHERE domain=?",
                    (domain,),
                ).fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.warning("get_site_selector 실패[%s]: %s", domain, e)
            return None

    def upsert_site_selector(
        self,
        domain: str,
        row_selector: str,
        title_selector: str,
        date_selector: str,
        link_selector: str,
    ) -> bool:
        """자가치유된 최신 셀렉터 저장/갱신."""
        try:
            with self._connect() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO site_selectors
                       (domain, row_selector, title_selector, date_selector, link_selector, updated_at)
                       VALUES (?,?,?,?,?,CURRENT_TIMESTAMP)""",
                    (domain, row_selector, title_selector, date_selector, link_selector),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.warning("upsert_site_selector 실패[%s]: %s", domain, e)
            return False

    def list_site_selectors(self) -> List[dict]:
        """전체 등록된 사이트 셀렉터 목록 조회."""
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "SELECT domain, row_selector, title_selector, date_selector, link_selector, updated_at "
                    "FROM site_selectors ORDER BY updated_at DESC"
                )
                return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            logger.warning("list_site_selectors 실패: %s", e)
            return []

    # ------------------------------------------------------------------ 사업주 프로필 (REQ-020)
    _CP_JSON_COLS = ("prior_grant_history", "certifications", "tags")
    _CP_BOOL_COLS = ("has_rnd_lab", "is_capital_impaired", "has_tax_arrears")
    _CP_INT_COLS = (
        "current_pi_projects", "current_member_projects",
        "registered_patents_count", "available_cash_fund",
    )

    def _decode_profile_row(self, row: sqlite3.Row) -> dict:
        """sqlite 행 -> Python dict( JSON열 해독 / boolean·int 형식 환원)."""
        row = dict(row)
        for col in self._CP_JSON_COLS:
            raw = row.get(col)
            if not raw:
                row[col] = []
                continue
            try:
                row[col] = json.loads(raw)
            except Exception:
                row[col] = []
        for col in self._CP_BOOL_COLS:
            row[col] = bool(row.get(col))
        for col in self._CP_INT_COLS:
            v = row.get(col)
            row[col] = int(v) if v else 0
        return row

    def get_company_profile(self) -> Optional[dict]:
        """
        현재 저장된 사업주 프로필(id=1) 조회.
        - dict: 저장된 프로필(JSON 해독, boolean/int 환원)
        - None: DB 접근 실패(degrade) — 호출측은 빈 프로필 폴백 사용.
        (빈 기본행은 항상 존재 하므로 '미설정' 상태를 company_name로 구분.)
        """
        try:
            with self._connect() as conn:
                row = conn.execute("SELECT * FROM company_profile WHERE id=1").fetchone()
                if row is None:
                    return None
                return self._decode_profile_row(row)
        except Exception as e:
            logger.warning("get_company_profile 실패(degrade): %s", e)
            return None

    def upsert_company_profile(self, data: dict) -> bool:
        """
        사업주 프로필 저장/갱신(단일행 id=1 INSERT OR REPLACE).
        data는 company_profile 컬럼의 부분 집합 허용. 누락값은 기본값으로 보강.
        실패 시 False(return)·파이프라인 미중단(degrade).
        """
        if not isinstance(data, dict):
            logger.warning("upsert_company_profile: 타입 불일치 %s", type(data).__name__)
            return False

        def _g(col, default=None):
            return data.get(col, default)

        # JSON/boolean/int 정규화
        prior = _g("prior_grant_history", []) or []
        certs = _g("certifications", []) or []
        tags = _g("tags", []) or []
        if isinstance(prior, str):
            prior = [x.strip() for x in prior.split(",") if x.strip()]
        if isinstance(certs, str):
            certs = [x.strip() for x in certs.split(",") if x.strip()]
        if isinstance(tags, str):
            tags = [x.strip() for x in tags.split(",") if x.strip()]

        def _to_int(v):
            try:
                return int(v) if v not in (None, "", False) else 0
            except (ValueError, TypeError):
                return 0

        row = {
            "company_name": (str(_g("company_name", "") or "")).strip(),
            "biz_reg_no": (str(_g("biz_reg_no", "") or "")).strip(),
            "opened_date": (str(_g("opened_date", "") or "")).strip(),
            "founder_birth": (str(_g("founder_birth", "") or "")).strip(),
            "founder_gender": (str(_g("founder_gender", "F") or "F")).strip().upper()[:1] or "F",
            "address": (str(_g("address", "") or "")).strip(),
            "debt_ratio_pct": (float(_g("debt_ratio_pct")) if _g("debt_ratio_pct") not in (None, "", False) else None),
            "has_rnd_lab": 1 if _g("has_rnd_lab") else 0,
            "is_capital_impaired": 1 if _g("is_capital_impaired") else 0,
            "has_tax_arrears": 1 if _g("has_tax_arrears") else 0,
            "current_pi_projects": _to_int(_g("current_pi_projects", 0)),
            "current_member_projects": _to_int(_g("current_member_projects", 0)),
            "registered_patents_count": _to_int(_g("registered_patents_count", 0)),
            "available_cash_fund": _to_int(_g("available_cash_fund", 0)),
            "prior_grant_history": json.dumps(prior, ensure_ascii=False),
            "certifications": json.dumps(certs, ensure_ascii=False),
            "tags": json.dumps(tags, ensure_ascii=False),
        }

        try:
            with self._connect() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO company_profile
                       (id, company_name, biz_reg_no, opened_date, founder_birth, founder_gender,
                        address, debt_ratio_pct, has_rnd_lab, is_capital_impaired, has_tax_arrears,
                        current_pi_projects, current_member_projects, registered_patents_count,
                        available_cash_fund, prior_grant_history, certifications, tags, updated_at)
                       VALUES (1,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
                    (
                        row["company_name"], row["biz_reg_no"], row["opened_date"],
                        row["founder_birth"], row["founder_gender"], row["address"],
                        row["debt_ratio_pct"], row["has_rnd_lab"],
                        row["is_capital_impaired"], row["has_tax_arrears"],
                        row["current_pi_projects"], row["current_member_projects"],
                        row["registered_patents_count"], row["available_cash_fund"],
                        row["prior_grant_history"], row["certifications"], row["tags"],
                    ),
                )
                conn.commit()
            return True
        except Exception as e:
            logger.warning("upsert_company_profile 실패(degrade): %s", e)
            return False

    def clear_company_profile(self) -> bool:
        """사업주 프로필 초기화(빈 기본행으로 리셋)."""
        try:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE company_profile SET company_name='', biz_reg_no='', opened_date='', "
                    "founder_birth='', founder_gender='F', address='', debt_ratio_pct=NULL, "
                    "has_rnd_lab=0, is_capital_impaired=0, has_tax_arrears=0, current_pi_projects=0, "
                    "current_member_projects=0, registered_patents_count=0, available_cash_fund=0, "
                    "prior_grant_history='[]', certifications='[]', tags='[]', updated_at=CURRENT_TIMESTAMP "
                    "WHERE id=1",
                )
                conn.commit()
            return True
        except Exception as e:
            logger.warning("clear_company_profile 실패(degrade): %s", e)
            return False

    # ------------------------------------------------------------------ 연도 거버넌스 및 통계
    def get_year_statistics(self) -> Dict[str, Any]:
        """연도별 공고 집계 및 2026 연도 거버넌스 무결성 지표 산출."""
        default_stats = {
            "total_announcements": 0,
            "year_2026_count": 0,
            "past_years_count": 0,
            "future_years_count": 0,
            "compliance_rate_pct": 100.0,
            "by_year": {},
            "by_portal": {},
        }
        try:
            with self._connect() as conn:
                cur = conn.execute("SELECT target_year, COUNT(*) as cnt FROM announcements GROUP BY target_year")
                by_year = {int(r["target_year"]): int(r["cnt"]) for r in cur.fetchall() if r["target_year"] is not None}

                cur = conn.execute("SELECT source_portal, COUNT(*) as cnt FROM announcements GROUP BY source_portal")
                by_portal = {str(r["source_portal"]): int(r["cnt"]) for r in cur.fetchall()}

                total = sum(by_year.values())
                y2026 = by_year.get(2026, 0)
                past = sum(cnt for yr, cnt in by_year.items() if yr < 2026)
                future = sum(cnt for yr, cnt in by_year.items() if yr > 2026)
                compliance = (y2026 / total * 100.0) if total > 0 else 100.0

                return {
                    "total_announcements": total,
                    "year_2026_count": y2026,
                    "past_years_count": past,
                    "future_years_count": future,
                    "compliance_rate_pct": round(compliance, 1),
                    "by_year": by_year,
                    "by_portal": by_portal,
                }
        except Exception as e:
            logger.warning("get_year_statistics 실패: %s", e)
            return default_stats

    def list_announcements(
        self,
        query: str = "",
        portal: str = "",
        year_filter: str = "all",
        limit: int = 100,
    ) -> List[dict]:
        """
        공고 목록 다중 조건 조회 (검색어, 포털, 연도별 필터링 지원).
        year_filter 옵션:
        - 'all': 전체 공고
        - '2026': 2026년도 공고만 (target_year = 2026)
        - 'past': 2025년 이하 과거 공고 (target_year < 2026)
        - 'future': 2027년 이상 공고 (target_year > 2026)
        """
        try:
            with self._connect() as conn:
                sql = "SELECT * FROM announcements WHERE 1=1"
                params: list = []
                if query:
                    sql += " AND (title LIKE ? OR ministry LIKE ? OR organization LIKE ?)"
                    q_like = f"%{query}%"
                    params.extend([q_like, q_like, q_like])
                if portal:
                    sql += " AND source_portal = ?"
                    params.append(portal)
                if year_filter == "2026":
                    sql += " AND target_year = 2026"
                elif year_filter == "past":
                    sql += " AND target_year < 2026"
                elif year_filter == "future":
                    sql += " AND target_year > 2026"

                sql += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)

                cur = conn.execute(sql, params)
                return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            logger.warning("list_announcements 실패: %s", e)
            return []

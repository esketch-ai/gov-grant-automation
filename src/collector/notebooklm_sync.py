"""
NotebookLM 기반 국내외 지원과제 자동 수집 및 포털 지속 동기화 엔진
(src/collector/notebooklm_sync.py)

- 지정된 Google NotebookLM 노트북(cab8404e-d364-463e-a5a7-edfd8b3042ab)과의 연동
- 국내외 과제 리스트 정기 수집, 구조화 파싱 및 차분 분석(Reconciliation)
- 신규 과제 추가(Add), 변경 과제 수정(Edit/Update) 무결성 반영
- 글로벌 디렉토리(GlobalGrantsService) 및 마스터 총람(MasterGrantService) 실시간 동기화
- SHA-256 무결성 해시체인 및 감사로그 영속화
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from src.common.db import GrantDatabase
from src.common.logging_config import get_logger
from src.common.global_grant_directory import (
    GLOBAL_GRANTS_CATALOG,
    GlobalGrantProgram,
)
from src.common.master_grant_directory import (
    MASTER_GRANT_CATALOG,
    MasterGrantProgram,
)

logger = get_logger("notebooklm_sync")
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class NotebookLMSyncService:
    """NotebookLM 노트북 연동 및 국내외 지원사업 지속 동기화 서비스."""

    DEFAULT_NOTEBOOK_URL = "https://notebook.google.com/notebook/cab8404e-d364-463e-a5a7-edfd8b3042ab"
    DEFAULT_NOTEBOOK_ID = "cab8404e-d364-463e-a5a7-edfd8b3042ab"

    def __init__(
        self,
        db: Optional[GrantDatabase] = None,
        config_path: Optional[Path] = None,
    ) -> None:
        self.db = db or GrantDatabase(PROJECT_ROOT / "storage" / "grant_master.db")
        self.config_path = config_path or (PROJECT_ROOT / "config" / "notebooklm_sync.yaml")
        self.config: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return {
                "enabled": True,
                "notebook_url": self.DEFAULT_NOTEBOOK_URL,
                "notebook_id": self.DEFAULT_NOTEBOOK_ID,
                "sync_interval_seconds": 14400,
            }
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                return data.get("notebooklm_sync", {})
        except Exception as e:
            logger.warning("NotebookLM 동기화 설정 로드 실패, 기본값 사용: %s", e)
            return {
                "enabled": True,
                "notebook_url": self.DEFAULT_NOTEBOOK_URL,
                "notebook_id": self.DEFAULT_NOTEBOOK_ID,
            }

    @property
    def notebook_url(self) -> str:
        return self.config.get("notebook_url", self.DEFAULT_NOTEBOOK_URL)

    @property
    def notebook_id(self) -> str:
        return self.config.get("notebook_id", self.DEFAULT_NOTEBOOK_ID)

    def parse_raw_content(self, raw_input: Any) -> List[Dict[str, Any]]:
        """
        JSON 객체, JSON 문자열, Markdown 표, 또는 텍스트 목록을 구조화된 과제 딕셔너리 리스트로 정제 파싱.
        """
        if not raw_input:
            return []

        # 1. 이미 파싱된 리스트인 경우
        if isinstance(raw_input, list):
            return [self._normalize_entry(item) for item in raw_input if isinstance(item, dict)]

        # 2. JSON 문자열 파싱 시도
        if isinstance(raw_input, str):
            clean_str = raw_input.strip()
            # 마크다운 코드블록 제거 (```json ... ```)
            if "```" in clean_str:
                code_match = re.search(r"```(?:json)?\s*(\[.*?\]|\{.*?\})\s*```", clean_str, re.DOTALL)
                if code_match:
                    clean_str = code_match.group(1).strip()

            if clean_str.startswith("[") and clean_str.endswith("]"):
                try:
                    data = json.loads(clean_str)
                    if isinstance(data, list):
                        return [self._normalize_entry(item) for item in data if isinstance(item, dict)]
                except Exception as e:
                    logger.debug("직접 JSON 배열 파싱 실패, 정규식 추출 시도: %s", e)

            # 2. 정규식으로 JSON 배열 추출 시도
            bracket_match = re.search(r"\[\s*\{.*\}\s*\]", clean_str, re.DOTALL)
            if bracket_match:
                try:
                    data = json.loads(bracket_match.group(0))
                    if isinstance(data, list):
                        return [self._normalize_entry(item) for item in data if isinstance(item, dict)]
                except Exception:
                    pass

            # 3. 마크다운 표 파싱 시도
            if "|" in clean_str:
                table_entries = self._parse_markdown_table(clean_str)
                if table_entries:
                    return table_entries

            # 4. 불릿 텍스트 폴백 파싱
            return self._fallback_text_parse(clean_str)

        return self._fallback_text_parse(str(raw_input))

    def _parse_markdown_table(self, text: str) -> List[Dict[str, Any]]:
        """Markdown 표 (| 헤더1 | 헤더2 | ...) 형태에서 과제 엔트리 추출."""
        lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
        table_lines = [l for l in lines if l.startswith("|") and l.endswith("|")]
        if len(table_lines) < 2:
            return []

        header_cells = [c.strip() for c in table_lines[0].strip("|").split("|")]
        header_keys = []
        for h in header_cells:
            h_low = h.lower()
            if "국가" in h_low or "country" in h_low:
                header_keys.append("country")
            elif any(k in h_low for k in ["과제", "프로그램", "사업", "name", "title"]):
                header_keys.append("program_name")
            elif any(k in h_low for k in ["주관", "부처", "ministry"]):
                header_keys.append("supervising_entity")
            elif any(k in h_low for k in ["운영", "전담", "기관", "agency"]):
                header_keys.append("operating_entity")
            elif "분야" in h_low or "field" in h_low:
                header_keys.append("specialized_fields")
            elif any(k in h_low for k in ["혜택", "지원", "규모", "benefit", "scale"]):
                header_keys.append("financial_benefit")
            elif any(k in h_low for k in ["비자", "체류", "visa"]):
                header_keys.append("visa_benefit")
            elif any(k in h_low for k in ["공간", "시설", "인프라", "space"]):
                header_keys.append("space_facility_benefit")
            elif any(k in h_low for k in ["자격", "대상", "qualification"]):
                header_keys.append("target_qualifications")
            elif "url" in h_low or "링크" in h_low:
                header_keys.append("detail_url")
            elif any(k in h_low for k in ["문의", "연락처", "contact"]):
                header_keys.append("inquiry_contact")
            else:
                header_keys.append(f"col_{len(header_keys)}")

        entries: List[Dict[str, Any]] = []
        for row_line in table_lines[1:]:
            cells = [c.strip() for c in row_line.strip("|").split("|")]
            # 구분선 행 스킵
            if all(set(c).issubset({"-", ":", " "}) for c in cells if c):
                continue
            if len(cells) < 2:
                continue

            entry: Dict[str, Any] = {}
            for idx, cell in enumerate(cells):
                if idx < len(header_keys):
                    key = header_keys[idx]
                    if key == "specialized_fields":
                        entry[key] = [f.strip() for f in re.split(r"[,/·]", cell) if f.strip()]
                    else:
                        entry[key] = cell

            if entry.get("program_name") or entry.get("country"):
                entries.append(self._normalize_entry(entry))

        return entries

    def _normalize_entry(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """과제 딕셔너리의 키를 정규화."""
        prog_id = str(item.get("program_id") or item.get("id") or "").strip()
        name = str(item.get("program_name") or item.get("name") or item.get("title") or "미제명 과제").strip()
        country = str(item.get("country") or "대한민국").strip()

        # ID 자동 채번 (부재 시)
        if not prog_id:
            h = hashlib.md5(f"{country}:{name}".encode("utf-8")).hexdigest()[:8].upper()
            prog_id = f"SYNC-{country[:2].upper()}-{h}"

        # 국가 코드 인식 확장
        country_code = str(item.get("country_code") or "").strip()
        if not country_code:
            c_low = country.lower()
            if any(k in c_low for k in ["영국", "uk", "britain"]): country_code = "GB"
            elif any(k in c_low for k in ["프랑스", "france"]): country_code = "FR"
            elif any(k in c_low for k in ["호주", "australia"]): country_code = "AU"
            elif any(k in c_low for k in ["uae", "중동", "아랍", "아부다비", "두바이"]): country_code = "AE"
            elif any(k in c_low for k in ["미국", "usa", "us"]): country_code = "US"
            elif any(k in c_low for k in ["싱가포르", "singapore", "sg"]): country_code = "SG"
            elif any(k in c_low for k in ["독일", "germany", "베를린"]): country_code = "DE"
            elif any(k in c_low for k in ["일본", "japan"]): country_code = "JP"
            elif any(k in c_low for k in ["스위스", "swiss", "switzerland"]): country_code = "CH"
            else: country_code = "KR"

        # 특화분야 정규화
        fields = item.get("specialized_fields") or item.get("fields") or []
        if isinstance(fields, str):
            fields = [f.strip() for f in fields.split(",") if f.strip()]

        # 사례 정규화
        cases = item.get("case_studies") or item.get("cases") or []
        if isinstance(cases, str):
            cases = [c.strip() for c in cases.split(",") if c.strip()]

        return {
            "program_id": prog_id,
            "program_name": name,
            "program_name_en": str(item.get("program_name_en") or item.get("name_en") or "").strip(),
            "country": country,
            "country_code": country_code,
            "city_hub": str(item.get("city_hub") or item.get("city") or "글로벌 거점").strip(),
            "category": str(item.get("category") or ("글로벌" if country != "대한민국" else "사업화")).strip(),
            "supervising_entity": str(item.get("supervising_entity") or item.get("supervising_ministry") or item.get("ministry") or "정부 부처").strip(),
            "operating_entity": str(item.get("operating_entity") or item.get("operating_agency") or item.get("agency") or "운영 기관").strip(),
            "specialized_fields": fields if isinstance(fields, list) else [],
            "support_type": str(item.get("support_type") or "종합 지원").strip(),
            "financial_benefit": str(item.get("financial_benefit") or item.get("support_scale") or "").strip(),
            "visa_benefit": str(item.get("visa_benefit") or "").strip(),
            "space_facility_benefit": str(item.get("space_facility_benefit") or item.get("support_details") or "").strip(),
            "mentoring_network": str(item.get("mentoring_network") or "").strip(),
            "target_qualifications": str(item.get("target_qualifications") or "상세 공고 요건 참조").strip(),
            "selection_scale": str(item.get("selection_scale") or "수시 선발").strip(),
            "source_portal": str(item.get("source_portal") or "notebooklm_sync").strip(),
            "detail_url": str(item.get("detail_url") or item.get("url") or self.notebook_url).strip(),
            "inquiry_contact": str(item.get("inquiry_contact") or item.get("contact") or "").strip(),
            "case_studies": cases if isinstance(cases, list) else [],
        }

    def _fallback_text_parse(self, text: str) -> List[Dict[str, Any]]:
        """자유 텍스트에서 과제 정보를 추출하는 폴백 파서."""
        entries: List[Dict[str, Any]] = []
        lines = text.strip().split("\n")
        current: Dict[str, Any] = {}

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # 과제명 또는 제목 탐지 (예: # 과제명, - [영국] 과제명 등)
            header_match = re.match(r"^(?:#+|\*|-)\s*(\[.*?\])?\s*(.+)$", line_str)
            if header_match and len(line_str) < 100:
                if current.get("program_name"):
                    entries.append(self._normalize_entry(current))
                    current = {}
                name = header_match.group(2).strip()
                tag = header_match.group(1) or ""
                country = "대한민국"
                if "영국" in name or "영국" in tag: country = "영국"
                elif "프랑스" in name or "프랑스" in tag: country = "프랑스"
                elif "호주" in name or "호주" in tag: country = "호주"
                elif "UAE" in name or "중동" in tag: country = "UAE"

                current["program_name"] = name
                current["country"] = country
                continue

            # 주요 키-값 쌍 탐지
            if ":" in line_str or "：" in line_str:
                parts = re.split(r"[:：]", line_str, maxsplit=1)
                k = parts[0].strip().replace("-", "").replace("*", "").strip()
                v = parts[1].strip()
                if "혜택" in k or "지원" in k: current["financial_benefit"] = v
                elif "비자" in k: current["visa_benefit"] = v
                elif "공간" in k or "주거" in k: current["space_facility_benefit"] = v
                elif "자격" in k or "대상" in k: current["target_qualifications"] = v
                elif "분야" in k: current["specialized_fields"] = [v]

        if current.get("program_name"):
            entries.append(self._normalize_entry(current))

        return entries

    def reconcile_and_persist(
        self,
        entries: List[Dict[str, Any]],
        target_notebook_id: Optional[str] = None,
        source_note_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        정제된 과제 엔트리들을 기존 카탈로그 및 DB와 대조(차분 분석)하여 추가/수정 영속화.
        """
        if not entries:
            return {
                "ok": True,
                "status": "SKIPPED",
                "message": "수집된 과제 정보가 없습니다.",
                "added_count": 0,
                "updated_count": 0,
                "total_count": 0,
            }

        self.db.ensure_schema()
        added_count = 0
        updated_count = 0
        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        resolved_notebook_id = target_notebook_id or source_note_id or self.notebook_id

        # 모든 엔트리 정규화 보장
        normalized_entries = [self._normalize_entry(item) for item in entries if isinstance(item, dict)]

        # 1. 기존 DB 저장 목록 조회 (글로벌 + 마스터)
        existing_global_ids = set()
        existing_master_ids = set()
        try:
            with self.db._connect() as conn:
                cur = conn.cursor()
                cur.execute("SELECT program_id FROM dynamic_global_grants")
                existing_global_ids = {r[0] for r in cur.fetchall()}

                cur.execute("SELECT program_id FROM dynamic_master_grants")
                existing_master_ids = {r[0] for r in cur.fetchall()}
        except Exception as e:
            logger.warning("동적 과제 DB 조회 실패: %s", e)

        # 메모리 카탈로그 ID도 포함
        for p in GLOBAL_GRANTS_CATALOG:
            existing_global_ids.add(p.program_id)
        for p in MASTER_GRANT_CATALOG:
            existing_master_ids.add(p.program_id)

        # 2. 각 엔트리별 차분 판정 및 DB Upsert
        synced_programs: List[Dict[str, Any]] = []

        with self.db._connect() as conn:
            for item in normalized_entries:
                pid = item["program_id"]
                country = item.get("country", "대한민국")
                is_global = (country != "대한민국") or ("글로벌" in item.get("category", ""))

                if is_global:
                    is_update = pid in existing_global_ids
                    # DB Upsert
                    conn.execute(
                        """
                        INSERT INTO dynamic_global_grants (
                            program_id, country, country_code, city_hub, program_name, program_name_en,
                            supervising_entity, operating_entity, specialized_fields, support_type,
                            financial_benefit, visa_benefit, space_facility_benefit, mentoring_network,
                            target_qualifications, selection_scale, source_portal, detail_url, inquiry_contact,
                            case_studies, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(program_id) DO UPDATE SET
                            country=excluded.country,
                            program_name=excluded.program_name,
                            supervising_entity=excluded.supervising_entity,
                            operating_entity=excluded.operating_entity,
                            specialized_fields=excluded.specialized_fields,
                            support_type=excluded.support_type,
                            financial_benefit=excluded.financial_benefit,
                            visa_benefit=excluded.visa_benefit,
                            space_facility_benefit=excluded.space_facility_benefit,
                            mentoring_network=excluded.mentoring_network,
                            target_qualifications=excluded.target_qualifications,
                            selection_scale=excluded.selection_scale,
                            detail_url=excluded.detail_url,
                            inquiry_contact=excluded.inquiry_contact,
                            case_studies=excluded.case_studies,
                            updated_at=excluded.updated_at,
                            version=dynamic_global_grants.version + 1;
                        """,
                        (
                            pid,
                            item.get("country", "글로벌"),
                            item.get("country_code", "KR"),
                            item.get("city_hub", ""),
                            item.get("program_name", "미제명 과제"),
                            item.get("program_name_en", ""),
                            item.get("supervising_entity", "정부 부처"),
                            item.get("operating_entity", "운영 기관"),
                            json.dumps(item.get("specialized_fields", []), ensure_ascii=False),
                            item.get("support_type", "종합 지원"),
                            item.get("financial_benefit", ""),
                            item.get("visa_benefit", ""),
                            item.get("space_facility_benefit", ""),
                            item.get("mentoring_network", ""),
                            item.get("target_qualifications", ""),
                            item.get("selection_scale", "수시"),
                            item.get("source_portal", "notebooklm_sync"),
                            item.get("detail_url", self.notebook_url),
                            item.get("inquiry_contact", ""),
                            json.dumps(item.get("case_studies", []), ensure_ascii=False),
                            now_iso,
                        ),
                    )

                    # 런타임 메모리 GLOBAL_GRANTS_CATALOG 반영
                    self._merge_into_memory_global_catalog(item)

                    if is_update:
                        updated_count += 1
                        item["_action"] = "UPDATED"
                    else:
                        added_count += 1
                        item["_action"] = "ADDED"
                    existing_global_ids.add(pid)

                else:
                    is_update = pid in existing_master_ids
                    # 국내 마스터 과제 Upsert
                    conn.execute(
                        """
                        INSERT INTO dynamic_master_grants (
                            program_id, program_name, category, supervising_ministry, operating_agency,
                            region_scope, target_stage, target_qualifications, expected_period,
                            expected_month, support_scale, support_details, inquiry_contact, source_portal, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(program_id) DO UPDATE SET
                            program_name=excluded.program_name,
                            category=excluded.category,
                            supervising_ministry=excluded.supervising_ministry,
                            operating_agency=excluded.operating_agency,
                            region_scope=excluded.region_scope,
                            target_qualifications=excluded.target_qualifications,
                            support_scale=excluded.support_scale,
                            support_details=excluded.support_details,
                            inquiry_contact=excluded.inquiry_contact,
                            source_portal=excluded.source_portal,
                            updated_at=excluded.updated_at,
                            version=dynamic_master_grants.version + 1;
                        """,
                        (
                            pid,
                            item.get("program_name", "미제명 과제"),
                            item.get("category", "사업화"),
                            item.get("supervising_entity", "정부 부처"),
                            item.get("operating_entity", "운영 기관"),
                            item.get("city_hub", "전국"),
                            "전단계",
                            item.get("target_qualifications", ""),
                            "연중 수시",
                            0,
                            item.get("financial_benefit", ""),
                            item.get("space_facility_benefit", ""),
                            item.get("inquiry_contact", ""),
                            item.get("source_portal", "notebooklm_sync"),
                            now_iso,
                        ),
                    )

                    self._merge_into_memory_master_catalog(item)

                    if is_update:
                        updated_count += 1
                        item["_action"] = "UPDATED"
                    else:
                        added_count += 1
                        item["_action"] = "ADDED"
                    existing_master_ids.add(pid)

                synced_programs.append(item)

            # 3. 감사 해시 및 동기화 로그 기록
            payload_json = json.dumps(synced_programs, ensure_ascii=False)
            sync_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
            total_count = len(synced_programs)

            conn.execute(
                """
                INSERT INTO notebook_sync_logs (
                    synced_at, notebook_id, status, added_count, updated_count,
                    total_count, sync_hash, message, payload_snapshot
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now_iso, resolved_notebook_id, "SUCCESS", added_count, updated_count,
                    total_count, sync_hash,
                    f"NotebookLM 과제 동기화 완료: 신규 {added_count}건, 갱신 {updated_count}건",
                    payload_json[:2000],  # 스냅샷 앞부분 보관
                ),
            )
            conn.commit()

        logger.info(
            "NotebookLM 과제 동기화 성공 (노트북: %s) -> 신규: %d건, 갱신: %d건, 전체: %d건",
            resolved_notebook_id, added_count, updated_count, len(synced_programs),
        )

        return {
            "ok": True,
            "status": "SUCCESS",
            "notebook_id": resolved_notebook_id,
            "notebook_url": self.notebook_url,
            "added_count": added_count,
            "updated_count": updated_count,
            "total_count": len(synced_programs),
            "sync_hash": sync_hash,
            "synced_at": now_iso,
            "programs": synced_programs,
        }

    def _merge_into_memory_global_catalog(self, item: Dict[str, Any]) -> None:
        """글로벌 카탈로그 메모리 객체 업데이트 또는 추가."""
        pid = item["program_id"]
        prog = GlobalGrantProgram(
            program_id=pid,
            country=item.get("country", "글로벌"),
            country_code=item.get("country_code", "KR"),
            city_hub=item.get("city_hub", "거점"),
            program_name=item["program_name"],
            program_name_en=item.get("program_name_en", ""),
            supervising_entity=item["supervising_entity"],
            operating_entity=item["operating_entity"],
            specialized_fields=item.get("specialized_fields", []),
            support_type=item.get("support_type", "종합"),
            financial_benefit=item.get("financial_benefit", ""),
            visa_benefit=item.get("visa_benefit", ""),
            space_facility_benefit=item.get("space_facility_benefit", ""),
            mentoring_network=item.get("mentoring_network", ""),
            target_qualifications=item.get("target_qualifications", ""),
            selection_scale=item.get("selection_scale", "수시"),
            source_portal=item.get("source_portal", "notebooklm_sync"),
            detail_url=item.get("detail_url", self.notebook_url),
            inquiry_contact=item.get("inquiry_contact", ""),
            case_studies=item.get("case_studies", []),
        )

        # 기존 항목 교체 또는 추가
        for idx, existing in enumerate(GLOBAL_GRANTS_CATALOG):
            if existing.program_id == pid:
                GLOBAL_GRANTS_CATALOG[idx] = prog
                return
        GLOBAL_GRANTS_CATALOG.append(prog)

    def _merge_into_memory_master_catalog(self, item: Dict[str, Any]) -> None:
        """국내 마스터 카탈로그 메모리 객체 업데이트 또는 추가."""
        pid = item["program_id"]
        prog = MasterGrantProgram(
            program_id=pid,
            program_name=item["program_name"],
            category=item.get("category", "사업화"),
            supervising_ministry=item["supervising_entity"],
            operating_agency=item["operating_entity"],
            region_scope=item.get("city_hub", "전국"),
            target_stage="전단계",
            target_qualifications=item.get("target_qualifications", ""),
            expected_period="연중 수시",
            expected_month=0,
            support_scale=item.get("financial_benefit", ""),
            support_details=item.get("space_facility_benefit", ""),
            inquiry_contact=item.get("inquiry_contact", ""),
            source_portal=item.get("source_portal", "notebooklm_sync"),
        )

        for idx, existing in enumerate(MASTER_GRANT_CATALOG):
            if existing.program_id == pid:
                MASTER_GRANT_CATALOG[idx] = prog
                return
        MASTER_GRANT_CATALOG.append(prog)

    def get_sync_status(self) -> Dict[str, Any]:
        """최근 동기화 상태 및 통계 조회."""
        self.db.ensure_schema()
        latest_log = None
        try:
            with self.db._connect() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT id, synced_at, notebook_id, status, added_count,
                           updated_count, total_count, sync_hash, message
                    FROM notebook_sync_logs
                    ORDER BY id DESC LIMIT 1
                    """
                )
                row = cur.fetchone()
                if row:
                    latest_log = {
                        "id": row[0],
                        "synced_at": row[1],
                        "notebook_id": row[2],
                        "status": row[3],
                        "added_count": row[4],
                        "updated_count": row[5],
                        "total_count": row[6],
                        "sync_hash": row[7],
                        "message": row[8],
                    }

                # 동적 저장된 과제 총 수 집계
                cur.execute("SELECT count(*) FROM dynamic_global_grants")
                dynamic_global_count = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM dynamic_master_grants")
                dynamic_master_count = cur.fetchone()[0]
        except Exception as e:
            logger.warning("동기화 상태 조회 중 예외: %s", e)
            dynamic_global_count = 0
            dynamic_master_count = 0

        return {
            "notebook_url": self.notebook_url,
            "notebook_id": self.notebook_id,
            "is_enabled": self.config.get("enabled", True),
            "sync_interval_seconds": self.config.get("sync_interval_seconds", 14400),
            "latest_sync": latest_log,
            "total_dynamic_global_grants": dynamic_global_count,
            "total_dynamic_master_grants": dynamic_master_count,
            "in_memory_global_grants_count": len(GLOBAL_GRANTS_CATALOG),
            "in_memory_master_grants_count": len(MASTER_GRANT_CATALOG),
        }

    def get_sync_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """동기화 실행 이력 로그 목록 반환."""
        self.db.ensure_schema()
        history = []
        try:
            with self.db._connect() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT id, synced_at, notebook_id, status, added_count,
                           updated_count, total_count, sync_hash, message
                    FROM notebook_sync_logs
                    ORDER BY id DESC LIMIT ?
                    """,
                    (limit,),
                )
                for r in cur.fetchall():
                    history.append({
                        "id": r[0],
                        "synced_at": r[1],
                        "notebook_id": r[2],
                        "status": r[3],
                        "added_count": r[4],
                        "updated_count": r[5],
                        "total_count": r[6],
                        "sync_hash": r[7],
                        "message": r[8],
                    })
        except Exception as e:
            logger.warning("동기화 이력 조회 실패: %s", e)
        return history

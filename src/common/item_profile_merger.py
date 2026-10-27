"""사업 아이템 ↔ 기업 프로필 병합 및 상속 헬퍼
(src/common/item_profile_merger.py)
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from src.matcher.preflight import DEFAULT_PROFILE


# REQ-021 아이템 company_specs 스키마 14대 표준 필드
COMPANY_SPECS_FIELDS = [
    "company_name",
    "biz_reg_no",
    "opened_date",
    "founder_birth",
    "founder_gender",
    "address",
    "debt_ratio_pct",
    "has_rnd_lab",
    "is_capital_impaired",
    "has_tax_arrears",
    "current_pi_projects",
    "registered_patents_count",
    "prior_grant_history",
    "certifications",
]

_BOOL_FIELDS = frozenset({"has_rnd_lab", "is_capital_impaired", "has_tax_arrears"})
_LIST_FIELDS = frozenset({"prior_grant_history", "certifications", "tags", "keywords"})


def merge_item_company_specs(
    item_specs: Optional[Dict[str, Any]],
    global_profile: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    아이템의 company_specs와 글로벌 company_profile을 병합합니다.
    - 아이템에 명시적으로 설정된 값(오버라이드)이 우선합니다.
    - 글로벌 프로필의 company_name이 없거나 비어있으면 상속하지 않습니다.
    - 법적 정합성 가드레일:
      1) 대표자가 여성이 아닌 경우 (남성 'M' 또는 미지정 '') 상속된 인증서에서 '여성기업' 원천 배제.
      2) 아이템에서 founder_gender가 'NONE'인 경우 명시적 미지정으로 상속 차단.
      3) 아이템에 certifications가 명시된 경우(빈 리스트 포함) 해당 리스트를 유지.
    """
    item_raw = item_specs or {}
    global_raw = global_profile or {}

    effective = dict(DEFAULT_PROFILE)

    # 1. 글로벌 프로필 기본 적용 (글로벌 프로필이 유효할 때만)
    if global_raw and any(str(global_raw.get(k) or "").strip() for k in ("company_name", "biz_reg_no")):
        for k, v in global_raw.items():
            if v is not None and k in effective:
                effective[k] = v

    # 2. 아이템별 company_specs 오버라이드
    is_explicit_gender_none = False
    for k in COMPANY_SPECS_FIELDS:
        if k not in item_raw:
            continue
        v = item_raw[k]

        if k in _BOOL_FIELDS:
            if v is not None:
                effective[k] = bool(v)
        elif k in _LIST_FIELDS:
            if isinstance(v, list):
                # 아이템에 명시된 리스트(빈 리스트 포함) 유지
                effective[k] = list(v)
            elif isinstance(v, str) and v.strip():
                effective[k] = [x.strip() for x in v.split(",") if x.strip()]
        else:
            if v is not None:
                str_v = str(v).strip()
                if k == "founder_gender":
                    if str_v.upper() == "NONE":
                        effective[k] = ""
                        is_explicit_gender_none = True
                    elif str_v != "":
                        effective[k] = str_v
                elif str_v != "":
                    effective[k] = v

    # 3. 법적 정합성 가드레일:
    # 대표자가 여성이 명백히 아닌 경우 (남성 'M'이거나 미지정/NONE '') "여성기업" 인증 원천 배제
    gender_val = str(effective.get("founder_gender") or "").strip().upper()
    if gender_val != "F" or is_explicit_gender_none:
        if "certifications" in effective and isinstance(effective["certifications"], list):
            effective["certifications"] = [c for c in effective["certifications"] if c != "여성기업"]

    return effective

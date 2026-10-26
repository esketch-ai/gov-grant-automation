"""LLM 출력으로부터 JSON 오브젝트를 추출하는 공통 헬퍼."""
from __future__ import annotations

import json
import re


def extract_json_object(text: str) -> dict:
    """
    LLM 응답에서 JSON 오브젝트를 추출한다.
    1) ```json ... ``` 코드펜스
    2) { ... } 첫-마지막 괄호
    순서로 시도하고, 실패 시 {} 반환.
    """
    if not text:
        return {}

    # 1) 코드펜스
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        try:
            return json.loads(fence.group(1))
        except Exception:
            pass

    # 2) 첫 '{' ~ 마지막 '}'
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e != -1 and e > s:
        try:
            return json.loads(text[s : e + 1])
        except Exception:
            pass

    return {}

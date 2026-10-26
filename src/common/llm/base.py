"""
LLMClient 추상 인터페이스 + 공통 유틸리티.

모든 구현체는 generate_structured() 로 Pydantic 스키마에 맞는
dict 를 반환해야 한다. 파싱 실패는 LLMStructuredParseError 로 상기를
투입하고, 상위는 (matcher)가 안전 degrade 를 결정한다.
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Type, TypeVar

from .schemas_helpers import extract_json_object

T = TypeVar("T")


class LLMStructuredParseError(Exception):
    """structured 출력으로부터 스키마를 추출/검증하지 못한 경우."""


class LLMClient(ABC):
    """Structured Output을 생성/검증할 수 있는 LLM 어댑터."""

    @abstractmethod
    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: "Type[object]",
    ) -> dict:
        """
        system+user 프롬프트로 LLM을 호출하고, response_schema(Pydantic v2)
        로 검증 가능한 dict 를 반환한다. 검증 실패 시 LLMStructuredParseError.
        """
        raise NotImplementedError

    def _validate(self, raw: dict, response_schema: "Type[object]") -> dict:
        try:
            obj = response_schema.model_validate(raw)
            return obj.model_dump()
        except Exception:
            # Pydantic 미설치 fallback (import 시 shim)
            if not hasattr(response_schema, "model_validate"):
                return raw
            raise LLMStructuredParseError(
                f"Structured Output 검증 실패: {raw!r:.200}"
            )

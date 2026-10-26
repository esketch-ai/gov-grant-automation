from __future__ import annotations

"""LLM 클라이언트 추상화. 로컬 Ollama(1순위) / 클라우드(선택) 구조."""
import os

from .base import LLMClient, LLMStructuredParseError
from .ollama_client import OllamaClient
from .cloud_client import CloudLLMClient


def build_llm_client(force_offline: bool = False) -> LLMClient:
    """
    환경변수로 어댑터를 결정한다.
    - LLM_PROVIDER=cloud -> CloudLLMClient (OpenAI 호환 엔드포인트 / Gemini)
    - 그 외(기본값)     -> OllamaClient  (로컬, DEFAULT)
    """
    provider = os.environ.get("LLM_PROVIDER", "ollama").lower()
    if provider == "cloud":
        base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
        model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        api_key = os.environ.get("LLM_API_KEY", "")
        return CloudLLMClient(base_url=base_url, model=model, api_key=api_key)

    base_url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model = os.environ.get("OLLAMA_MODEL", "qwen3:32b")
    return OllamaClient(base_url=base_url, model=model)

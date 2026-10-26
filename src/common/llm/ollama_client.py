"""
로컬 Ollama 어댑터 (기본 LLM 프로바이더).
http://127.0.0.1:11434 /api/chat 호출로 Structured Output을 생성하고
Pydantic 스키마로 검증한다. 파싱 실패 시 1회 재시도 후
LLMStructuredParseError 를 상위로 던진다(상위=matcher가 degrade 결정).
"""
from __future__ import annotations

from ..logging_config import get_logger
from .base import LLMClient, LLMStructuredParseError
from .schemas_helpers import extract_json_object

logger = get_logger(__name__)


class OllamaClient(LLMClient):
    def __init__(self, base_url: str = "http://127.0.0.1:11434", model: str = "qwen3:32b",
                 timeout: float = 300.0, max_retries: int = 1, keep_alive: str = "1h"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.keep_alive = keep_alive  # 메모리 상주 시간(워밍업 후 유지)

    def _chat(self, unused_system: str, user_prompt: str) -> str:
        """Ollama /api/chat 호출. 실패 시 빈 문자열로 degrade(파이프라인 미중단)."""
        import httpx

        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "format": "json",   # Ollama Structured 출력 촉진
            "keep_alive": self.keep_alive,  # 모델 메모리 상주 유지(워밍업 효과)
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
            return data.get("message", {}).get("content", "") or ""
        except Exception as e:
            logger.warning("Ollama 호출 실패: %s", e)
            return ""

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: "object",
    ) -> dict:
        schema_json = _safe_json_schema(response_schema)
        instruction = (
            "\n\n[출력 형식 강제조항] 다음 JSON 문자열 하나만 출력하세요. "
            "설명·마크다운·코드펜스 없이 순수 JSON만 출력합니다. "
            f"JSON 스키마: {schema_json}"
        )
        prompt = (system_prompt + "\n" if system_prompt else "") + user_prompt + instruction

        last_error = "없음"
        for attempt in range(1 + self.max_retries):
            text = self._chat("", prompt)
            obj = extract_json_object(text)
            if obj:
                try:
                    return self._validate(obj, response_schema)
                except LLMStructuredParseError as e:
                    last_error = f"검증 실패(attempt {attempt + 1}): {e}"
                    logger.warning(last_error)
            else:
                last_error = f"JSON 추출 실패(attempt {attempt + 1})"
                logger.warning(last_error)

        raise LLMStructuredParseError(f"Structured Output 파싱 실패: {last_error}")


    @staticmethod
    def warmup(base_url: str = "http://127.0.0.1:11434", model: str = "qwen3:32b",
               keep_alive: str = "1h", timeout: float = 10.0) -> bool:
        """
        사전 워밍업: 모델 메모리 상주를 빠르게 확인/트리거한다.
        /api/tags 로 존재 확인 후 극소량 /api/generate(keep_alive=1h) 로 메모리 상주 고정.
        실패는 로그 후 False(파이프라인 미중단 — 미상주 시 첫 호출이 다시 로드).
        """
        import httpx
        url = base_url.rstrip("/")
        try:
            with httpx.Client(timeout=timeout) as client:
                client.get(f"{url}/api/tags")  # 존재 확인
                client.post(f"{url}/api/generate", json={
                    "model": model, "prompt": "warm", "stream": False, "keep_alive": keep_alive,
                })
            logger.info("Ollama warm-up 완료: 모델 '%s' 메모리 상주 고정(keep_alive=%s)", model, keep_alive)
            return True
        except Exception as e:
            logger.warning("Ollama warm-up 실패(무시 후 재시도): %s", e)
            return False


def _safe_json_schema(schema: type) -> str:
    """Pydantic v2 의 model_json_schema() 를 best-effort 문자열로 변환."""
    try:
        import json

        return json.dumps(schema.model_json_schema(), ensure_ascii=False)
    except Exception:
        return "{}"

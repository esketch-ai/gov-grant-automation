"""
선택형 클라우드 어댑터 (OpenAI 호환 엔드포인트 / Gemini 등).
LLM_PROVIDER=cloud 인 경우에만 활성화된다. 로컬 Ollama 1순위 원칙.
"""
from __future__ import annotations

from ..logging_config import get_logger
from .base import LLMClient, LLMStructuredParseError
from .schemas_helpers import extract_json_object

logger = get_logger(__name__)


class CloudLLMClient(LLMClient):
    def __init__(
        self,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        api_key: str = "",
        timeout: float = 300.0,
        max_retries: int = 1,
    ):
        if not api_key:
            raise ValueError("CloudLLMClient 는 LLM_API_KEY 환경변수가 필요합니다.")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.token = api_key
        self.timeout = timeout
        self.max_retries = max_retries

    def _chat(self, system_prompt: str, user_prompt: str) -> str:
        import httpx

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt or "당신은 정부 R&D/조달 자격 검증 전문가입니다."},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning("Cloud LLM 호출 실패: %s", e)
            return ""

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: "object",
    ) -> dict:
        instruction = "\n\n[출력 형식 강제조항] 순수 JSON 문자열 하나만 출력하세요."
        last_error = "없음"
        for attempt in range(1 + self.max_retries):
            text = self._chat(system_prompt, user_prompt + instruction)
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
        raise LLMStructuredParseError(f"Cloud Structured Output 파싱 실패: {last_error}")

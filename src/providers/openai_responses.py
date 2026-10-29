"""OpenAI SDK Responses API adapter for Azure OpenAI v1 and compatible endpoints."""

import os

from .base import ProviderResult


MESSAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "message": {"type": "string"},
                },
                "required": ["id", "message"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["results"],
    "additionalProperties": False,
}


class OpenAIResponsesProvider:
    def __init__(self, api_key_env: str, base_url: str | None, timeout_seconds: int, max_retries: int = 0):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ValueError("OpenAI SDK is not installed. Install local dependencies with pip install -r requirements-local.txt.") from exc
        api_key = os.environ.get(api_key_env, "").strip()
        if not api_key:
            raise ValueError(f"API key is missing. Set {api_key_env} in the local .env file or environment.")
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
            max_retries=max_retries,
        )

    def generate(self, payload: dict, system_prompt: str, model: str) -> ProviderResult:
        import json

        user_content = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        response = self.client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_content}]},
            ],
            text={"format": {
                "type": "json_schema",
                "name": "customer_messages",
                "strict": True,
                "schema": MESSAGE_SCHEMA,
            }},
            store=False,
        )
        usage = getattr(response, "usage", None)
        return ProviderResult(
            output_text=response.output_text or "",
            request_id=getattr(response, "id", None),
            model=getattr(response, "model", None),
            input_tokens=getattr(usage, "input_tokens", None) if usage else None,
            output_tokens=getattr(usage, "output_tokens", None) if usage else None,
            total_tokens=getattr(usage, "total_tokens", None) if usage else None,
        )


def is_retryable_api_error(exc: Exception) -> bool:
    """Retry only transient transport, timeout, rate-limit, or server failures."""
    try:
        from openai import APIConnectionError, APIStatusError, APITimeoutError, InternalServerError, RateLimitError
    except ImportError:
        return False
    if isinstance(exc, (APIConnectionError, APITimeoutError, RateLimitError, InternalServerError)):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code >= 500 or exc.status_code == 429
    return False

"""Small provider boundary for synchronous, structured suggestions."""

import json
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import Settings


class ProviderFailure(Exception):
    """A safe, content-free provider failure."""


class AIProvider(Protocol):
    def generate_structured(
        self, *, kind: str, context: dict[str, Any], schema: dict[str, Any]
    ) -> object: ...


class OpenAIProvider:
    def __init__(self, settings: Settings):
        self.settings = settings

    def generate_structured(
        self, *, kind: str, context: dict[str, Any], schema: dict[str, Any]
    ) -> object:
        if not self.settings.ai_api_key:
            raise ProviderFailure("configuration")
        from app.ai.prompts import prompt_for

        payload = {
            "model": self.settings.ai_model,
            "store": False,
            "instructions": prompt_for(kind),
            "input": json.dumps({"context": context, "output_schema": schema}, ensure_ascii=False),
            "text": {"format": {"type": "json_object"}},
        }
        request = Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.ai_api_key.get_secret_value()}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.settings.ai_timeout_seconds) as response:
                raw = response.read()
        except (HTTPError, URLError, TimeoutError, OSError):
            raise ProviderFailure("unavailable") from None
        try:
            result = json.loads(raw)
            if result["status"] != "completed":
                raise ValueError
            chunks = [
                part["text"]
                for item in result["output"]
                if item.get("type") == "message"
                for part in item.get("content", [])
                if part.get("type") == "output_text"
            ]
            return json.loads("".join(chunks))
        except (KeyError, TypeError, ValueError):
            raise ProviderFailure("invalid_response") from None

"""Small provider boundary for synchronous, structured suggestions."""

import json
import logging
import re
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import Settings

logger = logging.getLogger(__name__)
_SAFE_LOG_VALUE = re.compile(r"[^a-zA-Z0-9_.:-]")


def _safe_log_value(value: object) -> str:
    if value is None:
        return "unknown"
    return _SAFE_LOG_VALUE.sub("_", str(value))[:80] or "unknown"


def _message_classification(value: object) -> str:
    if not isinstance(value, str):
        return "unknown"
    message = value.casefold()
    patterns = (
        ("unsupported parameter", "unsupported_parameter"),
        ("unknown parameter", "unknown_parameter"),
        ("unrecognized parameter", "unknown_parameter"),
        ("invalid parameter", "invalid_parameter"),
        ("model_not_found", "model_unavailable"),
        ("model does not exist", "model_unavailable"),
        ("json mode", "json_mode_error"),
        ("json schema", "json_schema_error"),
    )
    return next((category for marker, category in patterns if marker in message), "unclassified")


def _provider_error_fields(error: HTTPError) -> tuple[str, str, str, str]:
    try:
        body = json.loads(error.read(65_536))
        details = body.get("error", {}) if isinstance(body, dict) else {}
        if not isinstance(details, dict):
            return "unknown", "unknown", "unknown", "unknown"
        return (
            _safe_log_value(details.get("type", "unknown")),
            _safe_log_value(details.get("code", "unknown")),
            _safe_log_value(details.get("param", "unknown")),
            _message_classification(details.get("message")),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        return "unknown", "unknown", "unknown", "unknown"


def _log_provider_error(
    *,
    operation: str,
    model: str,
    category: str,
    timeout: int,
    status: int | None = None,
    error_type: str = "unknown",
    error_code: str = "unknown",
    error_param: str = "unknown",
    message_class: str = "unknown",
) -> None:
    logger.warning(
        "AI provider error operation=%s model=%s category=%s status=%s "
        "error_type=%s error_code=%s error_param=%s message_class=%s timeout_seconds=%s",
        _safe_log_value(operation),
        _safe_log_value(model),
        category,
        status if status is not None else "none",
        error_type,
        error_code,
        error_param,
        message_class,
        timeout,
    )


class ProviderFailure(Exception):
    """A safe, content-free provider failure."""


class AIProvider(Protocol):
    def generate_structured(
        self, *, kind: str, context: dict[str, Any], schema: dict[str, Any]
    ) -> object: ...


def _serialize_input(context: dict[str, Any], schema: dict[str, Any]) -> str:
    content = json.dumps({"context": context, "output_schema": schema}, ensure_ascii=False)
    return f"Return only valid JSON matching the output_schema below.\n{content}"


def _build_request_payload(
    *, kind: str, context: dict[str, Any], schema: dict[str, Any], settings: Settings
) -> dict[str, Any]:
    from app.ai.prompts import prompt_for

    return {
        "model": settings.ai_model,
        "store": False,
        "instructions": prompt_for(kind),
        "input": _serialize_input(context, schema),
        "text": {"format": {"type": "json_object"}},
    }


class OpenAIProvider:
    def __init__(self, settings: Settings):
        self.settings = settings

    def generate_structured(
        self, *, kind: str, context: dict[str, Any], schema: dict[str, Any]
    ) -> object:
        if not self.settings.ai_api_key:
            raise ProviderFailure("configuration")
        payload = _build_request_payload(
            kind=kind, context=context, schema=schema, settings=self.settings
        )
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
        except HTTPError as exc:
            error_type, error_code, error_param, message_class = _provider_error_fields(exc)
            _log_provider_error(
                operation=kind,
                model=self.settings.ai_model,
                category="provider_http_error",
                status=exc.code,
                error_type=error_type,
                error_code=error_code,
                error_param=error_param,
                message_class=message_class,
                timeout=self.settings.ai_timeout_seconds,
            )
            raise ProviderFailure("unavailable") from None
        except TimeoutError:
            _log_provider_error(
                operation=kind,
                model=self.settings.ai_model,
                category="timeout",
                timeout=self.settings.ai_timeout_seconds,
            )
            raise ProviderFailure("unavailable") from None
        except URLError:
            _log_provider_error(
                operation=kind,
                model=self.settings.ai_model,
                category="network_error",
                timeout=self.settings.ai_timeout_seconds,
            )
            raise ProviderFailure("unavailable") from None
        except OSError:
            _log_provider_error(
                operation=kind,
                model=self.settings.ai_model,
                category="transport_error",
                timeout=self.settings.ai_timeout_seconds,
            )
            raise ProviderFailure("unavailable") from None
        try:
            result = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            _log_provider_error(
                operation=kind,
                model=self.settings.ai_model,
                category="invalid_json",
                timeout=self.settings.ai_timeout_seconds,
            )
            raise ProviderFailure("invalid_response") from None
        try:
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
        except json.JSONDecodeError:
            _log_provider_error(
                operation=kind,
                model=self.settings.ai_model,
                category="invalid_json",
                timeout=self.settings.ai_timeout_seconds,
            )
            raise ProviderFailure("invalid_response") from None
        except (KeyError, TypeError, ValueError):
            _log_provider_error(
                operation=kind,
                model=self.settings.ai_model,
                category="invalid_response",
                timeout=self.settings.ai_timeout_seconds,
            )
            raise ProviderFailure("invalid_response") from None

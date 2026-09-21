import io
import json
import logging
from email.message import Message
from types import SimpleNamespace
from typing import Any, cast
from urllib.error import HTTPError

import pytest
from pydantic import SecretStr

from app.ai import provider as provider_module
from app.ai.provider import OpenAIProvider, ProviderFailure, _build_request_payload
from app.core.config import Settings
from app.schemas.diet import VersionContent as DietContent
from app.schemas.workout import VersionContent as WorkoutContent

SECRET = "sk-test-secret-never-log"
PII = "student.private@example.com"
PROMPT = "private clinical prompt"


def settings() -> Settings:
    return cast(
        Settings,
        SimpleNamespace(
            ai_api_key=SecretStr(SECRET),
            ai_model="gpt-5.6-luna",
            ai_timeout_seconds=45,
        ),
    )


def generate() -> object:
    return OpenAIProvider(settings()).generate_structured(
        kind="diet",
        context={"private": PII, "instructions": PROMPT},
        schema={"type": "object"},
    )


@pytest.mark.parametrize(
    ("kind", "schema", "context_keys"),
    [
        (
            "diet",
            DietContent.model_json_schema(),
            {"goal", "activity_level", "meal_schedule", "food_restrictions"},
        ),
        (
            "workout",
            WorkoutContent.model_json_schema(),
            {"goal", "activity_level", "training_experience", "training_frequency"},
        ),
    ],
)
def test_request_payload_has_valid_nonempty_string_input(
    kind: str, schema: dict[str, Any], context_keys: set[str]
) -> None:
    context = {key: f"synthetic-{key}" for key in context_keys}
    payload = _build_request_payload(kind=kind, context=context, schema=schema, settings=settings())

    assert set(payload) == {"model", "store", "instructions", "input", "text"}
    assert payload["model"] == "gpt-5.6-luna"
    assert payload["store"] is False
    assert payload["text"] == {"format": {"type": "json_object"}}
    assert isinstance(payload["instructions"], str)
    assert "json" in payload["instructions"].casefold()
    assert 1_000 < len(payload["instructions"]) < 10_000
    assert "Prompt version: v2" in payload["instructions"]
    assert isinstance(payload["input"], str) and payload["input"]
    assert "json" in payload["input"].casefold()
    assert payload["input"].encode("utf-8").decode("utf-8") == payload["input"]

    instruction, separator, serialized_content = payload["input"].partition("\n")
    assert separator == "\n"
    assert instruction == "Return only valid JSON matching the output_schema below."
    decoded_input = json.loads(serialized_content)
    assert set(decoded_input) == {"context", "output_schema"}
    assert set(decoded_input["context"]) == context_keys
    assert decoded_input["output_schema"] == schema
    encoded_request = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    assert json.loads(encoded_request)["input"] == payload["input"]


def test_json_mode_requires_input_message_itself_to_mention_json() -> None:
    payload = _build_request_payload(
        kind="diet",
        context={"goal": "synthetic"},
        schema={"type": "object"},
        settings=settings(),
    )

    assert payload["text"] == {"format": {"type": "json_object"}}
    assert "json" in payload["input"].casefold()


@pytest.mark.parametrize("status", [400, 401, 403, 404, 429, 500])
def test_http_errors_are_safely_categorized(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    status: int,
) -> None:
    response = {
        "error": {
            "type": f"safe_type_{status}",
            "code": f"safe_code_{status}",
            "param": "text.format",
            "message": (
                f"Unsupported parameter: text.format {SECRET} Authorization Bearer {PII} {PROMPT}"
            ),
        }
    }

    def fail(*args: Any, **kwargs: Any) -> None:
        raise HTTPError(
            "https://api.openai.com/v1/responses",
            status,
            "sensitive upstream message",
            Message(),
            io.BytesIO(json.dumps(response).encode()),
        )

    monkeypatch.setattr(provider_module, "urlopen", fail)
    with caplog.at_level(logging.WARNING, logger="app.ai.provider"):
        with pytest.raises(ProviderFailure, match="unavailable"):
            generate()

    log = caplog.text
    assert f"status={status}" in log
    assert "category=provider_http_error" in log
    assert f"error_type=safe_type_{status}" in log
    assert f"error_code=safe_code_{status}" in log
    assert "error_param=text.format" in log
    assert "message_class=unsupported_parameter" in log
    assert SECRET not in log
    assert "Authorization" not in log
    assert PII not in log
    assert PROMPT not in log


def test_null_error_fields_are_logged_as_unknown(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    response = {
        "error": {
            "type": "invalid_request_error",
            "code": None,
            "param": None,
            "message": f"unclassified {SECRET} {PII} {PROMPT}",
        }
    }

    def fail(*args: Any, **kwargs: Any) -> None:
        raise HTTPError(
            "https://api.openai.com/v1/responses",
            400,
            "sensitive upstream message",
            Message(),
            io.BytesIO(json.dumps(response).encode()),
        )

    monkeypatch.setattr(provider_module, "urlopen", fail)
    with caplog.at_level(logging.WARNING, logger="app.ai.provider"):
        with pytest.raises(ProviderFailure, match="unavailable"):
            generate()

    assert "error_code=unknown" in caplog.text
    assert "error_param=unknown" in caplog.text
    assert "message_class=unclassified" in caplog.text
    assert SECRET not in caplog.text
    assert PII not in caplog.text
    assert PROMPT not in caplog.text


def test_timeout_is_safely_categorized(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def fail(*args: Any, **kwargs: Any) -> None:
        raise TimeoutError(f"{SECRET} {PII} {PROMPT}")

    monkeypatch.setattr(provider_module, "urlopen", fail)
    with caplog.at_level(logging.WARNING, logger="app.ai.provider"):
        with pytest.raises(ProviderFailure, match="unavailable"):
            generate()

    assert "category=timeout" in caplog.text
    assert "timeout_seconds=45" in caplog.text
    assert SECRET not in caplog.text
    assert PII not in caplog.text
    assert PROMPT not in caplog.text


def test_invalid_response_is_safely_categorized(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return f"invalid {SECRET} {PII} {PROMPT}".encode()

    monkeypatch.setattr(provider_module, "urlopen", lambda *args, **kwargs: Response())
    with caplog.at_level(logging.WARNING, logger="app.ai.provider"):
        with pytest.raises(ProviderFailure, match="invalid_response"):
            generate()

    assert "category=invalid_json" in caplog.text
    assert SECRET not in caplog.text
    assert PII not in caplog.text
    assert PROMPT not in caplog.text


def test_invalid_output_text_json_is_safely_categorized(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "status": "completed",
                    "output": [
                        {
                            "type": "message",
                            "content": [
                                {"type": "output_text", "text": f"invalid {SECRET} {PII} {PROMPT}"}
                            ],
                        }
                    ],
                }
            ).encode()

    monkeypatch.setattr(provider_module, "urlopen", lambda *args, **kwargs: Response())
    with caplog.at_level(logging.WARNING, logger="app.ai.provider"):
        with pytest.raises(ProviderFailure, match="invalid_response"):
            generate()

    assert "category=invalid_json" in caplog.text
    assert SECRET not in caplog.text
    assert PII not in caplog.text
    assert PROMPT not in caplog.text

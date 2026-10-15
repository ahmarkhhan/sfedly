"""Configured Apertus chat-completions endpoint; no alternative-model fallback."""

import os
import json
import math
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import httpx


class EndpointError(ValueError):
    """Safe failure metadata; never includes provider bodies or credentials."""

    def __init__(self, reason: str, message: str, status_code: int | None = None):
        super().__init__(message)
        self.reason = reason
        self.status_code = status_code


def request_payload(settings: "Settings", messages: list[dict[str, str]], *, max_tokens=4096,
                    temperature=0, json_schema: dict | None = None) -> dict:
    if type(max_tokens) is not int or max_tokens < 1:
        raise ValueError("max_tokens must be a positive integer")
    if type(temperature) not in {int, float} or not math.isfinite(temperature) or temperature < 0:
        raise ValueError("temperature must be finite and nonnegative")
    payload = {"model": settings.model, "messages": messages,
               "temperature": temperature, "max_tokens": max_tokens}
    if json_schema is not None:
        payload["response_format"] = {"type": "json_schema", "json_schema": {
            "name": "parliamentary_affair", "schema": json_schema, "strict": True}}
    return payload


@dataclass(frozen=True)
class Settings:
    model: str
    base_url: str
    api_key: str = field(repr=False)

    @classmethod
    def from_environment(cls):
        model = os.environ.get("LLM_NAME", "").strip()
        base_url = os.environ.get("LLM_BASE_URL", "").strip().rstrip("/")
        key = os.environ.get("LLM_API_KEY", "").strip()
        if not model or not base_url:
            raise ValueError("Set LLM_NAME and LLM_BASE_URL in the local environment or .env")
        url = urlsplit(base_url)
        if not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("LLM_BASE_URL must be a base URL without credentials, query or fragment")
        if url.scheme != "https" and not (
            url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"}
        ):
            raise ValueError("Use HTTPS, or HTTP for a local model endpoint")
        return cls(model=model, base_url=base_url, api_key=key)


@dataclass(frozen=True)
class Completion:
    content: str
    usage: dict[str, int]
    finish_reason: str | None
    reported_model: str | None


def complete_recorded(settings: Settings, messages: list[dict[str, str]], *, max_tokens=4096, temperature=0,
                      json_schema: dict | None = None,
                      transport: httpx.BaseTransport | None = None) -> Completion:
    """Retain provider completion status, including truncated/unknown responses.

    Callers must persist and validate the response before accepting proposals.
    The legacy complete() API below continues to reject non-stop generations.
    """
    headers = {"Authorization": f"Bearer {settings.api_key}"} if settings.api_key else {}
    payload = request_payload(settings, messages, max_tokens=max_tokens,
                              temperature=temperature, json_schema=json_schema)
    try:
        with httpx.Client(timeout=60, follow_redirects=False, transport=transport) as client:
            response = client.post(
                settings.base_url + "/chat/completions",
                headers=headers,
                json=payload,
            )
        if response.status_code != 200:
            raise EndpointError("http_error", f"Model endpoint returned HTTP {response.status_code}; no output accepted",
                                response.status_code)
        data = response.json()
        reported_model = data.get("model")
        if reported_model is not None and reported_model != settings.model:
            raise EndpointError("model_mismatch", "Endpoint returned a different model; no output accepted")
        choice = data["choices"][0]
        finish_reason = choice.get("finish_reason")
        if finish_reason is not None and not isinstance(finish_reason, str):
            raise EndpointError("response_shape", "Invalid provider completion status")
        content = choice["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise EndpointError("empty_response", "Model returned no text; no output accepted")
        raw_usage = data.get("usage")
        if not isinstance(raw_usage, dict):
            raw_usage = {}
        usage = {k: v for k, v in raw_usage.items()
                 if k in {"prompt_tokens", "completion_tokens", "total_tokens"}
                 and type(v) is int and v >= 0}
        return Completion(content, usage, finish_reason, reported_model)
    except httpx.HTTPError:
        raise EndpointError("connection_error", "Model connection failed or timed out; check the endpoint and access") from None
    except (KeyError, IndexError, TypeError, AttributeError, json.JSONDecodeError):
        raise EndpointError("response_shape", "Unexpected chat-completions response; no output accepted") from None


def complete(settings: Settings, messages: list[dict[str, str]], *, max_tokens=4096, temperature=0,
             json_schema: dict | None = None,
             transport: httpx.BaseTransport | None = None) -> tuple[str, dict[str, int]]:
    result = complete_recorded(settings, messages, max_tokens=max_tokens, temperature=temperature,
                               json_schema=json_schema, transport=transport)
    if result.finish_reason != "stop":
        raise EndpointError("incomplete_response", "Model response did not complete normally; no output accepted")
    return result.content, result.usage


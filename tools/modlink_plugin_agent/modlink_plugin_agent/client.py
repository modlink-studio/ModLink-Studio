"""OpenAI-compatible JSON client for the plugin agent."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import httpx

type ChatMessage = dict[str, Any]
type PostCallable = Callable[..., Any]


@dataclass(frozen=True, slots=True)
class AiConfig:
    base_url: str
    api_key: str
    model: str
    timeout_s: float = 60.0

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)


class OpenAICompatibleJsonClient:
    def __init__(
        self,
        config: AiConfig,
        *,
        post: PostCallable | None = None,
    ) -> None:
        if not config.is_configured:
            raise ValueError("AI agent requires base URL, API key, and model")
        self._config = config
        self._post = httpx.post if post is None else post

    def complete_json(self, messages: Sequence[ChatMessage]) -> dict[str, Any]:
        url = f"{self._config.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._config.model,
            "messages": list(messages),
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        try:
            response = self._post(
                url,
                headers=headers,
                json=payload,
                timeout=self._config.timeout_s,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            hint = _http_status_hint(status)
            raise RuntimeError(f"AI service returned HTTP {status}. {hint}") from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Could not connect to AI service: {exc}") from exc
        except ValueError as exc:
            raise RuntimeError("AI service returned invalid JSON") from exc

        message = _extract_assistant_message(data)
        content = _message_content(message)
        return _parse_json_content(content)


def _extract_assistant_message(data: object) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise RuntimeError("AI response must be an object")
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("AI response is missing choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise RuntimeError("AI response choice must be an object")
    message = first.get("message")
    if not isinstance(message, dict):
        raise RuntimeError("AI response is missing message")
    return dict(message)


def _message_content(message: dict[str, Any]) -> str:
    content = message.get("content")
    if not isinstance(content, str):
        raise RuntimeError("AI response is missing text content")
    return content


def _parse_json_content(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("AI response content is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("AI response JSON must be an object")
    return parsed


def _http_status_hint(status: object) -> str:
    if status == 401:
        return "Check the API key value and --api-key-env/.env configuration."
    if status == 403:
        return "Check whether the API key has access to the selected model."
    if status == 404:
        return "Check --base-url; it should point to an OpenAI-compatible /v1 endpoint."
    if status == 400:
        return "Check the model name and whether the provider supports JSON response_format."
    return "Check the OpenAI-compatible service configuration."

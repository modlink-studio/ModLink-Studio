from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import httpx
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from modlink_ui.shared.ui_settings.ai import AiAssistantConfig

from .experiment_runtime import ExperimentRuntimeSnapshot

EXPERIMENT_AI_SYSTEM_PROMPT = """You are the ModLink Studio experiment setup assistant.
Help the user draft experiment_name, session_name, and step queue values for the current live experiment sidebar.
Do not control acquisition, recording, hardware, devices, files, or timing.
Return only one JSON object with this exact shape:
{"message":"...","proposal":{"experiment_name":"...","session_name":"...","steps":["..."]}}
If there is no concrete setting proposal, use null for proposal:
{"message":"...","proposal":null}
Use concise Chinese unless the user asks otherwise."""


@dataclass(frozen=True, slots=True)
class ExperimentAiProposal:
    experiment_name: str | None = None
    session_name: str | None = None
    steps: tuple[str, ...] | None = None

    @property
    def has_values(self) -> bool:
        return (
            self.experiment_name is not None
            or self.session_name is not None
            or self.steps is not None
        )


@dataclass(frozen=True, slots=True)
class ExperimentAiReply:
    message: str
    proposal: ExperimentAiProposal | None = None


type ChatMessage = dict[str, str]
type PostCallable = Callable[..., Any]


def build_experiment_ai_messages(
    snapshot: ExperimentRuntimeSnapshot,
    conversation: Sequence[ChatMessage],
) -> list[ChatMessage]:
    context = {
        "experiment_name": snapshot.experiment_name,
        "session_name": snapshot.session_name,
        "steps": [step.label for step in snapshot.steps],
        "current_step_index": snapshot.current_step_index,
        "current_step": None if snapshot.current_step is None else snapshot.current_step.label,
    }
    messages: list[ChatMessage] = [
        {"role": "system", "content": EXPERIMENT_AI_SYSTEM_PROMPT},
        {
            "role": "system",
            "content": "Current experiment sidebar state JSON:\n"
            + json.dumps(context, ensure_ascii=False),
        },
    ]
    for item in conversation[-16:]:
        role = item.get("role", "")
        content = item.get("content", "")
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    return messages


def parse_experiment_ai_content(content: str) -> ExperimentAiReply:
    raw_text = str(content or "").strip()
    if not raw_text:
        return ExperimentAiReply("模型没有返回内容。")

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        return ExperimentAiReply(raw_text)

    if not isinstance(payload, dict):
        return ExperimentAiReply(raw_text)

    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        return ExperimentAiReply(raw_text)

    proposal = _parse_proposal(payload.get("proposal"))
    return ExperimentAiReply(message.strip(), proposal)


class OpenAICompatibleExperimentClient:
    def __init__(
        self,
        config: AiAssistantConfig,
        *,
        post: PostCallable | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        if not config.is_configured:
            raise ValueError("AI assistant requires base_url, api_key, and model")
        self._config = config
        self._post = httpx.post if post is None else post
        self._timeout_s = timeout_s

    def complete(self, messages: Sequence[ChatMessage]) -> ExperimentAiReply:
        url = f"{self._config.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self._config.model,
            "messages": list(messages),
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = self._post(
                url,
                headers=headers,
                json=payload,
                timeout=self._timeout_s,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            raise RuntimeError(f"AI 服务返回 HTTP {status}") from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"无法连接 AI 服务：{exc}") from exc
        except ValueError as exc:
            raise RuntimeError("AI 服务返回了无效 JSON") from exc

        return parse_experiment_ai_content(_extract_assistant_content(data))


class ExperimentAiRequestWorker(QObject):
    sig_finished = pyqtSignal(object)
    sig_failed = pyqtSignal(str)

    def __init__(
        self,
        client: OpenAICompatibleExperimentClient,
        messages: Sequence[ChatMessage],
    ) -> None:
        super().__init__()
        self._client = client
        self._messages = list(messages)

    @pyqtSlot()
    def run(self) -> None:
        try:
            reply = self._client.complete(self._messages)
        except Exception as exc:  # pragma: no cover - exercised through Qt signal path
            self.sig_failed.emit(str(exc))
            return
        self.sig_finished.emit(reply)


def _extract_assistant_content(data: object) -> str:
    if not isinstance(data, dict):
        raise RuntimeError("AI 服务响应格式不正确")
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("AI 服务响应缺少 choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise RuntimeError("AI 服务响应 choices 格式不正确")
    message = first.get("message")
    if not isinstance(message, dict):
        raise RuntimeError("AI 服务响应缺少 message")
    content = message.get("content")
    if not isinstance(content, str):
        raise RuntimeError("AI 服务响应缺少文本内容")
    return content


def _parse_proposal(raw_proposal: object) -> ExperimentAiProposal | None:
    if raw_proposal is None:
        return None
    if not isinstance(raw_proposal, dict):
        return None

    proposal = ExperimentAiProposal(
        experiment_name=_optional_text(raw_proposal.get("experiment_name")),
        session_name=_optional_text(raw_proposal.get("session_name")),
        steps=_optional_steps(raw_proposal.get("steps")),
    )
    return proposal if proposal.has_values else None


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text if text else None


def _optional_steps(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, list):
        return None
    steps = tuple(str(step).strip() for step in value if str(step).strip())
    return steps


__all__ = [
    "ChatMessage",
    "EXPERIMENT_AI_SYSTEM_PROMPT",
    "ExperimentAiProposal",
    "ExperimentAiReply",
    "ExperimentAiRequestWorker",
    "OpenAICompatibleExperimentClient",
    "build_experiment_ai_messages",
    "parse_experiment_ai_content",
]

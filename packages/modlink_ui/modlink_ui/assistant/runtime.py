from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from modlink_ui.features.live.experiment_runtime import ExperimentRuntimeSnapshot
from modlink_ui.shared.ui_settings.ai import AiAssistantConfig

from .config import (
    ExperimentAiConfig,
)
from .config import (
    config as default_ai_config,
)
from .tools import ExperimentAiAction, ExperimentToolSession

type ChatMessage = dict[str, Any]


class ChatCompletionResponse(Protocol):
    def raise_for_status(self) -> None: ...

    def json(self) -> object: ...


class ChatCompletionPost(Protocol):
    def __call__(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, object],
        timeout: float,
    ) -> ChatCompletionResponse: ...


@dataclass(frozen=True, slots=True)
class ExperimentAiReply:
    message: str
    actions: tuple[ExperimentAiAction, ...] = ()


@dataclass(frozen=True, slots=True)
class ExperimentAiRequest:
    snapshot: ExperimentRuntimeSnapshot
    conversation: tuple[ChatMessage, ...]
    recording_label: str = ""
    annotation_label: str = ""


def _build_experiment_ai_messages(
    request: ExperimentAiRequest,
    *,
    ai_config: ExperimentAiConfig = default_ai_config,
) -> list[ChatMessage]:
    snapshot = request.snapshot
    context = {
        "experiment_name": snapshot.experiment_name,
        "session_name": snapshot.session_name,
        "recording_label": request.recording_label,
        "annotation_label": request.annotation_label,
        "steps": [step.label for step in snapshot.steps],
        "current_step_index": snapshot.current_step_index,
        "current_step": None if snapshot.current_step is None else snapshot.current_step.label,
    }
    messages: list[ChatMessage] = [
        {"role": "system", "content": ai_config.system_prompt},
        {
            "role": "system",
            "content": "Current experiment sidebar state JSON:\n"
            + json.dumps(context, ensure_ascii=False),
        },
    ]
    for item in request.conversation[-16:]:
        role = item.get("role", "")
        content = item.get("content", "")
        if role in {"user", "assistant"} and content:
            messages.append({"role": str(role), "content": str(content)})
    return messages


class OpenAICompatibleExperimentClient:
    def __init__(
        self,
        connection_config: AiAssistantConfig,
        *,
        post: ChatCompletionPost | None = None,
        timeout_s: float = 30.0,
        ai_config: ExperimentAiConfig = default_ai_config,
    ) -> None:
        if not connection_config.is_configured:
            raise ValueError("AI assistant requires base_url, api_key, and model")
        self._connection_config = connection_config
        self._post = httpx.post if post is None else post
        self._timeout_s = timeout_s
        self._ai_config = ai_config

    def complete(self, request: ExperimentAiRequest) -> ExperimentAiReply:
        url = f"{self._connection_config.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._connection_config.api_key}",
            "Content-Type": "application/json",
        }
        tool_session = ExperimentToolSession.from_snapshot(
            request.snapshot,
            recording_label=request.recording_label,
            annotation_label=request.annotation_label,
        )
        request_messages = _build_experiment_ai_messages(
            request,
            ai_config=self._ai_config,
        )
        for _ in range(self._ai_config.max_tool_rounds):
            payload = {
                "model": self._connection_config.model,
                "messages": request_messages,
                "temperature": self._ai_config.temperature,
                "tools": tool_session.openai_tools(),
                "tool_choice": "auto",
            }

            data = self._post_chat_completion(url, headers, payload)
            message = _extract_assistant_message(data)
            tool_calls = _extract_tool_calls(message)
            if not tool_calls:
                message_text = _message_content(message).strip()
                return ExperimentAiReply(
                    message_text or _actions_message(tool_session.actions),
                    tuple(tool_session.actions),
                )

            request_messages.append(
                {
                    "role": "assistant",
                    "content": _message_content(message),
                    "tool_calls": tool_calls,
                }
            )
            for tool_call in tool_calls:
                name, arguments = _parse_tool_call(tool_call)
                result = tool_session.run_tool_call(name, arguments)
                request_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": str(tool_call.get("id", "")),
                        "content": result,
                    }
                )

        actions = tuple(tool_session.actions)
        return ExperimentAiReply(_actions_message(actions), actions=actions)

    def _post_chat_completion(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, object],
    ) -> object:
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

        return data


class ExperimentAiRequestWorker(QObject):
    sig_finished = pyqtSignal(object)
    sig_failed = pyqtSignal(str)

    def __init__(
        self,
        client: OpenAICompatibleExperimentClient,
        request: ExperimentAiRequest,
    ) -> None:
        super().__init__()
        self._client = client
        self._request = request

    @pyqtSlot()
    def run(self) -> None:
        try:
            reply = self._client.complete(self._request)
        except Exception as exc:  # pragma: no cover - exercised through Qt signal path
            self.sig_failed.emit(str(exc))
            return
        self.sig_finished.emit(reply)


def _actions_message(actions: Sequence[ExperimentAiAction]) -> str:
    if actions:
        return "已按你的要求更新实验设置。"
    return "没有执行任何设置更改。"


def _extract_assistant_message(data: object) -> dict[str, object]:
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
    return message


def _message_content(message: dict[str, object]) -> str:
    content = message.get("content")
    if content is None:
        return ""
    if not isinstance(content, str):
        raise RuntimeError("AI 服务响应缺少文本内容")
    return content


def _extract_tool_calls(message: dict[str, object]) -> list[dict[str, object]]:
    tool_calls = message.get("tool_calls")
    if tool_calls is None:
        return []
    if not isinstance(tool_calls, list):
        raise RuntimeError("AI 服务响应 tool_calls 格式不正确")
    normalized: list[dict[str, object]] = []
    for tool_call in tool_calls:
        if not isinstance(tool_call, dict):
            raise RuntimeError("AI 服务响应 tool_call 格式不正确")
        normalized.append(tool_call)
    return normalized


def _parse_tool_call(tool_call: dict[str, object]) -> tuple[str, dict[str, object]]:
    function = tool_call.get("function")
    if not isinstance(function, dict):
        raise RuntimeError("AI tool_call 缺少 function")
    name = function.get("name")
    if not isinstance(name, str) or not name.strip():
        raise RuntimeError("AI tool_call 缺少 function name")
    raw_arguments = function.get("arguments", {})
    if isinstance(raw_arguments, str):
        try:
            parsed_arguments = json.loads(raw_arguments or "{}")
        except json.JSONDecodeError as exc:
            raise RuntimeError("AI tool_call arguments 不是有效 JSON") from exc
    else:
        parsed_arguments = raw_arguments
    if not isinstance(parsed_arguments, dict):
        raise RuntimeError("AI tool_call arguments 必须是对象")
    return name.strip(), dict(parsed_arguments)


__all__ = [
    "ChatMessage",
    "ExperimentAiReply",
    "ExperimentAiRequest",
    "ExperimentAiRequestWorker",
    "OpenAICompatibleExperimentClient",
]

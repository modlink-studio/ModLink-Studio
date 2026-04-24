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
Help the user configure the current live experiment sidebar.
Use tools when the user asks to set or change experiment name, session name, labels, steps, or current step navigation.
Do not control acquisition start/stop, recording, hardware, devices, files, or timing.
After tool calls, summarize what changed in concise Chinese.
If you need more information, ask one short question."""

EXPERIMENT_AI_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "set_experiment_name",
            "description": "Set the live sidebar experiment name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "string", "description": "Experiment name to set."},
                },
                "required": ["value"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_session_name",
            "description": "Set the live sidebar session name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "string", "description": "Session name to set."},
                },
                "required": ["value"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_label",
            "description": "Set a label in the acquisition panel. Use recording_label for the recording label and annotation_label for marker/segment labels.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "enum": ["recording_label", "annotation_label"],
                        "description": "Which label field to set.",
                    },
                    "value": {"type": "string", "description": "Label value to set."},
                },
                "required": ["target", "value"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_steps",
            "description": "Replace the live experiment step queue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Step labels, in order.",
                    },
                },
                "required": ["steps"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "previous_step",
            "description": "Move the current experiment step backward by one step.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "next_step",
            "description": "Move the current experiment step forward by one step.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
]


@dataclass(frozen=True, slots=True)
class ExperimentAiAction:
    name: str
    arguments: dict[str, object]


@dataclass(frozen=True, slots=True)
class ExperimentAiReply:
    message: str
    actions: tuple[ExperimentAiAction, ...] = ()


@dataclass(slots=True)
class ExperimentAiToolState:
    experiment_name: str
    session_name: str
    recording_label: str
    annotation_label: str
    steps: list[str]
    current_step_index: int

    @classmethod
    def from_snapshot(
        cls,
        snapshot: ExperimentRuntimeSnapshot,
        *,
        recording_label: str = "",
        annotation_label: str = "",
    ) -> ExperimentAiToolState:
        return cls(
            experiment_name=snapshot.experiment_name,
            session_name=snapshot.session_name,
            recording_label=recording_label,
            annotation_label=annotation_label,
            steps=[step.label for step in snapshot.steps],
            current_step_index=snapshot.current_step_index,
        )

    def as_dict(self) -> dict[str, object]:
        current_step = None
        if 0 <= self.current_step_index < len(self.steps):
            current_step = self.steps[self.current_step_index]
        return {
            "experiment_name": self.experiment_name,
            "session_name": self.session_name,
            "recording_label": self.recording_label,
            "annotation_label": self.annotation_label,
            "steps": list(self.steps),
            "current_step_index": self.current_step_index,
            "current_step": current_step,
        }


class ExperimentAiToolRunner:
    def __init__(self, state: ExperimentAiToolState) -> None:
        self.state = state
        self.actions: list[ExperimentAiAction] = []

    def run(self, name: str, arguments: dict[str, object]) -> str:
        normalized_name = str(name or "").strip()
        normalized_arguments = dict(arguments)
        handler = getattr(self, f"_run_{normalized_name}", None)
        if handler is None:
            return self._result(False, f"unknown tool: {normalized_name}")

        try:
            message = handler(normalized_arguments)
        except Exception as exc:
            return self._result(False, str(exc))

        self.actions.append(ExperimentAiAction(normalized_name, normalized_arguments))
        return self._result(True, message)

    def _run_set_experiment_name(self, arguments: dict[str, object]) -> str:
        value = _required_text(arguments, "value")
        self.state.experiment_name = value
        arguments["value"] = value
        return "experiment name updated"

    def _run_set_session_name(self, arguments: dict[str, object]) -> str:
        value = _required_text(arguments, "value")
        self.state.session_name = value
        arguments["value"] = value
        return "session name updated"

    def _run_set_label(self, arguments: dict[str, object]) -> str:
        target = _required_text(arguments, "target")
        if target not in {"recording_label", "annotation_label"}:
            raise ValueError("target must be recording_label or annotation_label")
        value = _required_text(arguments, "value")
        setattr(self.state, target, value)
        arguments["target"] = target
        arguments["value"] = value
        return f"{target} updated"

    def _run_set_steps(self, arguments: dict[str, object]) -> str:
        raw_steps = arguments.get("steps")
        if not isinstance(raw_steps, list):
            raise ValueError("steps must be an array")
        steps = [str(step).strip() for step in raw_steps if str(step).strip()]
        self.state.steps = steps
        self.state.current_step_index = 0 if steps else -1
        arguments["steps"] = steps
        return "steps updated"

    def _run_previous_step(self, _arguments: dict[str, object]) -> str:
        if self.state.current_step_index <= 0:
            return "already at first step"
        self.state.current_step_index -= 1
        return "moved to previous step"

    def _run_next_step(self, _arguments: dict[str, object]) -> str:
        if not 0 <= self.state.current_step_index < len(self.state.steps) - 1:
            return "already at last step"
        self.state.current_step_index += 1
        return "moved to next step"

    def _result(self, ok: bool, message: str) -> str:
        return json.dumps(
            {
                "ok": ok,
                "message": message,
                "state": self.state.as_dict(),
            },
            ensure_ascii=False,
        )


type ChatMessage = dict[str, Any]
type PostCallable = Callable[..., Any]


def build_experiment_ai_messages(
    snapshot: ExperimentRuntimeSnapshot,
    conversation: Sequence[ChatMessage],
    *,
    recording_label: str = "",
    annotation_label: str = "",
) -> list[ChatMessage]:
    context = {
        "experiment_name": snapshot.experiment_name,
        "session_name": snapshot.session_name,
        "recording_label": recording_label,
        "annotation_label": annotation_label,
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
            messages.append({"role": str(role), "content": str(content)})
    return messages


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

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        tool_runner: ExperimentAiToolRunner,
    ) -> ExperimentAiReply:
        url = f"{self._config.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }

        request_messages = list(messages)
        for _ in range(8):
            payload = {
                "model": self._config.model,
                "messages": request_messages,
                "temperature": 0.2,
                "tools": EXPERIMENT_AI_TOOLS,
                "tool_choice": "auto",
            }

            data = self._post_chat_completion(url, headers, payload)
            message = _extract_assistant_message(data)
            tool_calls = _extract_tool_calls(message)
            if not tool_calls:
                message_text = _message_content(message).strip()
                return ExperimentAiReply(
                    message_text or self._actions_message(tool_runner.actions),
                    tuple(tool_runner.actions),
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
                result = tool_runner.run(name, arguments)
                request_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": str(tool_call.get("id", "")),
                        "content": result,
                    }
                )

        actions = tuple(tool_runner.actions)
        return ExperimentAiReply(self._actions_message(actions), actions=actions)

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

    @staticmethod
    def _actions_message(actions: Sequence[ExperimentAiAction]) -> str:
        if actions:
            return "已按你的要求更新实验设置。"
        return "没有执行任何设置更改。"


class ExperimentAiRequestWorker(QObject):
    sig_finished = pyqtSignal(object)
    sig_failed = pyqtSignal(str)

    def __init__(
        self,
        client: OpenAICompatibleExperimentClient,
        messages: Sequence[ChatMessage],
        tool_runner: ExperimentAiToolRunner,
    ) -> None:
        super().__init__()
        self._client = client
        self._messages = list(messages)
        self._tool_runner = tool_runner

    @pyqtSlot()
    def run(self) -> None:
        try:
            reply = self._client.complete(self._messages, tool_runner=self._tool_runner)
        except Exception as exc:  # pragma: no cover - exercised through Qt signal path
            self.sig_failed.emit(str(exc))
            return
        self.sig_finished.emit(reply)


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


def _required_text(arguments: dict[str, object], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{key} must not be empty")
    return text


__all__ = [
    "ChatMessage",
    "EXPERIMENT_AI_TOOLS",
    "EXPERIMENT_AI_SYSTEM_PROMPT",
    "ExperimentAiAction",
    "ExperimentAiReply",
    "ExperimentAiToolRunner",
    "ExperimentAiToolState",
    "ExperimentAiRequestWorker",
    "OpenAICompatibleExperimentClient",
    "build_experiment_ai_messages",
]

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from modlink_ui.features.live.experiment_runtime import ExperimentRuntimeSnapshot

type JsonSchema = dict[str, Any]

SET_EXPERIMENT_NAME = "set_experiment_name"
SET_SESSION_NAME = "set_session_name"
SET_LABEL = "set_label"
SET_STEPS = "set_steps"
PREVIOUS_STEP = "previous_step"
NEXT_STEP = "next_step"


@dataclass(frozen=True, slots=True)
class ExperimentAiAction:
    name: str
    arguments: dict[str, object]


@dataclass(slots=True)
class ExperimentDraftState:
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
    ) -> ExperimentDraftState:
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


class ExperimentToolSession:
    def __init__(self, draft: ExperimentDraftState) -> None:
        self.draft = draft
        self.actions: list[ExperimentAiAction] = []

    @classmethod
    def from_snapshot(
        cls,
        snapshot: ExperimentRuntimeSnapshot,
        *,
        recording_label: str = "",
        annotation_label: str = "",
    ) -> ExperimentToolSession:
        return cls(
            ExperimentDraftState.from_snapshot(
                snapshot,
                recording_label=recording_label,
                annotation_label=annotation_label,
            )
        )

    def openai_tools(self) -> list[dict[str, Any]]:
        return _openai_tool_specs()

    def run_tool_call(self, name: str, arguments: dict[str, object]) -> str:
        tool_name = str(name or "").strip()
        normalized_arguments = dict(arguments)

        try:
            if tool_name == SET_EXPERIMENT_NAME:
                message = self._set_experiment_name(normalized_arguments)
            elif tool_name == SET_SESSION_NAME:
                message = self._set_session_name(normalized_arguments)
            elif tool_name == SET_LABEL:
                message = self._set_label(normalized_arguments)
            elif tool_name == SET_STEPS:
                message = self._set_steps(normalized_arguments)
            elif tool_name == PREVIOUS_STEP:
                message = self._previous_step()
            elif tool_name == NEXT_STEP:
                message = self._next_step()
            else:
                return self._result(False, f"unknown tool: {tool_name}")
        except ValueError as exc:
            return self._result(False, str(exc))

        self.actions.append(ExperimentAiAction(tool_name, normalized_arguments))
        return self._result(True, message)

    def _set_experiment_name(self, arguments: dict[str, object]) -> str:
        value = _required_text(arguments, "value")
        self.draft.experiment_name = value
        arguments["value"] = value
        return "experiment name updated"

    def _set_session_name(self, arguments: dict[str, object]) -> str:
        value = _required_text(arguments, "value")
        self.draft.session_name = value
        arguments["value"] = value
        return "session name updated"

    def _set_label(self, arguments: dict[str, object]) -> str:
        target = _required_text(arguments, "target")
        if target not in {"recording_label", "annotation_label"}:
            raise ValueError("target must be recording_label or annotation_label")

        value = _required_text(arguments, "value")
        if target == "recording_label":
            self.draft.recording_label = value
        else:
            self.draft.annotation_label = value

        arguments["target"] = target
        arguments["value"] = value
        return f"{target} updated"

    def _set_steps(self, arguments: dict[str, object]) -> str:
        raw_steps = arguments.get("steps")
        if not isinstance(raw_steps, list):
            raise ValueError("steps must be an array")

        steps = [str(step).strip() for step in raw_steps if str(step).strip()]
        self.draft.steps = steps
        self.draft.current_step_index = 0 if steps else -1
        arguments["steps"] = steps
        return "steps updated"

    def _previous_step(self) -> str:
        if self.draft.current_step_index <= 0:
            return "already at first step"
        self.draft.current_step_index -= 1
        return "moved to previous step"

    def _next_step(self) -> str:
        if not 0 <= self.draft.current_step_index < len(self.draft.steps) - 1:
            return "already at last step"
        self.draft.current_step_index += 1
        return "moved to next step"

    def _result(self, ok: bool, message: str) -> str:
        return json.dumps(
            {
                "ok": ok,
                "message": message,
                "draft": self.draft.as_dict(),
            },
            ensure_ascii=False,
        )


def _openai_tool_specs() -> list[dict[str, Any]]:
    return [
        _openai_tool(
            SET_EXPERIMENT_NAME,
            "Set the live sidebar experiment name.",
            _object_parameters(
                {
                    "value": {
                        "type": "string",
                        "description": "Experiment name to set.",
                    },
                },
                required=("value",),
            ),
        ),
        _openai_tool(
            SET_SESSION_NAME,
            "Set the live sidebar session name.",
            _object_parameters(
                {
                    "value": {
                        "type": "string",
                        "description": "Session name to set.",
                    },
                },
                required=("value",),
            ),
        ),
        _openai_tool(
            SET_LABEL,
            "Set a label in the acquisition panel. Use recording_label for the recording label and annotation_label for marker/segment labels.",
            _object_parameters(
                {
                    "target": {
                        "type": "string",
                        "enum": ["recording_label", "annotation_label"],
                        "description": "Which label field to set.",
                    },
                    "value": {
                        "type": "string",
                        "description": "Label value to set.",
                    },
                },
                required=("target", "value"),
            ),
        ),
        _openai_tool(
            SET_STEPS,
            "Replace the live experiment step queue.",
            _object_parameters(
                {
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Step labels, in order.",
                    },
                },
                required=("steps",),
            ),
        ),
        _openai_tool(
            PREVIOUS_STEP,
            "Move the current experiment step backward by one step.",
            _object_parameters(),
        ),
        _openai_tool(
            NEXT_STEP,
            "Move the current experiment step forward by one step.",
            _object_parameters(),
        ),
    ]


def _openai_tool(name: str, description: str, parameters: JsonSchema) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }


def _object_parameters(
    properties: dict[str, JsonSchema] | None = None,
    *,
    required: tuple[str, ...] = (),
) -> JsonSchema:
    schema: JsonSchema = {
        "type": "object",
        "properties": dict(properties or {}),
        "additionalProperties": False,
    }
    if required:
        schema["required"] = list(required)
    return schema


def _required_text(arguments: dict[str, object], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")

    text = value.strip()
    if not text:
        raise ValueError(f"{key} must not be empty")
    return text


__all__ = [
    "ExperimentAiAction",
]

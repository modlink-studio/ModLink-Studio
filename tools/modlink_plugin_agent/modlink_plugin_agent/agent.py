"""Scaffold-to-full-code orchestration for ModLink plugin generation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from .client import ChatMessage
from .scaffold import run_scaffold_generate
from .verifier import VerificationResult, verify_plugin_project
from .workspace import (
    apply_file_edits,
    normalize_json_object,
    parse_file_edits,
    summarize_project_files,
)


class JsonClient(Protocol):
    def complete_json(self, messages: list[ChatMessage]) -> dict[str, Any]: ...


type VerifyCallable = Callable[[Path], VerificationResult]


@dataclass(frozen=True, slots=True)
class PluginAgentConfig:
    out_dir: Path
    scaffold_command: str | None = None
    overwrite: bool = False
    max_repairs: int = 2


@dataclass(frozen=True, slots=True)
class PluginAgentResult:
    ok: bool
    project_dir: Path
    scaffold_spec: dict[str, Any]
    written_files: tuple[Path, ...] = ()
    repairs: int = 0
    verification_log: str = ""
    error: str = ""


@dataclass(slots=True)
class PluginAgent:
    client: JsonClient
    config: PluginAgentConfig
    verify: VerifyCallable = verify_plugin_project
    _written_files: list[Path] = field(default_factory=list, init=False)

    def generate(self, description: str) -> PluginAgentResult:
        request = description.strip()
        if not request:
            raise ValueError("device description must not be empty")

        scaffold_spec = _extract_scaffold_spec(
            self.client.complete_json(_build_scaffold_messages(request))
        )
        scaffold_result = run_scaffold_generate(
            scaffold_spec,
            self.config.out_dir,
            scaffold_command=self.config.scaffold_command,
            overwrite=self.config.overwrite,
        )
        project_dir = Path(str(scaffold_result["projectDir"])).resolve()
        normalized_spec = normalize_json_object(scaffold_result.get("spec"))
        plugin_name = str(normalized_spec.get("pluginName") or scaffold_spec.get("pluginName"))

        edit_payload = self.client.complete_json(
            _build_code_messages(request, normalized_spec, summarize_project_files(project_dir))
        )
        self._apply_payload(project_dir, plugin_name, edit_payload)

        verification = self.verify(project_dir)
        repairs = 0
        while not verification.ok and repairs < self.config.max_repairs:
            repairs += 1
            repair_payload = self.client.complete_json(
                _build_repair_messages(
                    request,
                    normalized_spec,
                    summarize_project_files(project_dir),
                    verification.log,
                )
            )
            self._apply_payload(project_dir, plugin_name, repair_payload)
            verification = self.verify(project_dir)

        return PluginAgentResult(
            ok=verification.ok,
            project_dir=project_dir,
            scaffold_spec=normalized_spec,
            written_files=tuple(self._written_files),
            repairs=repairs,
            verification_log=verification.log,
            error="" if verification.ok else "verification failed",
        )

    def _apply_payload(self, project_dir: Path, plugin_name: str, payload: object) -> None:
        edits = parse_file_edits(payload)
        self._written_files.extend(apply_file_edits(project_dir, plugin_name, edits))


def _extract_scaffold_spec(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("scaffoldSpec", "spec", "plugin"):
        value = payload.get(key)
        if isinstance(value, dict):
            return dict(value)
    return dict(payload)


def _build_scaffold_messages(description: str) -> list[ChatMessage]:
    return [
        {
            "role": "system",
            "content": (
                "You design ModLink Python driver plugin scaffold specs. "
                "Return JSON only. Do not include markdown. The JSON object must match this shape: "
                "{pluginName, displayName, deviceId, providers, dataArrival, driverKind, "
                "dependencies, streams}. streams items use {streamKey, displayName, payloadType, "
                "sampleRateHz, chunkSize, channelNames, unit}. payloadType is signal, raster, "
                "field, or video. dataArrival is push, poll, or unsure. driverKind is driver or loop."
            ),
        },
        {
            "role": "user",
            "content": f"Create the scaffold spec for this device:\n{description}",
        },
    ]


def _build_code_messages(
    description: str,
    scaffold_spec: dict[str, Any],
    project_files: str,
) -> list[ChatMessage]:
    return [
        _code_system_message(),
        {
            "role": "user",
            "content": (
                "Turn this scaffold into a fuller ModLink driver plugin. "
                "Return JSON only with a files array. Each file is a full replacement file, not a diff.\n\n"
                f"Device description:\n{description}\n\n"
                f"Scaffold spec:\n{scaffold_spec}\n\n"
                f"Current project files:\n{project_files}"
            ),
        },
    ]


def _build_repair_messages(
    description: str,
    scaffold_spec: dict[str, Any],
    project_files: str,
    verification_log: str,
) -> list[ChatMessage]:
    return [
        _code_system_message(),
        {
            "role": "user",
            "content": (
                "Repair the generated ModLink driver plugin. Return JSON only with a files array. "
                "Replace only files needed to fix the verification failure.\n\n"
                f"Device description:\n{description}\n\n"
                f"Scaffold spec:\n{scaffold_spec}\n\n"
                f"Verification log:\n{verification_log[-12000:]}\n\n"
                f"Current project files:\n{project_files}"
            ),
        },
    ]


def _code_system_message() -> ChatMessage:
    return {
        "role": "system",
        "content": (
            "You write ModLink Python driver plugins. Return JSON only: "
            '{"files":[{"path":"relative/path.py","content":"full file content"}]}. '
            "Do not return shell commands. Do not write outside the project. Allowed files are "
            "pyproject.toml, README.md, tests/*.py, and Python modules inside the plugin package. "
            "Drivers must implement the modlink_sdk Driver or LoopDriver contract, expose "
            "create_driver(), return stable StreamDescriptor objects, and emit FrameEnvelope data "
            "with shapes matching the descriptors. Tests must be offline and deterministic."
        ),
    }

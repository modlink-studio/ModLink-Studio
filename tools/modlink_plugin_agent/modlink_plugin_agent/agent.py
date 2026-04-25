"""Scaffold-to-full-code orchestration for ModLink plugin generation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from .client import ChatMessage
from .scaffold import generate_scaffold_project
from .verifier import VerificationResult, verify_plugin_project
from .workspace import (
    apply_file_edits,
    parse_file_edits,
    summarize_project_files,
)


class JsonClient(Protocol):
    def complete_json(self, messages: list[ChatMessage]) -> dict[str, Any]: ...


type VerifyCallable = Callable[[Path], VerificationResult]


@dataclass(frozen=True, slots=True)
class PluginAgentConfig:
    out_dir: Path
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
        scaffold_result = generate_scaffold_project(
            scaffold_spec,
            self.config.out_dir,
            overwrite=self.config.overwrite,
        )
        project_dir = scaffold_result.project_dir.resolve()
        normalized_spec = scaffold_result.spec.as_json()
        plugin_name = scaffold_result.spec.plugin_name

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
            "External plugin projects depend on modlink-studio, not a separately published "
            "modlink-sdk package; driver code still imports SDK types from modlink_sdk. "
            "Drivers must implement the modlink_sdk Driver or LoopDriver contract. create_driver() "
            "must return a driver instance. SearchResult requires title as the first argument; "
            "use SearchResult(title='Device name', subtitle='', device_id='name.01', extra={...}). "
            "StreamDescriptor requires device_id, stream_key, payload_type, nominal_sample_rate_hz, "
            "chunk_size, and optional channel_names/display_name/metadata. FrameEnvelope requires "
            "device_id, stream_key, timestamp_ns, and data. Emitted data shapes must match the "
            "descriptors. Tests must be offline, deterministic, and aligned with these SDK "
            "dataclass signatures. Streaming/background-thread tests must stop threads cleanly and "
            "must not rely on exhausted mock side_effect iterators that raise StopIteration in a "
            "background thread."
        ),
    }

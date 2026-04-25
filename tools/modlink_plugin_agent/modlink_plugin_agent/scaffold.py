"""Deterministic Python scaffold writer used by the plugin agent."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

type DriverKind = Literal["driver", "loop"]
type DataArrival = Literal["push", "poll", "unsure"]
type PayloadType = Literal["signal", "raster", "field", "video"]

_DEVICE_ID_PATTERN = re.compile(r"^[a-z0-9_]+\.[0-9]{2,}$")
_DEVICE_ID_WITH_SUFFIX_PATTERN = re.compile(r"^([a-z0-9_]+)[._-]([0-9]{2,})$")
_MODLINK_STUDIO_DEPENDENCY = "modlink-studio>=0.3.0rc1"
_PAYLOAD_TYPES = {"signal", "raster", "field", "video"}
_DATA_ARRIVALS = {"push", "poll", "unsure"}
_DRIVER_KINDS = {"driver", "loop"}


@dataclass(frozen=True, slots=True)
class StreamSpec:
    stream_key: str
    display_name: str
    payload_type: PayloadType
    sample_rate_hz: float
    chunk_size: int
    channel_names: tuple[str, ...]
    unit: str = ""
    raster_length: int | None = None
    field_height: int | None = None
    field_width: int | None = None
    video_height: int | None = None
    video_width: int | None = None


@dataclass(frozen=True, slots=True)
class DriverSpec:
    plugin_name: str
    project_name: str
    class_name: str
    display_name: str
    device_id: str
    providers: tuple[str, ...]
    driver_kind: DriverKind
    driver_reason: str
    data_arrival: DataArrival
    dependencies: tuple[str, ...]
    streams: tuple[StreamSpec, ...]

    def as_json(self) -> dict[str, Any]:
        return {
            "pluginName": self.plugin_name,
            "projectName": self.project_name,
            "className": self.class_name,
            "displayName": self.display_name,
            "deviceId": self.device_id,
            "providers": list(self.providers),
            "driverKind": self.driver_kind,
            "driverReason": self.driver_reason,
            "dataArrival": self.data_arrival,
            "dependencies": list(self.dependencies),
            "streams": [
                {
                    "streamKey": stream.stream_key,
                    "displayName": stream.display_name,
                    "payloadType": stream.payload_type,
                    "sampleRateHz": stream.sample_rate_hz,
                    "chunkSize": stream.chunk_size,
                    "channelNames": list(stream.channel_names),
                    "unit": stream.unit,
                    "rasterLength": stream.raster_length,
                    "fieldHeight": stream.field_height,
                    "fieldWidth": stream.field_width,
                    "videoHeight": stream.video_height,
                    "videoWidth": stream.video_width,
                }
                for stream in self.streams
            ],
        }


@dataclass(frozen=True, slots=True)
class GeneratedProject:
    project_dir: Path
    written_files: tuple[Path, ...]
    commands: dict[str, str]
    spec: DriverSpec

    def as_json(self) -> dict[str, Any]:
        return {
            "ok": True,
            "projectDir": str(self.project_dir),
            "writtenFiles": [str(path) for path in self.written_files],
            "commands": self.commands,
            "spec": self.spec.as_json(),
        }


class ScaffoldExistsError(Exception):
    def __init__(self, project_dir: Path) -> None:
        super().__init__(f"Target directory already exists: {project_dir}")
        self.project_dir = project_dir


def generate_scaffold_project(
    raw_spec: dict[str, Any],
    out_dir: Path,
    *,
    overwrite: bool = False,
) -> GeneratedProject:
    spec = validate_scaffold_spec(raw_spec)
    project_dir = out_dir.resolve() / spec.plugin_name
    if project_dir.exists():
        if not overwrite:
            raise ScaffoldExistsError(project_dir)
        shutil.rmtree(project_dir)

    package_dir = project_dir / spec.plugin_name
    tests_dir = project_dir / "tests"
    package_dir.mkdir(parents=True)
    tests_dir.mkdir()

    files = (
        (project_dir / "pyproject.toml", _render_pyproject(spec)),
        (project_dir / "README.md", _render_readme(spec)),
        (project_dir / "LICENSE", _render_license()),
        (project_dir / ".gitignore", _render_gitignore()),
        (package_dir / "__init__.py", _render_init(spec)),
        (package_dir / "driver.py", _render_driver(spec)),
        (package_dir / "factory.py", _render_factory(spec)),
        (tests_dir / "test_smoke.py", _render_smoke_test(spec)),
    )
    written_files: list[Path] = []
    for path, content in files:
        path.write_text(content, encoding="utf-8")
        written_files.append(path)

    return GeneratedProject(
        project_dir=project_dir,
        written_files=tuple(written_files),
        commands={
            "install": "python -m pip install -e .",
            "test": "python -m pytest",
            "runHost": "python -m modlink_studio",
            "checkEntryPoints": (
                'python -c "from importlib.metadata import entry_points; '
                "print(sorted(ep.name for ep in entry_points(group='modlink.drivers')))\""
            ),
        },
        spec=spec,
    )


def validate_scaffold_spec(raw_spec: dict[str, Any]) -> DriverSpec:
    plugin_name = _sanitize_identifier(_required_text(raw_spec, "pluginName"))
    if not plugin_name:
        raise ValueError("pluginName must contain at least one letter or number")

    device_id = _normalize_device_id(raw_spec.get("deviceId"), plugin_name)

    providers = tuple(_split_tokens(raw_spec.get("providers"), normalize=True))
    if not providers:
        raise ValueError("providers must contain at least one provider token")

    streams = tuple(
        _validate_stream(item, index)
        for index, item in enumerate(_required_list(raw_spec, "streams"))
    )
    if not streams:
        raise ValueError("streams must contain at least one stream")

    data_arrival = _choice(raw_spec.get("dataArrival"), _DATA_ARRIVALS, "unsure")
    driver_kind = _choice(
        raw_spec.get("driverKind"), _DRIVER_KINDS, _recommended_driver_kind(data_arrival)
    )
    dependencies = tuple(
        dict.fromkeys(
            [
                _MODLINK_STUDIO_DEPENDENCY,
                "numpy>=2.3.3",
                *[
                    dependency
                    for dependency in _split_tokens(raw_spec.get("dependencies"))
                    if not _is_modlink_dependency(dependency)
                ],
            ]
        )
    )

    return DriverSpec(
        plugin_name=plugin_name,
        project_name=plugin_name.replace("_", "-"),
        class_name=_to_pascal_case(plugin_name),
        display_name=str(raw_spec.get("displayName") or _to_pascal_case(plugin_name)).strip(),
        device_id=device_id,
        providers=providers,
        driver_kind=driver_kind,
        driver_reason=_driver_reason(data_arrival, driver_kind),
        data_arrival=data_arrival,
        dependencies=dependencies,
        streams=streams,
    )


def _validate_stream(raw_stream: object, index: int) -> StreamSpec:
    if not isinstance(raw_stream, dict):
        raise ValueError(f"streams[{index}] must be an object")
    stream_key = _normalize_token(_required_text(raw_stream, "streamKey"))
    if not stream_key:
        raise ValueError(f"streams[{index}].streamKey must contain at least one letter or number")
    payload_type = _choice(raw_stream.get("payloadType"), _PAYLOAD_TYPES, "signal")
    sample_rate_hz = _positive_float(
        raw_stream.get("sampleRateHz"), f"streams[{index}].sampleRateHz"
    )
    chunk_size = _positive_int(raw_stream.get("chunkSize"), f"streams[{index}].chunkSize")
    channel_names = tuple(_split_tokens(raw_stream.get("channelNames")))
    if not channel_names:
        raise ValueError(f"streams[{index}].channelNames must contain at least one channel")
    return StreamSpec(
        stream_key=stream_key,
        display_name=str(raw_stream.get("displayName") or _to_title_words(stream_key)).strip(),
        payload_type=payload_type,
        sample_rate_hz=sample_rate_hz,
        chunk_size=chunk_size,
        channel_names=channel_names,
        unit=str(raw_stream.get("unit") or "").strip(),
        raster_length=_optional_positive_int(raw_stream.get("rasterLength"), default=128),
        field_height=_optional_positive_int(raw_stream.get("fieldHeight"), default=48),
        field_width=_optional_positive_int(raw_stream.get("fieldWidth"), default=48),
        video_height=_optional_positive_int(raw_stream.get("videoHeight"), default=480),
        video_width=_optional_positive_int(raw_stream.get("videoWidth"), default=640),
    )


def _render_driver(spec: DriverSpec) -> str:
    base_class = "LoopDriver" if spec.driver_kind == "loop" else "Driver"
    descriptors = ",\n".join(_render_descriptor(stream, spec.device_id) for stream in spec.streams)
    shape_lines = "\n".join(
        f"# - {stream.stream_key} ({stream.payload_type}): {_expected_shape(stream)}"
        for stream in spec.streams
    )
    return f'''"""{spec.display_name} driver implementation.

Expected FrameEnvelope.data shapes for this scaffold:
{shape_lines}
"""

from __future__ import annotations

import time

import numpy as np

from modlink_sdk import {base_class}, FrameEnvelope, SearchResult, StreamDescriptor

DEFAULT_DEVICE_ID = "{spec.device_id}"


class {spec.class_name}Driver({base_class}):
    """Starter template for a ModLink Python driver plugin."""

    supported_providers = {spec.providers!r}

    def __init__(self) -> None:
        super().__init__()
        self._connected = False
        self._seq = 0

    @property
    def device_id(self) -> str:
        return DEFAULT_DEVICE_ID

    @property
    def display_name(self) -> str:
        return "{spec.display_name}"

    def descriptors(self) -> list[StreamDescriptor]:
        return [
{descriptors}
        ]

    def search(self, provider: str) -> list[SearchResult]:
        if provider not in self.supported_providers:
            expected = ", ".join(self.supported_providers)
            raise ValueError(
                f"{{type(self).__name__}} search provider must be one of: {{expected}}"
            )

        # TODO: Replace this stub with real device discovery.
        return []

    def connect_device(self, config: SearchResult) -> None:
        # TODO: Use config.extra to establish the real device connection.
        self._connected = True
        self._seq = 0

    def disconnect_device(self) -> None:
        self._connected = False
        self._seq = 0

    def emit_frame(
        self,
        stream_key: str,
        data: np.ndarray,
        *,
        timestamp_ns: int | None = None,
        seq: int | None = None,
    ) -> None:
        super().emit_frame(
            FrameEnvelope(
                device_id=self.device_id,
                stream_key=stream_key,
                timestamp_ns=time.time_ns() if timestamp_ns is None else int(timestamp_ns),
                data=np.ascontiguousarray(data),
                seq=self._seq if seq is None else int(seq),
            )
        )

    def next_seq(self) -> int:
        value = self._seq
        self._seq += 1
        return value
{_render_driver_methods(spec)}
'''


def _render_descriptor(stream: StreamSpec, device_id: str) -> str:
    metadata = _stream_metadata(stream)
    metadata_line = f",\n                metadata={metadata!r}" if metadata else ""
    return f'''            StreamDescriptor(
                device_id=self.device_id,
                stream_key="{stream.stream_key}",
                payload_type="{stream.payload_type}",
                nominal_sample_rate_hz={stream.sample_rate_hz},
                chunk_size={stream.chunk_size},
                channel_names={stream.channel_names!r}{metadata_line},
                display_name="{stream.display_name}",
            )'''


def _render_driver_methods(spec: DriverSpec) -> str:
    if spec.driver_kind == "loop":
        loop_interval = max(
            1,
            min(round(1000 * stream.chunk_size / stream.sample_rate_hz) for stream in spec.streams),
        )
        return f"""
    loop_interval_ms = {loop_interval}

    def on_loop_started(self) -> None:
        if not self._connected:
            raise RuntimeError("device is not connected")
        self._seq = 0

    def on_loop_stopped(self) -> None:
        pass

    def loop(self) -> None:
        # TODO: Poll the real device, build one payload, and emit it with emit_frame().
        raise NotImplementedError(f"{{type(self).__name__}} must implement loop")
"""
    return """
    def start_streaming(self) -> None:
        if not self._connected:
            raise RuntimeError("device is not connected")
        # TODO: Start callback registration, async tasks, or background workers here.
        raise NotImplementedError(f"{type(self).__name__} must implement start_streaming")

    def stop_streaming(self) -> None:
        # TODO: Tear down streaming resources here.
        raise NotImplementedError(f"{type(self).__name__} must implement stop_streaming")
"""


def _render_factory(spec: DriverSpec) -> str:
    return f'''"""Factory function for {spec.class_name}Driver."""

from __future__ import annotations

from .driver import {spec.class_name}Driver


def create_driver() -> {spec.class_name}Driver:
    return {spec.class_name}Driver()
'''


def _render_init(spec: DriverSpec) -> str:
    return f'''"""{spec.display_name} driver plugin package."""

from __future__ import annotations

from .driver import {spec.class_name}Driver
from .factory import create_driver

__all__ = ["{spec.class_name}Driver", "create_driver"]
'''


def _render_pyproject(spec: DriverSpec) -> str:
    deps = "\n".join(f'    "{dependency}",' for dependency in spec.dependencies)
    return f'''[project]
name = "{spec.project_name}"
version = "0.2.0"
description = "{spec.display_name} driver plugin for ModLink Studio"
readme = "README.md"
license = "MIT"
license-files = ["LICENSE"]
requires-python = ">=3.13"
dependencies = [
{deps}
]

[project.entry-points."modlink.drivers"]
{spec.project_name} = "{spec.plugin_name}.factory:create_driver"

[project.urls]
Documentation = "https://modlink-studio.github.io/sdk"

[build-system]
requires = ["setuptools>=80"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["{spec.plugin_name}*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
'''


def _render_readme(spec: DriverSpec) -> str:
    stream_lines = "\n".join(
        f"- **{stream.display_name}**: stream_key=`{stream.stream_key}` | "
        f"payload=`{stream.payload_type}` | rate=`{stream.sample_rate_hz}` | "
        f"chunk=`{stream.chunk_size}` | shape=`{_expected_shape(stream)}`"
        for stream in spec.streams
    )
    return f"""# {spec.display_name} Driver Plugin

This project is a ModLink Python driver plugin generated by the ModLink plugin agent.

## Driver Summary

- **Plugin package**: `{spec.plugin_name}`
- **Project name**: `{spec.project_name}`
- **Device ID**: `{spec.device_id}`
- **Providers**: `{", ".join(spec.providers)}`
- **Base class**: `{"LoopDriver" if spec.driver_kind == "loop" else "Driver"}`
- **Why this base class**: {spec.driver_reason}

## Streams

{stream_lines}

## Install

```bash
python -m pip install -e .
```

## Test

```bash
python -m pytest
```
"""


def _render_smoke_test(spec: DriverSpec) -> str:
    first_stream = spec.streams[0]
    return f'''from __future__ import annotations

from {spec.plugin_name}.factory import create_driver


def test_create_driver_returns_ready_instance() -> None:
    driver = create_driver()

    assert driver.device_id == "{spec.device_id}"
    assert driver.display_name == "{spec.display_name}"

    descriptors = driver.descriptors()
    assert len(descriptors) == {len(spec.streams)}
    assert descriptors[0].stream_key == "{first_stream.stream_key}"
'''


def _render_license() -> str:
    return """MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def _render_gitignore() -> str:
    return """.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
dist/
build/
"""


def _stream_metadata(stream: StreamSpec) -> dict[str, str | int]:
    metadata: dict[str, str | int] = {}
    if stream.unit:
        metadata["unit"] = stream.unit
    if stream.payload_type == "raster" and stream.raster_length is not None:
        metadata["length"] = stream.raster_length
    if stream.payload_type == "field":
        if stream.field_height is not None:
            metadata["height"] = stream.field_height
        if stream.field_width is not None:
            metadata["width"] = stream.field_width
    if stream.payload_type == "video":
        if stream.video_height is not None:
            metadata["height"] = stream.video_height
        if stream.video_width is not None:
            metadata["width"] = stream.video_width
    return metadata


def _expected_shape(stream: StreamSpec) -> str:
    if stream.payload_type == "signal":
        return f"[{len(stream.channel_names)}, {stream.chunk_size}]"
    if stream.payload_type == "raster":
        return f"[{len(stream.channel_names)}, {stream.chunk_size}, {stream.raster_length}]"
    if stream.payload_type == "field":
        return f"[{len(stream.channel_names)}, {stream.chunk_size}, {stream.field_height}, {stream.field_width}]"
    return f"[{len(stream.channel_names)}, {stream.chunk_size}, {stream.video_height}, {stream.video_width}]"


def _sanitize_identifier(value: str) -> str:
    normalized = re.sub(r"[^\w\s-]", "", str(value))
    normalized = re.sub(r"[-\s]+", "_", normalized).lower().strip("_")
    if not normalized:
        return ""
    return f"plugin_{normalized}" if normalized[0].isdigit() else normalized


def _normalize_token(value: object) -> str:
    normalized = re.sub(r"[^a-z0-9_]+", "_", str(value or "").strip().lower())
    return re.sub(r"_+", "_", normalized).strip("_")


def _to_pascal_case(value: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in re.split(r"[_-]+", value) if part)


def _to_title_words(value: str) -> str:
    return " ".join(
        part[:1].upper() + part[1:] for part in _normalize_token(value).split("_") if part
    )


def _make_device_id(plugin_name: str) -> str:
    return f"{_normalize_token(plugin_name)}.01"


def _normalize_device_id(value: object, plugin_name: str) -> str:
    if value is None or str(value).strip() == "":
        return _make_device_id(plugin_name)

    raw = str(value).strip().lower().replace("-", "_")
    cleaned = re.sub(r"[^a-z0-9_.]+", "_", raw)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_.")
    if _DEVICE_ID_PATTERN.match(cleaned):
        return cleaned

    suffix_match = _DEVICE_ID_WITH_SUFFIX_PATTERN.match(cleaned)
    if suffix_match is not None:
        return f"{suffix_match.group(1)}.{suffix_match.group(2)}"

    token = _normalize_token(cleaned)
    if token:
        return f"{token}.01"
    return _make_device_id(plugin_name)


def _split_tokens(value: object, *, normalize: bool = False) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, tuple):
        raw_items = list(value)
    elif isinstance(value, str):
        raw_items = value.split(",")
    elif value is None:
        raw_items = []
    else:
        raw_items = [str(value)]
    tokens: list[str] = []
    for item in raw_items:
        token = _normalize_token(item) if normalize else str(item).strip()
        if token and token not in tokens:
            tokens.append(token)
    return tokens


def _is_modlink_dependency(value: str) -> bool:
    name = re.split(r"[<>=!~\[]", value, maxsplit=1)[0].strip().lower().replace("_", "-")
    return name in {"modlink-sdk", "modlink-studio"}


def _required_text(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{key} must not be empty")
    return text


def _required_list(raw: dict[str, Any], key: str) -> list[object]:
    value = raw.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be an array")
    return value


def _choice(value: object, choices: set[str], default: str) -> Any:
    text = str(value or default).strip().lower()
    return text if text in choices else default


def _positive_int(value: object, field_name: str) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a positive integer") from exc
    if parsed <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return parsed


def _optional_positive_int(value: object, *, default: int) -> int:
    if value is None or value == "":
        return default
    return _positive_int(value, "optional integer field")


def _positive_float(value: object, field_name: str) -> float:
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a positive number") from exc
    if parsed <= 0:
        raise ValueError(f"{field_name} must be a positive number")
    return parsed


def _recommended_driver_kind(data_arrival: DataArrival) -> DriverKind:
    return "loop" if data_arrival == "poll" else "driver"


def _driver_reason(data_arrival: DataArrival, driver_kind: DriverKind) -> str:
    if data_arrival == "push":
        if driver_kind == "driver":
            return "The device pushes data into the driver, so Driver is the natural default."
        return "The device pushes data, but LoopDriver was kept for a polling-style implementation."
    if data_arrival == "poll":
        if driver_kind == "loop":
            return "The driver polls the device on its own loop, so LoopDriver is recommended."
        return (
            "The driver polls the device, but Driver is valid when lifecycle control stays custom."
        )
    if driver_kind == "driver":
        return "Driver is the safer starting point until the device runtime pattern is clear."
    return "LoopDriver was selected even though the data arrival pattern is still uncertain."

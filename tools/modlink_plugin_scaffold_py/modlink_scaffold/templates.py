"""Template rendering for scaffold files."""

from __future__ import annotations

import json
from datetime import datetime

from .i18n import get_copy
from .models import DriverSpec, Language, StreamSpec


def render_expected_shape(stream: StreamSpec) -> str:
    """Render expected data shape for a stream."""
    if stream.payload_type == "signal":
        return f"[{len(stream.channel_names)}, {stream.chunk_size}]"
    if stream.payload_type == "raster":
        return f"[{len(stream.channel_names)}, {stream.chunk_size}, {stream.raster_length}]"
    if stream.payload_type == "field":
        return f"[{len(stream.channel_names)}, {stream.chunk_size}, {stream.field_height}, {stream.field_width}]"
    return f"[{len(stream.channel_names)}, {stream.chunk_size}, {stream.video_height}, {stream.video_width}]"


def render_metadata(stream: StreamSpec) -> str | None:
    """Render metadata JSON for a stream."""
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
    return json.dumps(metadata, indent=4) if metadata else None


def render_descriptor(stream: StreamSpec) -> str:
    """Render StreamDescriptor code for a stream."""
    metadata = render_metadata(stream)
    metadata_line = ""
    if metadata:
        formatted = metadata.replace("\n", "\n                ")
        metadata_line = f",\n                metadata={formatted}"

    return f"""StreamDescriptor(
                device_id=self.device_id,
                stream_key="{stream.stream_key}",
                payload_type="{stream.payload_type}",
                nominal_sample_rate_hz={stream.sample_rate_hz},
                chunk_size={stream.chunk_size},
                channel_names={json.dumps(stream.channel_names)}{metadata_line},
                display_name="{stream.display_name}",
            )"""


def render_driver_methods(spec: DriverSpec) -> str:
    """Render driver-specific methods."""
    if spec.driver_kind == "loop":
        # Calculate loop interval from streams
        intervals = [
            round(1000 * stream.chunk_size / stream.sample_rate_hz)
            for stream in spec.streams
        ]
        loop_interval = max(1, min(intervals)) if intervals else 100

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
        raise NotImplementedError(f"{type(self).__name__} must implement loop")
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


def render_driver_py(spec: DriverSpec) -> str:
    """Render driver.py content."""
    descriptors = ",\n".join(render_descriptor(s) for s in spec.streams)
    shape_lines = "\n".join(
        f"# - {s.stream_key} ({s.payload_type}): {render_expected_shape(s)}"
        for s in spec.streams
    )

    base_class = "LoopDriver" if spec.driver_kind == "loop" else "Driver"

    return f"""\"\"\"{spec.display_name} driver implementation.

Expected FrameEnvelope.data shapes for this scaffold:
{shape_lines}
\"\"\"from __future__ import annotations

import time

import numpy as np

from modlink_sdk import {base_class}, FrameEnvelope, SearchResult, StreamDescriptor

DEFAULT_DEVICE_ID = "{spec.device_id}"


class {spec.className}Driver({base_class}):
    \"\"\"Official starter template for a ModLink Python driver plugin.\"\"\"supported_providers = {json.dumps(spec.providers)}

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
                f"{type(self).__name__} search provider must be one of: {expected}"
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
{render_driver_methods(spec)}"""


def render_factory_py(spec: DriverSpec) -> str:
    """Render factory.py content."""
    return f"""\"\"\"Factory function for {spec.className}Driver.\"\"\"from __future__ import annotations

from .driver import {spec.className}Driver


def create_driver() -> {spec.className}Driver:
    return {spec.className}Driver()
"""


def render_init_py(spec: DriverSpec) -> str:
    """Render __init__.py content."""
    return f"""\"\"\"{spec.display_name} driver plugin package.\"\"\"from __future__ import annotations

from .driver import {spec.className}Driver
from .factory import create_driver

__all__ = ["{spec.className}Driver", "create_driver"]
"""


def render_pyproject_toml(spec: DriverSpec) -> str:
    """Render pyproject.toml content."""
    deps_lines = "\n".join(f'    "{dep}",' for dep in spec.dependencies)

    return f"""[project]
name = "{spec.project_name}"
version = "0.2.0"
description = "{spec.display_name} driver plugin for ModLink Studio"
readme = "README.md"
license = "MIT"
license-files = ["LICENSE"]
requires-python = ">=3.13"
dependencies = [
{deps_lines}
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
"""


def render_readme(spec: DriverSpec, language: Language) -> str:
    """Render README.md content."""
    copy = get_copy(language)
    stream_lines = "\n".join(
        f"- **{s.display_name}**: stream_key=`{s.stream_key}` | payload=`{s.payload_type}` | rate=`{s.sample_rate_hz}` | chunk=`{s.chunk_size}` | shape=`{render_expected_shape(s)}`"
        for s in spec.streams
    )

    base_class = "LoopDriver" if spec.driver_kind == "loop" else "Driver"
    install_cmd = copy.get("install_command", "Install: python -m pip install -e .")
    test_cmd = copy.get("test_command", "Test: python -m pytest")
    run_cmd = copy.get("run_command", "Run: python -m modlink_studio")

    if language == "zh":
        return f"""# {spec.display_name} Driver 插件

这是为 ModLink Studio 生成的新版官方 Python driver 模板。

## Driver 摘要

- **插件包名**：`{spec.plugin_name}`
- **项目名**：`{spec.project_name}`
- **Device ID**：`{spec.device_id}`
- **Providers**：`{", ".join(spec.providers)}`
- **基类**：`{base_class}`
- **选择原因**：{spec.driver_reason}

## Streams

{stream_lines}

## 推荐工作流

1. 在 `search()` 里返回真实的 `SearchResult`
2. 在 `connect_device()` / `disconnect_device()` 中补完连接逻辑
3. 在 streaming 或 loop 路径里产出真实 payload，并通过 `emit_frame()` 发出
4. 运行测试：

```bash
python -m pytest
```

## 安装

```bash
python -m pip install -e .
```

## 运行宿主

```bash
python -m modlink_studio
```

## 说明

- 这个模板固定使用 MIT 许可证。
- `driver.py` 已经给出了 `emit_frame()` 和 `next_seq()` 辅助方法。
- 发布前建议补齐你自己的 README 细节、项目链接和设备说明。
"""

    return f"""# {spec.display_name} Driver Plugin

This project is the official starter template for a ModLink Python driver plugin.

## Driver Summary

- **Plugin package**: `{spec.plugin_name}`
- **Project name**: `{spec.project_name}`
- **Device ID**: `{spec.device_id}`
- **Providers**: `{", ".join(spec.providers)}`
- **Base class**: `{base_class}`
- **Why this base class**: {spec.driver_reason}

## Streams

{stream_lines}

## Recommended workflow

1. Return real `SearchResult` entries from `search()`
2. Implement real device connection logic in `connect_device()` / `disconnect_device()`
3. Produce real payloads in the loop or streaming path and emit them with `emit_frame()`
4. Run the generated test suite:

```bash
python -m pytest
```

## Install

```bash
python -m pip install -e .
```

## Run the host

```bash
python -m modlink_studio
```

## Notes

- This template always generates an MIT-licensed driver project.
- `driver.py` already includes `emit_frame()` and `next_seq()` helpers.
- Before publishing, replace the placeholder README details with the real device documentation.
"""


def render_license() -> str:
    """Render LICENSE content."""
    year = datetime.now().year
    return f"""MIT License

Copyright (c) {year}

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


def render_gitignore() -> str:
    """Render .gitignore content."""
    return """.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
dist/
build/
"""


def render_smoke_test(spec: DriverSpec) -> str:
    """Render test_smoke.py content."""
    first_stream = spec.streams[0] if spec.streams else None
    stream_key = first_stream.stream_key if first_stream else "stream_1"

    return f"""from __future__ import annotations

from {spec.plugin_name}.factory import create_driver


def test_create_driver_returns_ready_instance() -> None:
    driver = create_driver()

    assert driver.device_id == "{spec.device_id}"
    assert driver.display_name == "{spec.display_name}"

    descriptors = driver.descriptors()
    assert len(descriptors) == {len(spec.streams)}
    assert descriptors[0].stream_key == "{stream_key}"
"""
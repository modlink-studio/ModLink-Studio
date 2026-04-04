"""File renderers for generated plugin scaffolds."""

from __future__ import annotations

from textwrap import indent

from ..i18n import Language
from .context import NextStepCommands
from .spec import DriverSpec, StreamSpec


def generate_driver_py(spec: DriverSpec) -> str:
    stream_shape_lines = "\n".join(
        f"# - {stream.modality} ({stream.payload_type}): {stream.expected_shape}"
        for stream in spec.streams
    )
    descriptor_block = ",\n".join(render_descriptor(stream) for stream in spec.streams)

    return f'''"""{spec.display_name} driver implementation.

Expected FrameEnvelope.data shapes for this scaffold:
{stream_shape_lines}
"""

from __future__ import annotations

import time

import numpy as np

from modlink_sdk import {spec.driver_base_class}, FrameEnvelope, SearchResult, StreamDescriptor

DEFAULT_DEVICE_ID = "{spec.device_id}"


class {spec.class_name}Driver({spec.driver_base_class}):
    supported_providers = {spec.providers_tuple}
{indent(render_driver_header(spec), "    ")}

    @property
    def device_id(self) -> str:
        return DEFAULT_DEVICE_ID

    @property
    def display_name(self) -> str:
        return "{spec.display_name}"

    def descriptors(self) -> list[StreamDescriptor]:
        return [
{indent(descriptor_block, "            ")}
        ]

    def search(self, provider: str) -> list[SearchResult]:
        if provider not in self.supported_providers:
            expected = ", ".join(self.supported_providers)
            raise ValueError(
                f"{{type(self).__name__}} search provider must be one of: {{expected}}"
            )

        # TODO: Replace this stub with real device discovery.
        # Branch here if different providers need different discovery logic.
        return []

    def connect_device(self, config: SearchResult) -> None:
        # TODO: Use config.extra to establish a real device connection.
        self._connected = True
        self._seq = 0

    def disconnect_device(self) -> None:
        try:
            self.stop_streaming()
        except NotImplementedError:
            pass
        self._connected = False
        self._seq = 0

    def emit_frame(
        self,
        modality: str,
        data: np.ndarray,
        *,
        timestamp_ns: int | None = None,
        seq: int | None = None,
        extra: dict[str, object] | None = None,
    ) -> None:
        super().emit_frame(
            FrameEnvelope(
                device_id=self.device_id,
                modality=modality,
                timestamp_ns=time.time_ns() if timestamp_ns is None else int(timestamp_ns),
                data=np.ascontiguousarray(data),
                seq=self._seq if seq is None else int(seq),
                extra={{}} if extra is None else dict(extra),
            )
        )

    def next_seq(self) -> int:
        value = self._seq
        self._seq += 1
        return value
{render_driver_methods(spec)}
'''


def generate_factory_py(spec: DriverSpec) -> str:
    return f'''"""Factory function for {spec.class_name} driver."""

from __future__ import annotations

from .driver import {spec.class_name}Driver


def create_driver() -> {spec.class_name}Driver:
    return {spec.class_name}Driver()
'''


def generate_init_py(spec: DriverSpec) -> str:
    return f'''"""{spec.display_name} driver plugin package."""

from __future__ import annotations

from .driver import {spec.class_name}Driver
from .factory import create_driver

__all__ = ["{spec.class_name}Driver", "create_driver"]
'''


def generate_pyproject_toml(spec: DriverSpec) -> str:
    deps = "\n".join(f'    "{dependency}",' for dependency in spec.dependencies)

    return f"""[project]
name = "{spec.project_name}"
version = "0.2.0"
description = "{spec.display_name} driver plugin for ModLink Studio"
readme = "README.md"
license = "GPL-3.0-or-later"
requires-python = ">=3.13"
dependencies = [
{deps}
]

[project.urls]
Documentation = "https://modlink-studio.github.io/sdk"

[project.entry-points."modlink.drivers"]
{spec.entry_point_name} = "{spec.plugin_name}.factory:create_driver"

[build-system]
requires = ["setuptools>=80"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["{spec.plugin_name}*"]
"""


def generate_readme(
    spec: DriverSpec,
    commands: NextStepCommands,
    language: Language,
) -> str:
    return _generate_readme_zh(spec, commands) if language == "zh" else _generate_readme_en(spec, commands)


def _generate_readme_en(spec: DriverSpec, commands: NextStepCommands) -> str:
    stream_lines = "\n".join(render_stream_readme_line(stream) for stream in spec.streams)
    remaining_work = "\n".join(
        f"- Implement real frame production for `{stream.modality}` with shape `{stream.expected_shape}`."
        for stream in spec.streams
    )

    return f"""# {spec.display_name} Driver Plugin

{spec.display_name} driver plugin scaffold for ModLink Studio.

## Driver Summary

- **Plugin package**: `{spec.plugin_name}`
- **Project name**: `{spec.project_name}`
- **Device ID**: `{spec.device_id}`
- **Providers**: `{spec.providers_display}`
- **Base class**: `{spec.driver_base_class}`
- **Why this base class**: {spec.driver_reason}

## Streams

{stream_lines}

## Installation Model

- Keep one driver project per directory.
- If you have multiple drivers, keep them as sibling directories and install each one separately.
- After several driver projects are installed into the same Python environment, ModLink Studio can discover all of their `modlink.drivers` entry points.
- This driver package only depends on `modlink-sdk` plus its transport dependencies.
- The host environment is assumed to already have `modlink-studio` installed separately.
- The examples below use `python -m pip` because it is portable, but any environment manager is acceptable.

## Install

### Install this driver from this project directory

```bash
{commands.install_plugin_in_project}
```

### Install additional sibling drivers

```bash
python -m pip install -e ../another_driver
```

## Run ModLink Studio

```bash
{commands.run_module}
```

Or, if your environment exposes console scripts:

```bash
{commands.run_script}
```

## Test entry point discovery

```bash
{commands.test}
```

## Remaining Work

- Implement `search()` so it returns real `SearchResult` entries.
- Finish the transport-specific logic in `connect_device()` and `disconnect_device()`.
{remaining_work}

## Notes

- `driver.py` already includes `emit_frame()` and `next_seq()` helpers for the 0.2.0 callback/context runtime.
- Keep each stream's `modality`, `payload_type`, and expected frame shape stable across the driver lifetime.
- The canonical module launch form is `python -m modlink_studio`.
- Before publishing the driver, add your own `LICENSE`, README details, and project URLs.
"""


def _generate_readme_zh(spec: DriverSpec, commands: NextStepCommands) -> str:
    stream_lines = "\n".join(render_stream_readme_line_zh(stream) for stream in spec.streams)
    remaining_work = "\n".join(
        f"- 为 `{stream.modality}` 实现真实的数据产出逻辑，shape 应保持为 `{stream.expected_shape}`。"
        for stream in spec.streams
    )

    return f"""# {spec.display_name} Driver 插件

这是为 ModLink Studio 生成的 `{spec.display_name}` driver 插件脚手架。

## Driver 摘要

- **插件包名**：`{spec.plugin_name}`
- **项目名**：`{spec.project_name}`
- **Device ID**：`{spec.device_id}`
- **Providers**：`{spec.providers_display}`
- **基类**：`{spec.driver_base_class}`
- **选择原因**：{spec.driver_reason}

## Streams

{stream_lines}

## 安装模型

- 建议一个 driver 项目对应一个目录。
- 如果你有多个 drivers，建议把它们放成同级目录，再分别安装到同一个 Python 环境。
- 当多个 driver 项目都安装到同一个 Python 环境后，ModLink Studio 就能通过 `modlink.drivers` entry points 发现它们。
- 这个 driver 包本身只依赖 `modlink-sdk` 和它自己的传输层依赖。
- 这里默认宿主环境已经另外安装好了 `modlink-studio`。
- 下面使用 `python -m pip` 只是为了示例最通用，并不限制你使用其他环境管理工具。

## 安装

### 在当前项目目录安装这个 driver

```bash
{commands.install_plugin_in_project}
```

### 安装其他同级 driver

```bash
python -m pip install -e ../another_driver
```

## 运行 ModLink Studio

```bash
{commands.run_module}
```

如果你的环境暴露了 console script，也可以使用：

```bash
{commands.run_script}
```

## 检查 entry point 发现结果

```bash
{commands.test}
```

## 剩余工作

- 实现 `search()`，让它返回真实的 `SearchResult`。
- 在 `connect_device()` 和 `disconnect_device()` 中补完传输层逻辑。
{remaining_work}

## 说明

- `driver.py` 已经为 0.2.0 的 callback/context runtime 提供了 `emit_frame()` 和 `next_seq()` 两个辅助方法。
- 每个 stream 的 `modality`、`payload_type` 和期望 shape 在 driver 生命周期内应该保持稳定。
- 推荐的模块启动形式是 `python -m modlink_studio`。
- 公开分发这个 driver 之前，建议补齐自己的 `LICENSE`、README 细节和项目链接。
"""


def render_descriptor(stream: StreamSpec) -> str:
    metadata = stream.metadata
    metadata_line = ""
    if metadata:
        metadata_line = f",\n    metadata={metadata!r}"

    return (
        "StreamDescriptor(\n"
        f"    device_id=self.device_id,\n"
        f'    modality="{stream.modality}",\n'
        f'    payload_type="{stream.payload_type}",\n'
        f"    nominal_sample_rate_hz={stream.sample_rate_hz},\n"
        f"    chunk_size={stream.chunk_size},\n"
        f"    channel_names={stream.channel_names!r},\n"
        f'    display_name="{stream.display_name}"'
        f"{metadata_line}\n"
        ")"
    )


def render_driver_header(spec: DriverSpec) -> str:
    lines: list[str] = []
    if spec.driver_kind == "loop":
        lines.extend(
            [
                f"loop_interval_ms = {spec.suggested_loop_interval_ms}",
                "",
            ]
        )
    lines.extend(
        [
            "def __init__(self) -> None:",
            "    super().__init__()",
            "    self._connected = False",
            "    self._seq = 0",
        ]
    )
    return "\n".join(lines)


def render_driver_methods(spec: DriverSpec) -> str:
    if spec.driver_kind == "loop":
        return """
    def on_loop_started(self) -> None:
        if not self._connected:
            raise RuntimeError("device is not connected")
        self._seq = 0

    def on_loop_stopped(self) -> None:
        pass

    def loop(self) -> None:
        # TODO: Poll the device, build payloads, and emit frames with emit_frame().
        raise NotImplementedError(f"{type(self).__name__} must implement loop")
"""

    return """
    def start_streaming(self) -> None:
        if not self._connected:
            raise RuntimeError("device is not connected")
        # TODO: Start callback registration, background workers, or async streaming here.
        raise NotImplementedError(f"{type(self).__name__} must implement start_streaming")

    def stop_streaming(self) -> None:
        # TODO: Stop streaming resources here.
        raise NotImplementedError(f"{type(self).__name__} must implement stop_streaming")
"""


def render_stream_readme_line(stream: StreamSpec) -> str:
    metadata = stream.metadata
    metadata_suffix = ""
    if metadata:
        metadata_suffix = f" | metadata={metadata}"
    return (
        f"- **{stream.display_name}**: modality=`{stream.modality}` | "
        f"payload=`{stream.payload_type}` | rate=`{stream.sample_rate_hz}` | "
        f"chunk=`{stream.chunk_size}` | shape=`{stream.expected_shape}`{metadata_suffix}"
    )


def render_stream_readme_line_zh(stream: StreamSpec) -> str:
    metadata = stream.metadata
    metadata_suffix = ""
    if metadata:
        metadata_suffix = f" | metadata={metadata}"
    return (
        f"- **{stream.display_name}**：modality=`{stream.modality}` | "
        f"payload=`{stream.payload_type}` | rate=`{stream.sample_rate_hz}` | "
        f"chunk=`{stream.chunk_size}` | shape=`{stream.expected_shape}`{metadata_suffix}"
    )

import {getCopy} from "../lib/i18n.js";
import type {DriverSpec, Language, PreviewBundle, StreamSpec, SummaryMetric, SummaryViewModel} from "../lib/types.js";

function renderExpectedShape(stream: StreamSpec): string {
  if (stream.payloadType === "signal") {
    return `[${stream.channelNames.length}, ${stream.chunkSize}]`;
  }
  if (stream.payloadType === "raster") {
    return `[${stream.channelNames.length}, ${stream.chunkSize}, ${stream.rasterLength}]`;
  }
  if (stream.payloadType === "field") {
    return `[${stream.channelNames.length}, ${stream.chunkSize}, ${stream.fieldHeight}, ${stream.fieldWidth}]`;
  }
  return `[${stream.channelNames.length}, ${stream.chunkSize}, ${stream.videoHeight}, ${stream.videoWidth}]`;
}

function renderMetadata(stream: StreamSpec): string | null {
  const metadata: Record<string, string | number> = {};
  if (stream.unit) {
    metadata.unit = stream.unit;
  }
  if (stream.payloadType === "raster" && stream.rasterLength !== undefined) {
    metadata.length = stream.rasterLength;
  }
  if (stream.payloadType === "field") {
    if (stream.fieldHeight !== undefined) {
      metadata.height = stream.fieldHeight;
    }
    if (stream.fieldWidth !== undefined) {
      metadata.width = stream.fieldWidth;
    }
  }
  if (stream.payloadType === "video") {
    if (stream.videoHeight !== undefined) {
      metadata.height = stream.videoHeight;
    }
    if (stream.videoWidth !== undefined) {
      metadata.width = stream.videoWidth;
    }
  }
  return Object.keys(metadata).length === 0 ? null : JSON.stringify(metadata, null, 4);
}

function renderDescriptor(stream: StreamSpec): string {
  const metadata = renderMetadata(stream);
  const metadataLine = metadata ? `,\n                metadata=${metadata.replace(/\n/g, "\n                ")}` : "";
  return `StreamDescriptor(
                device_id=self.device_id,
                modality="${stream.modality}",
                payload_type="${stream.payloadType}",
                nominal_sample_rate_hz=${stream.sampleRateHz},
                chunk_size=${stream.chunkSize},
                channel_names=${JSON.stringify(stream.channelNames)}${metadataLine},
                display_name="${stream.displayName}",
            )`;
}

function renderDriverMethods(spec: DriverSpec): string {
  if (spec.driverKind === "loop") {
    const loopInterval = Math.max(
      1,
      Math.min(...spec.streams.map((stream) => Math.round((1000 * stream.chunkSize) / stream.sampleRateHz))),
    );
    return `
    loop_interval_ms = ${loopInterval}

    def on_loop_started(self) -> None:
        if not self._connected:
            raise RuntimeError("device is not connected")
        self._seq = 0

    def on_loop_stopped(self) -> None:
        pass

    def loop(self) -> None:
        # TODO: Poll the real device, build one payload, and emit it with emit_frame().
        raise NotImplementedError(f"{type(self).__name__} must implement loop")
`;
  }

  return `
    def start_streaming(self) -> None:
        if not self._connected:
            raise RuntimeError("device is not connected")
        # TODO: Start callback registration, async tasks, or background workers here.
        raise NotImplementedError(f"{type(self).__name__} must implement start_streaming")

    def stop_streaming(self) -> None:
        # TODO: Tear down streaming resources here.
        raise NotImplementedError(f"{type(self).__name__} must implement stop_streaming")
`;
}

export function renderDriverPy(spec: DriverSpec): string {
  const descriptors = spec.streams.map(renderDescriptor).join(",\n");
  const shapeLines = spec.streams
    .map((stream) => `# - ${stream.modality} (${stream.payloadType}): ${renderExpectedShape(stream)}`)
    .join("\n");

  return `"""${spec.displayName} driver implementation.

Expected FrameEnvelope.data shapes for this scaffold:
${shapeLines}
"""

from __future__ import annotations

import time

import numpy as np

from modlink_sdk import ${spec.driverKind === "loop" ? "LoopDriver" : "Driver"}, FrameEnvelope, SearchResult, StreamDescriptor

DEFAULT_DEVICE_ID = "${spec.deviceId}"


class ${spec.className}Driver(${spec.driverKind === "loop" ? "LoopDriver" : "Driver"}):
    """Official starter template for a ModLink Python driver plugin."""

    supported_providers = ${JSON.stringify(spec.providers)}

    def __init__(self) -> None:
        super().__init__()
        self._connected = False
        self._seq = 0

    @property
    def device_id(self) -> str:
        return DEFAULT_DEVICE_ID

    @property
    def display_name(self) -> str:
        return "${spec.displayName}"

    def descriptors(self) -> list[StreamDescriptor]:
        return [
${descriptors}
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
                extra={} if extra is None else dict(extra),
            )
        )

    def next_seq(self) -> int:
        value = self._seq
        self._seq += 1
        return value
${renderDriverMethods(spec)}`;
}

export function renderFactoryPy(spec: DriverSpec): string {
  return `"""Factory function for ${spec.className}Driver."""

from __future__ import annotations

from .driver import ${spec.className}Driver


def create_driver() -> ${spec.className}Driver:
    return ${spec.className}Driver()
`;
}

export function renderInitPy(spec: DriverSpec): string {
  return `"""${spec.displayName} driver plugin package."""

from __future__ import annotations

from .driver import ${spec.className}Driver
from .factory import create_driver

__all__ = ["${spec.className}Driver", "create_driver"]
`;
}

export function renderPyprojectToml(spec: DriverSpec): string {
  const deps = spec.dependencies.map((dependency) => `    "${dependency}",`).join("\n");
  return `[project]
name = "${spec.projectName}"
version = "0.2.0"
description = "${spec.displayName} driver plugin for ModLink Studio"
readme = "README.md"
license = "MIT"
license-files = ["LICENSE"]
requires-python = ">=3.13"
dependencies = [
${deps}
]

[project.entry-points."modlink.drivers"]
${spec.projectName} = "${spec.pluginName}.factory:create_driver"

[project.urls]
Documentation = "https://modlink-studio.github.io/sdk"

[build-system]
requires = ["setuptools>=80"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["${spec.pluginName}*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
`;
}

export function renderReadme(spec: DriverSpec, language: Language): string {
  const streamLines = spec.streams
    .map((stream) => `- **${stream.displayName}**: modality=\`${stream.modality}\` | payload=\`${stream.payloadType}\` | rate=\`${stream.sampleRateHz}\` | chunk=\`${stream.chunkSize}\` | shape=\`${renderExpectedShape(stream)}\``)
    .join("\n");

  if (language === "zh") {
    return `# ${spec.displayName} Driver 插件

这是为 ModLink Studio 生成的新版官方 Python driver 模板。

## Driver 摘要

- **插件包名**：\`${spec.pluginName}\`
- **项目名**：\`${spec.projectName}\`
- **Device ID**：\`${spec.deviceId}\`
- **Providers**：\`${spec.providers.join(", ")}\`
- **基类**：\`${spec.driverKind === "loop" ? "LoopDriver" : "Driver"}\`
- **选择原因**：${spec.driverReason}

## Streams

${streamLines}

## 推荐工作流

1. 在 \`search()\` 里返回真实的 \`SearchResult\`
2. 在 \`connect_device()\` / \`disconnect_device()\` 中补完连接逻辑
3. 在 streaming 或 loop 路径里产出真实 payload，并通过 \`emit_frame()\` 发出
4. 运行测试：

\`\`\`bash
python -m pytest
\`\`\`

## 安装

\`\`\`bash
python -m pip install -e .
\`\`\`

## 运行宿主

\`\`\`bash
python -m modlink_studio
\`\`\`

## 说明

- 这个模板固定使用 MIT 许可证。
- \`driver.py\` 已经给出了 \`emit_frame()\` 和 \`next_seq()\` 辅助方法。
- 发布前建议补齐你自己的 README 细节、项目链接和设备说明。
`;
  }

  return `# ${spec.displayName} Driver Plugin

This project is the official starter template for a ModLink Python driver plugin.

## Driver Summary

- **Plugin package**: \`${spec.pluginName}\`
- **Project name**: \`${spec.projectName}\`
- **Device ID**: \`${spec.deviceId}\`
- **Providers**: \`${spec.providers.join(", ")}\`
- **Base class**: \`${spec.driverKind === "loop" ? "LoopDriver" : "Driver"}\`
- **Why this base class**: ${spec.driverReason}

## Streams

${streamLines}

## Recommended workflow

1. Return real \`SearchResult\` entries from \`search()\`
2. Implement real device connection logic in \`connect_device()\` / \`disconnect_device()\`
3. Produce real payloads in the loop or streaming path and emit them with \`emit_frame()\`
4. Run the generated test suite:

\`\`\`bash
python -m pytest
\`\`\`

## Install

\`\`\`bash
python -m pip install -e .
\`\`\`

## Run the host

\`\`\`bash
python -m modlink_studio
\`\`\`

## Notes

- This template always generates an MIT-licensed driver project.
- \`driver.py\` already includes \`emit_frame()\` and \`next_seq()\` helpers.
- Before publishing, replace the placeholder README details with the real device documentation.
`;
}

export function renderLicense(): string {
  return `MIT License

Copyright (c) ${new Date().getFullYear()}

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
`;
}

export function renderGitIgnore(): string {
  return `.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
dist/
build/
`;
}

export function renderSmokeTest(spec: DriverSpec): string {
  const firstStream = spec.streams[0];
  return `from __future__ import annotations

from ${spec.pluginName}.factory import create_driver


def test_create_driver_returns_ready_instance() -> None:
    driver = create_driver()

    assert driver.device_id == "${spec.deviceId}"
    assert driver.display_name == "${spec.displayName}"

    descriptors = driver.descriptors()
    assert len(descriptors) == ${spec.streams.length}
    assert descriptors[0].modality == "${firstStream?.modality ?? "stream_1"}"
`;
}

function summarizeMetrics(spec: DriverSpec, language: Language): SummaryMetric[] {
  const copy = getCopy(language);
  return [
    {label: copy.deviceIdLabel, value: spec.deviceId},
    {label: copy.providersLabel, value: spec.providers.join(", ")},
    {label: copy.driverKindLabel, value: spec.driverKind === "loop" ? "LoopDriver" : "Driver"},
    {label: copy.dataArrivalLabel, value: copy.dataArrivalSummaryOptions[spec.dataArrival]},
    {label: copy.streamCountLabel, value: String(spec.streams.length)},
  ];
}

export function renderSummary(spec: DriverSpec, language: Language): SummaryViewModel {
  const copy = getCopy(language);
  return {
    kind: "ready",
    title: copy.summaryTitle,
    hero: {
      displayName: spec.displayName,
      pluginName: spec.pluginName,
      deviceId: spec.deviceId,
    },
    metrics: summarizeMetrics(spec, language),
  };
}

export function buildPreviewBundle(spec: DriverSpec | null, cwd: string, language: Language, errors: string[]): PreviewBundle {
  const copy = getCopy(language);
  if (spec === null) {
    return {
      summary: {
        kind: "invalid",
        title: copy.summaryTitle,
        message: copy.invalidSummaryMessage,
        errors,
      },
      driver: copy.invalidPreviewPlaceholder,
      pyproject: copy.invalidPreviewPlaceholder,
      readme: copy.invalidPreviewPlaceholder,
    };
  }
  return {
      summary: renderSummary(spec, language),
    driver: renderDriverPy(spec),
    pyproject: renderPyprojectToml(spec),
    readme: renderReadme(spec, language),
  };
}

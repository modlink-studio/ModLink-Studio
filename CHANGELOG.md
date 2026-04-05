# Changelog

## [0.2.0] - Unreleased

### Changed

- `modlink_sdk` / `modlink_core` 已切换到纯 Python runtime，不再沿用 `0.1.x` 的 Qt-style driver API。
- `modlink_studio_qml` 与 `packages/modlink_new_ui` 持续承接新的 QML UI 重构，Qt Widgets 与 QML 继续并行维护。
- 根工作区开发环境现在默认覆盖 `modlink-server`，`uv sync --dev` 后即可直接运行 server 入口与测试。

### Added

- 新增 `modlink-server` 应用，用于承载当前的 FastAPI server host。
- 录制完成与录制失败的 UI 提示会明确展示 session、recording_id 和保存路径，便于确认结果目录。
- 根仓库补齐 `ruff`、`pre-commit`、`.editorconfig`、`.gitattributes` 等基础开发规范。

### Tooling

- `tools/modlink_plugin_scaffold` 已从 Python 应用链路中拆出，重写为独立的 React + Ink npm 工具。
- `tools/modlink_plugin_scaffold` 现在使用 `Biome` 负责 TypeScript lint 与 format。

### Removed

- 删除历史 `deprecated/` 目录，不再保留旧实现入口。

### Notes

- `0.2.0` 的发布边界固定为“稳定采集、录制、保存”。
- 录制回放整体延后到 `0.3.0`，届时会与 `Experiment / Session / Protocol` 工作流一起实现。

# Changelog

本文件记录 ModLink Studio 的重要变更。

## [0.3.0rc1] - Unreleased

### Summary

`0.3.0rc1` 是当前 `0.3.0` 工作线上的首个发布候选版本。

这一版本的重点不是在 `0.1.x` 基础上继续堆叠功能，而是把项目从以 Qt 风格 driver 为中心的实现，重构为以纯 Python runtime 为中心的结构。`0.2.0` 主要完成的是边界重整与基础链路稳定化，为后续版本的实验工作流、回放能力和 AI 辅助能力打地基。

在 UI 方向上，`0.1.x` 实际上只有一条以 Qt Widgets 为主的界面路线；`0.2.0` 则首次明确开始推进新的 UI 方向。这里的 `new UI` 不是单指某一个新界面，而是两条并行推进的方向：

- 一条是基于 QML 的新桌面 UI 路线
- 一条是以 FastAPI server host 为边界、为后续 HTML / Web UI 做准备的服务化路线

这样做不是为了简单“多做一个 UI”，而是因为随着实时预览类型、界面层级和后续交互复杂度增加，Qt Widgets 在表达能力、组织方式和后续演进空间上的局限已经越来越明显，因此需要为后续版本提前建立新的 UI / host 路线。

`0.2.0` 当前锁定的发布边界是：

- 安装与启动
- 设备搜索与连接
- 实时流预览
- 开始 / 停止采集
- 录制与保存
- 插件安装与外部 driver 接入
  - `0.2.0` 公开分发面收口为单主包 `modlink-studio`

录制回放不属于 `0.2.0` 的发布范围，已整体延后到 `0.3.0`。

这一版本的公开安装入口以 **PyPI** 为准；`TestPyPI` 只用于发布前 rehearsal，不作为日常安装源。

`0.2.0` 的 `TestPyPI rehearsal` 已完成；正式稳定版使用 `0.2.0`，公开安装入口以 PyPI 为准。

---

### Breaking Changes

- 从 `0.1.x` 的 Qt-style driver API 切换到新的纯 Python runtime driver 模型
- `modlink_sdk` 与 `modlink_core` 不再以 Qt 作为运行时前提
- 现有 `0.1.x` driver 与 `0.2.0` 不兼容，需要迁移到新的 runtime-oriented driver API
- Monorepo 内部边界重新整理，明确区分为三类：
  - 基础包：
    - `modlink_sdk`
    - `modlink_core`
    - `modlink_ui`
    - `modlink_ui_qt_qml`
  - 宿主入口：
    - `modlink_studio`
    - `modlink_studio_qml`
    - `modlink_server`
  - 开发工具：
    - `tools/modlink_plugin_scaffold`

---

### Added

#### Runtime / Core

- 引入以 `ModLinkEngine` 为中心的运行时结构
- 引入 `DriverPortal`、`StreamBus`、`AcquisitionBackend`、`SettingsService` 等核心能力
- 增加后端事件流和 snapshot 风格的状态传播方式
- 将更多采集、设置和状态同步逻辑收回到 runtime / backend 侧

#### Application Hosts

- 新增 `modlink_server`，作为 FastAPI 形式的 server host
- 新增 `modlink_studio_qml`，承载 QML UI 宿主方向
- `modlink_studio` 继续作为主桌面宿主入口保留
- `modlink_server` 当前并不等于完整 Web UI，但它已经把后续 HTML / Web 前端所需的 host 边界先建立出来

#### UI / Preview

- `0.1.x` 的单一 Qt Widgets UI 路线在 `0.2.0` 中开始扩展为 Widgets + new UI 并行结构
- `new UI` 在当前阶段包含两个方向：
  - 基于 QML 的新桌面 UI
  - 基于 FastAPI host 的服务化边界，为后续 HTML / Web UI 做准备
- 新增 `modlink_ui_qt_qml`，承载新的 QML UI 方向
- 增加 QML 侧 preview controller / preview store / preview pipeline
- 补齐录制完成与录制失败时的结果提示，UI 可明确看到 session、recording_id 和保存路径
- Qt Widgets 主页面补齐空状态提示，避免无流时出现空白展示页

#### Plugin / Ecosystem

- `modlink_plugin_scaffold` 从主运行时链路中拆出，转为独立开发工具
- 新的脚手架工具改写为 React + Ink 的 npm 工具
- 官方驱动从主仓库拆出，迁移到独立仓库 `ModLink-Studio-Plugins`，并改为通过主包插件管理命令 + GitHub 发布物安装
- 外部 driver 开发路径明确为：
  - 主要依赖仓库内的 `modlink-sdk` 契约
  - 按需依赖仓库内的 `modlink-core`
  - 使用 `modlink.drivers` entry points 暴露 driver

#### Testing / Tooling

- 补齐和扩展了以下测试覆盖：
  - 纯 Python runtime
  - stream bus 行为
  - storage utilities / writers
  - QML smoke tests
  - preview 相关 UI 行为
- 根仓库加入 `ruff`、`pre-commit`、`.editorconfig`、`.gitattributes`
- `tools/modlink_plugin_scaffold` 增加 `Biome`，负责 TypeScript lint / format
- 根工作区开发环境现在默认可以覆盖 `modlink_server` 的测试与入口

---

### Changed

#### Architecture

- 以 runtime 为中心重构项目结构，降低 UI 对系统语义的直接承担
- 将更多系统行为从 UI 侧逻辑收束到 backend / runtime 服务
- 明确 bridge 层的职责是适配，而不是承载新的后端语义

#### Driver Model

- 收紧 driver 最小公共契约
- 强化基于 entry point 的插件发现策略
- 对损坏的 entry point、无效 driver 定义和未知 payload 维持 fail-fast 行为

#### Acquisition / Recording

- 重整 acquisition backend 与录制生命周期控制
- 重新梳理 marker / segment 相关链路
- 固定 `recording.json`、`annotations/`、`streams/` 的基本录制目录结构，为后续回放提供稳定输入基础

#### UI Structure

- 调整 `modlink_ui` 的页面和主界面组织方式
- 明确从 `0.1.x` 的单一 Widgets UI，过渡到 Widgets 与 QML/new UI 并行的结构
- 开始推进 new UI 的原因，是 Qt Widgets 在复杂实时预览、后续界面扩展和表现层组织上的局限逐渐显现
- 这里的 new UI 不只是一套 QML 界面，也包括以 `modlink_server` 为入口的服务化 host 边界，用于承接后续 HTML / Web UI
- QML UI 继续沿新结构迭代，Widgets 与 QML 维持并行
- 主页面与采集面板的默认交互更明确，不再依赖隐式状态理解

#### Documentation

- 更新安装说明、driver 开发说明和项目结构说明
- 公开安装与分发表述统一切到 PyPI / TestPyPI rehearsal 口径
- 将路线图正式纳入仓库，并要求实现内容同步更新 `ROADMAP.md`

---

### Fixed

- 修复 `SignalStreamView` 测试中的构造签名回归
- 修复 `modlink_server` 在根工作区开发环境中缺少测试依赖的问题
- 改进 Windows 下 settings 原子写入的稳定性，降低并发写入时的 `PermissionError` 风险
- 改善 widgets / QML 采集结果提示，使录制结果更容易被用户确认

---

### Removed

- 删除历史 `deprecated/` 目录，不再保留旧实现入口
- 移除旧的 in-app Python 版 plugin scaffold 路线，改为显式独立工具
- 不再把录制回放视作 `0.2.0` 的发布前置能力

---

### Plugin Management

`0.2.0` 当前提供以下官方驱动：

- Host Camera
- Host Microphone
- OpenBCI Ganglion

当前阶段的插件安装方式：

- 先安装 `modlink-studio`
- 再运行 `modlink-plugin install <plugin_id>`
- 官方驱动索引与 wheel 资产由独立仓库 `ModLink-Studio-Plugins` 提供

当前命令集主要覆盖官方驱动；插件索引已经改为远端 JSON manifest，后续版本会继续扩展为更通用的插件管理工具。

---

### Migration Notes

从 `0.1.x` 升级到 `0.2.0` 时，需要注意：

1. 旧 driver 需要迁移到新的 runtime-oriented driver API
2. 外部 driver 应优先依赖仓库内的 SDK 契约：
   - `modlink-sdk`
   - 设备自身的传输层依赖
3. 只有在确实需要 runtime 服务时，才额外依赖仓库内的 `modlink-core`
4. 插件发现基于 `modlink.drivers` entry points
5. 新 driver 项目建议从 `modlink_plugin_scaffold` 开始
6. `0.2.0` 的公开安装入口以单主包 `modlink-studio` 为准；`TestPyPI` 只用于发布前 rehearsal

---

### Known Limitations

- UI 仍处于适配期，Qt Widgets 与 QML 继续并行演进
- Backend 已脱离 Qt，但 bridge 与 host 集成仍有继续打磨空间
- `Experiment / Participant / Session / Protocol` 不属于 `0.2.0`
- AI 辅助工作流不属于 `0.2.0`
- Web UI 不属于 `0.2.0`
- 录制回放已明确延后到 `0.3.0`

---

### Notes on Release Scope

`0.2.0` 的目标不是“做完所有规划中的能力”，而是先把基础采集链路做稳：

- install
- launch
- search devices
- connect
- preview streams
- start / stop acquisition
- record and save
- install plugins through `modlink-plugin`

这一版本是后续能力的结构基础：

- `0.3.x`：实验工作流与回放
- `0.4.x`：AI 辅助 session 管理
- `0.5.x`：更广泛的生态与外部接口

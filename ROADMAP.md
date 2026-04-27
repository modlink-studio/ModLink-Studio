# ModLink Studio Roadmap

本文档记录当前版本边界、后续路线和明确不做的方向。它不是设计草稿合集；已经完成或废弃的探索只保留结论。

## 当前位置

当前主开发线是 `0.3.0rc2`。这一版建立在 `0.2.0` 的纯 Python runtime 基线上，重点补齐：

- recording replay
- analysis-first export
- widgets 主宿主里的 Replay 页面
- live experiment sidebar 与 AI assistant 原型
- 外部 driver plugin author skill

分支约定：

- `legacy/0.2.x`：维护 `0.2.x` 稳定线
- `wip/0.3.0`：当前 `0.3.0` / `0.3.0rc2` 开发线
- `main`：是否切到 `0.3.0rc2`，在 rc 发布验证后再决定

## 产品原则

- `modlink-studio` 继续作为公开安装入口，外部 driver plugin 依赖主包并通过 `modlink.drivers` entry point 被宿主发现。
- 主仓库只维护宿主、SDK、core、UI 和插件管理入口；官方驱动源码和发布资产由独立插件仓库维护。
- `recording` 是最小数据资产，`session` 和 `experiment` 是上层组织关系，不反向塑造 recording 的内部结构。
- Core 保持纯 Python runtime；Qt 相关行为只留在 UI / bridge 层。
- 不再维护 npm scaffold 或自研 Python plugin AI agent；外部插件开发转向 `tools/modlink-plugin-author/SKILL.md`。
- 不为了未来 Web/QML 路线提前保留当前用不到的宿主包、适配层或扩展点。

## 0.3.0rc2

目标：发布第二个 `0.3.0` 候选版本，修复 rc1 验证时发现的 UI 细节问题。

已完成：

- 版本号统一到 `0.3.0rc2`
- 修复 Windows 下 QFluentWidgets ComboBox popup 外层透明边框问题
- 官方插件仓库已发布兼容 `0.3.0rc1+` 的 rc 版本，并验证插件安装链路
- TestPyPI 发布流程按 `0.3.0rc2` 产物完整跑通
- 从干净 `.venv-testpypi` 安装 `modlink-studio==0.3.0rc2` 后，可加载 4 个官方插件并启动 runtime

后续仍需确认：

- docs site 使用当前 `0.3.0rc2` 口径发布

## 0.3.0rc1

目标：发布一个可验证的 `0.3.0` 候选版本，用来检查 replay/export、外部插件 author skill、Windows 文件写入稳定性和文档口径。

已完成：

- 版本号统一到 `0.3.0rc1`
- widgets Replay 页面接入 recordings 列表、player 和 export 页面
- `modlink_core.replay` 提供 `RecordingReader`、`ReplayBackend` 和 `ExportService`
- 首批导出格式覆盖 `signal_csv`、`signal_npz`、`raster_npz`、`field_npz`、`video_frames_zip`、`recording_bundle_zip`
- live experiment sidebar 支持 experiment/session/steps 管理
- AI assistant 原型使用 OpenAI-compatible Chat Completions 和本地工具调用
- `tools/modlink-plugin-author` 成为外部 driver plugin 的推荐起点
- 删除 npm plugin scaffold 和实验性 Python plugin AI agent
- 删除已不再维护的 QML / Web 宿主路线包
- 测试默认忽略外部插件目录、构建产物和 `node_modules`
- Windows settings 保存路径增加原子替换重试，降低并发保存时的 transient `PermissionError`

已验证：

- PyPI / TestPyPI 发布流程按 `0.3.0rc1` 产物完整跑通
- 从干净环境安装 `modlink-studio==0.3.0rc1` 后可启动 `modlink-studio`
- `modlink-plugin` 能列出和安装兼容官方驱动
- docs site 使用当前 `0.3.0rc1` 口径发布

## 0.3.0

目标：把 rc 期间暴露的问题修完，形成稳定的 `0.3.0`。重点不是继续扩功能，而是收口已经进入 rc 的能力。

优先级：

1. 稳定 replay/export
2. 收口 session / experiment 最小持久化和 UI 使用方式
3. 明确外部插件 author skill 的分发和使用说明
4. 完成发布链路、安装链路、插件安装链路的端到端验证

不把以下内容作为 `0.3.0` 前置条件：

- 完整 protocol editor
- 任意时间轴 seek
- 多 recording 拼接
- live/replay 混播
- Web UI
- 新 QML 宿主
- 独立插件注册中心

## 0.3.x

目标：在 `0.3.0` 稳定后，把 live experiment sidebar 与 AI assistant 原型收口成可用的实验辅助工作流。`0.3.x` 不只是 replay/export 的补丁线，也承担原先规划给 `0.4.x` 的 AI 辅助能力。

可能进入 `0.3.x` 的内容：

- AI assistant 支持更清晰的状态上下文
- AI 生成或调整 session steps、录制标签、marker 建议
- AI 输出必须经过可审计的本地 action，不执行任意命令
- 设置页继续保持 OpenAI-compatible provider 配置
- 关键动作仍由用户确认：连接设备、开始采集、停止采集、删除数据
- recording catalog 的查询和筛选体验
- session / experiment 列表、详情和 recording 归档
- 更完整的 marker / segment 展示和编辑
- replay 时间轴 seek
- 批量导出
- export 参数配置
- `modlink-plugin` 的状态、来源、升级提示和第三方插件可见性
- 外部插件开发文档和 skill 使用示例
- 面向 Claude Code / Codex 的独立插件项目示例

仍然保持克制：

- AI 只辅助填写、建议和整理，不直接控制硬件关键动作
- catalog 先服务当前 widgets UI，不抽象成通用数据库层
- export 扩展先通过内建格式推进，不引入插件式 exporter 体系
- session / experiment 先做最小持久化和 UI 流程，不提前设计复杂研究数据平台
- 不恢复 npm scaffold
- 不恢复自研 Python plugin AI agent

## 0.4.x

目标：生态和数据交换能力扩展。

候选方向：

- 更完整的插件索引和第三方插件安装体验
- BIDS / NWB / HDF5 等更正式的数据导出
- replay API 服务化
- Web replay 或轻量 Web viewer
- 更完整的发布自动化和兼容性矩阵

这些方向需要在 `0.3.x` 的实验辅助、数据模型和插件开发路径稳定后再推进。

## 长期技术债务

- 从 SDK 开始引入类型检查
- 提升 UI 测试覆盖，尤其是 replay/export 和 settings 页面
- 梳理 Windows 文件系统相关测试的稳定性
- 减少重复的临时测试目录和构建产物污染
- 为正式发布补齐更清晰的 release checklist

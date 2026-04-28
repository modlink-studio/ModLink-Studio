# ModLink Studio Roadmap

本文档记录当前版本边界、后续路线和明确不做的方向。它不是设计草稿合集；已经完成或废弃的探索只保留结论。

## 当前位置

当前主线正在准备 `0.3.0` 正式发布。`0.3.0` 仍属于 SDK / driver API 的早期阶段，不承诺兼容 `0.2.x` driver 实现；`0.4.0` 预计会继续收紧 SDK 与插件管理边界。当前重点补齐：

- recording replay
- analysis-first export
- widgets 主宿主里的 Replay 页面
- live experiment sidebar 与 AI assistant 原型
- 外部 driver plugin author skill
- 官方插件的 CLI 安装入口

分支约定：

- `legacy/0.2.x`：维护 `0.2.x` 稳定线
- `wip/0.3.0`：当前 `0.3.0` 发布准备线
- `main`：`0.3.0` 正式发布前的合并目标

## 产品原则

- `modlink-studio` 继续作为公开安装入口，外部 driver plugin 依赖主包并通过 `modlink.drivers` entry point 被宿主发现。
- 主仓库维护宿主、SDK、core、UI 和插件管理入口；官方驱动源码和发布资产由独立插件仓库维护。
- `recording` 是最小数据资产，`session` 和 `experiment` 是上层组织关系，不反向塑造 recording 的内部结构。
- Core 保持纯 Python runtime；Qt 相关行为只留在 UI / bridge 层。
- 插件开发不再维护 npm scaffold 或自研 Python plugin AI agent；外部插件开发转向 `tools/modlink-plugin-author/SKILL.md`。
- UI 继续保持工具型、低装饰、少定制；新增能力优先通过已有页面、已有控件和 schema 化配置承载。
- 不为了未来 Web/QML 路线提前保留当前用不到的宿主包、适配层或扩展点。

## 0.3.0

状态：准备正式发布。

目标：将 `0.3.0rc3` 验证过的发布边界提升为正式 `0.3.0`。这一版重点是收口已经进入 rc 的能力，不继续扩功能。

已完成：

- 版本号统一到 `0.3.0`
- replay / export / widgets Replay 页面已接入
- live experiment sidebar 与 AI assistant 原型已进入当前 widgets 宿主
- `tools/modlink-plugin-author` 成为外部 driver plugin 的推荐起点
- `modlink-plugin` 可安装官方驱动插件
- `0.3.0rc3` TestPyPI rehearsal 已完整跑通
- 从 TestPyPI 安装 `modlink-studio==0.3.0rc3` 后，可安装 4 个官方插件并启动 4 个 driver portal
- 保持 PyQt6 / PyQt6-Qt6 `>=6.10.2,<6.11` 约束，避开 Qt 6.11.0 在 Windows 上暴露透明 popup 边界的问题

发布前仍需完成：

- 将 `wip/0.3.0` 合并到 `main`
- 在正式 release commit 上打 `v0.3.0`
- 手动触发 PyPI 发布 workflow
- 发布对应 docs site

不作为 `0.3.0` 前置条件：

- 完整 protocol editor
- 任意时间轴 seek
- 多 recording 拼接
- live/replay 混播
- Web UI
- 新 QML 宿主
- 插件显示 / 隐藏 UI
- 独立插件注册中心

## 0.3.x

状态：计划中。

目标：稳定 `0.3.0` 已发布能力，修复发布后暴露的问题，并继续小步改善 replay/export、experiment/sidebar 和官方插件安装链路。

候选内容：

- replay / export 的 bug fix 和小体验改进
- recording catalog 的查询和筛选体验
- session / experiment 列表、详情和 recording 归档
- marker / segment 的展示和编辑
- replay 时间轴 seek
- 批量导出和 export 参数配置
- `modlink-plugin` CLI 的状态、来源、升级提示和错误信息
- 外部插件开发文档和 skill 使用示例
- 面向 Claude Code / Codex 的独立插件项目示例
- Qt 6.11 popup 透明边界问题的后续验证，但不把迁移 PySide6 或重写 UI 作为默认方向

仍然保持克制：

- AI 只辅助填写、建议和整理，不直接控制硬件关键动作
- catalog 先服务当前 widgets UI，不抽象成通用数据库层
- export 扩展先通过内建格式推进，不引入插件式 exporter 体系
- session / experiment 先做最小持久化和 UI 流程，不提前设计复杂研究数据平台
- 不恢复 npm scaffold
- 不恢复自研 Python plugin AI agent

## 0.4.0

状态：计划中。

目标：把已安装插件变成产品内可见、可控制的状态。第一版不做完整插件管理器，而是先提供最小 UI：查看已发现插件，并决定某个插件是否在 Studio UI 中展示。

核心范围：

- 新增插件状态 UI，优先放在 Settings 或 Devices 相关入口中
- 展示当前环境中已发现的 `modlink.drivers` entry point
- 展示插件名称、driver id、来源包、版本和当前显示状态
- 支持显示 / 隐藏已安装插件
- 隐藏只影响 Studio UI 是否展示该插件，不影响 runtime driver discovery 和 entry point 发现
- 对需要重启应用或重启 runtime 才能生效的操作给出明确提示
- 安装、更新和卸载仍主要通过 `modlink-plugin` CLI 完成
- CLI 和 UI 共享同一份本地显示状态，不维护两套配置

安全边界：

- UI 不执行插件作者提供的任意命令
- UI 不从任意第三方源下载安装插件
- 不自动静默隐藏新插件
- 插件来源、版本和显示状态必须可见
- 第一版不做插件沙箱，不承诺隔离恶意插件代码

不进入 `0.4.0`：

- 完整插件市场
- 完整安装 / 更新 / 卸载 UI
- 付费插件、账号系统或远端权限体系
- 插件签名和信任链
- 插件自定义 UI 扩展点
- AI 自动生成并安装插件
- 恢复 npm scaffold 或 Python plugin AI agent

## 0.4.x

状态：后续扩展。

目标：在插件显示 / 隐藏 UI 稳定后，继续扩展生态和数据交换能力。

候选方向：

- 第三方插件来源的可见性和手动添加流程
- 官方插件的安装 / 更新 / 卸载 UI
- 插件兼容性矩阵和升级提示
- BIDS / NWB / HDF5 等更正式的数据导出
- replay API 服务化
- Web replay 或轻量 Web viewer
- 更完整的发布自动化和兼容性矩阵

这些方向需要在 `0.4.0` 的插件管理基础稳定后再推进。

## 长期技术债务

- 从 SDK 开始引入类型检查
- 提升 UI 测试覆盖，尤其是 replay/export、settings 和插件管理页面
- 梳理 Windows 文件系统相关测试的稳定性
- 减少重复的临时测试目录和构建产物污染
- 为正式发布补齐更清晰的 release checklist

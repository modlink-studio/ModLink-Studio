---
layout: home

hero:
  name: ModLink Studio
  text: 设备接入、多模态采集与展示的文档站
  tagline: 了解 0.2.0 的 PyPI 发布口径、driver 契约、纯 Python runtime 和双 UI / host 方向
  actions:
    - theme: brand
      text: 开始安装
      link: /install
    - theme: alt
      text: 查看 SDK
      link: /sdk

features:
  - icon: 📦
    title: PyPI 安装
    details: 0.2.0 正式发布后将通过 PyPI 分发；发布前会先完成一次 TestPyPI rehearsal。
  - icon: 🔌
    title: Driver 接入
    details: 外部 driver 优先依赖仓库内的 SDK 契约，通过 modlink.drivers entry point 被宿主发现。
  - icon: 🧠
    title: 纯 Python Runtime
    details: SDK 与 Core 已从 Qt 运行时语义中拆开，宿主围绕统一流模型和采集后端工作。
  - icon: 🖥️
    title: 双 UI / Host 方向
    details: 0.2.0 继续保留 Qt Widgets 宿主，同时推进 QML UI 和 FastAPI host，为后续 HTML / Web UI 做准备。
  - icon: ⚠️
    title: 0.2.0 破坏升级
    details: 0.2.0 不兼容 0.1.x 的 Qt-style driver API；当前版本边界是稳定采集、录制和保存。
---

<div style="height: 1rem;"></div>

# ModLink Studio 文档总览

当前文档以 `0.2.0` 主线为准。这里描述的是 `0.2.0` 的目标发布状态，而不是 `0.1.x` 的旧行为：

- `modlink_sdk` / `modlink_core` 已经是纯 Python runtime
- `0.2.0` 不兼容 `0.1.x` 的 Qt-style driver API
- UI 当前保持 Qt Widgets 与 QML 两条桌面路线并行
- FastAPI host 已建立服务化边界，用于后续 HTML / Web UI
- 录制回放不属于 `0.2.0`，延后到 `0.3.0`

`0.2.0` 目前尚未正式发布。正式发布时将以 **PyPI** 作为公开安装入口；发布前会先完成一次 **TestPyPI rehearsal**，但 `TestPyPI` 不作为日常安装源。

## 从哪里开始

- 想安装和运行：看 [安装与发布](/install)
- 想接 driver：看 [SDK 开发者指南](/sdk)
- 想理解 runtime：看 [Core 模块架构](/core)
- 想看 UI / host 方向：看 [UI 模块架构](/ui) 和 [App 组合根](/app)
- 想查服务接口：看 [服务端 API 手册](/server-api)
- 想直接跳源码 API：看 [API 快速索引](/api)

## 三个正式入口

- 源码仓库：[github.com/modlink-studio/ModLink-Studio](https://github.com/modlink-studio/ModLink-Studio)
- 文档站点：[modlink-studio.github.io](https://modlink-studio.github.io)
- 正式发布渠道：PyPI（`0.2.0` 正式发布后生效）

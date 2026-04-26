---
layout: home

hero:
  name: ModLink Studio
  text: 设备接入、多模态采集与展示的文档站
  tagline: 了解 0.3.0rc1 的 PyPI 预发布口径、driver 契约、回放能力和当前 widgets 宿主路线
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
    details: 0.3.0rc1 作为预发布版本走 PyPI；TestPyPI rehearsal 已完成。
  - icon: 🔌
    title: Driver 接入
    details: 外部 driver 优先依赖仓库内的 SDK 契约，通过 modlink.drivers entry point 被宿主发现。
  - icon: 🧠
    title: 纯 Python Runtime
    details: SDK 与 Core 已从 Qt 运行时语义中拆开，宿主围绕统一流模型和采集后端工作。
  - icon: 🖥️
    title: Widgets 宿主
    details: 当前桌面宿主路线收敛到 Qt Widgets，FastAPI host 继续保留为服务化边界。
  - icon: ⚠️
    title: 0.3.0rc1 预发布
    details: 0.3.0rc1 继续沿用纯 Python runtime，并新增 recording replay 与 analysis export。
---

<div style="height: 1rem;"></div>

# ModLink Studio 文档总览

当前文档以 `0.3.0rc1` 主线为准。这里描述的是 `0.3.0` release candidate 的当前边界，而不是 `0.1.x` 的旧行为：

- `modlink_sdk` / `modlink_core` 已经是纯 Python runtime
- `0.2.0` 不兼容 `0.1.x` 的 Qt-style driver API
- 当前桌面宿主以 Qt Widgets 为准
- FastAPI host 已建立服务化边界，用于后续 HTML / Web UI
- recording replay 与 analysis export 已接入当前 widgets 宿主

`0.3.0rc1` 的公开安装入口以 **PyPI** 为准；`TestPyPI rehearsal` 已完成，但 `TestPyPI` 不作为日常安装源。

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
- 正式发布渠道：PyPI

---
layout: home

hero:
  name: ModLink Studio
  text: 设备接入、多模态采集与展示的文档站
  tagline: 了解 0.2.0 安装方式、官方插件、driver 契约和纯 Python runtime 结构
  actions:
    - theme: brand
      text: 开始安装
      link: /install
    - theme: alt
      text: 查看 SDK
      link: /sdk

features:
  - icon: 📦
    title: Cloudsmith 包源
    details: 第一版官方包源为 Cloudsmith OSS。当前公共仓库未配置 PyPI upstream proxy，因此安装命令默认使用 extra index。
  - icon: 🔌
    title: Driver 接入
    details: 外部 driver 项目优先依赖 modlink-sdk，通过 modlink.drivers entry point 被宿主发现。
  - icon: 📡
    title: 统一流模型
    details: 宿主围绕 StreamDescriptor 和 FrameEnvelope 协作，避免把展示层和采集层绑定到具体设备协议。
  - icon: 🧩
    title: 分层架构
    details: SDK 负责接入契约，Core 负责纯 Python runtime，UI 负责页面与桥接，App 负责最终装配和启动。
  - icon: ⚠️
    title: 0.2.0 破坏升级
    details: 0.2.0 不兼容 0.1.x 的 Qt-style driver API；当前 UI bridge 仍在后续适配中。
---

<div style="height: 1rem;"></div>

# ModLink Studio 文档总览

ModLink Studio 的公开包源位于 Cloudsmith 仓库 `xylt-space/modlink-studio`。文档站说明安装方式、官方插件和 driver 开发模型；源码仓库则负责维护实现本身。

当前文档以 `0.2.0` 主线为准。涉及 `sig_frame`、`QThread`、`QTimer` 或 `QObject` parent 的旧 driver 写法，都不再是 SDK/Core 的正式契约。


[![Packages on Cloudsmith](https://img.shields.io/badge/packages-Cloudsmith-2A6DF4?logo=cloudsmith&logoColor=white)](https://dl.cloudsmith.io/public/xylt-space/modlink-studio/python/simple/)

[![OSS hosting by Cloudsmith](https://img.shields.io/badge/OSS%20hosting-Cloudsmith-2A6DF4?logo=cloudsmith&logoColor=white)](https://cloudsmith.com/)

## 从哪里开始

- 想安装和运行：看 [安装与发布](/install)
- 想了解 SDK 契约：看 [SDK 开发者指南](/sdk)
- 想理解宿主如何组装：看 [App 组合根](/app)
- 想直接查接口：看 [API 快速索引](/api)

## 三个正式入口

- 源码仓库：[github.com/modlink-studio/ModLink-Studio](https://github.com/modlink-studio/ModLink-Studio)
- 文档站点：[modlink-studio.github.io](https://modlink-studio.github.io)
- 官方包源：[dl.cloudsmith.io/public/xylt-space/modlink-studio/python/simple/](https://dl.cloudsmith.io/public/xylt-space/modlink-studio/python/simple/)

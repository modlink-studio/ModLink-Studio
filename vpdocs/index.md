---
layout: home

hero:
  name: ModLink Studio
  text: 面向设备接入、多模态采集与展示的文档站
  tagline: 先看怎么写 driver，再看数据怎么流动，最后再看 UI 和应用如何把这些能力组合起来
  actions:
    - theme: brand
      text: 先看 SDK
      link: /sdk
    - theme: alt
      text: 看整体架构
      link: /core

features:
  - icon: 🔌
    title: 先解决接入
    details: 对设备开发者来说，最重要的是先决定继承 Driver 还是 LoopDriver，然后把 SearchResult、StreamDescriptor 和 FrameEnvelope 定清楚。
  - icon: 🧠
    title: 降低心智负担
    details: 常见轮询设备直接用 LoopDriver，callback 型设备直接继承 Driver。先服务最常见的写法，再保留通用底座。
  - icon: 📡
    title: 统一流模型
    details: 设备接入后，系统内部都只看 stream_id、payload_type、shape 和 descriptor，不让 UI 直接依赖设备协议。
  - icon: 🧩
    title: 分层明确
    details: SDK 负责接入契约，Core 负责运行时和总线，UI 负责展示，App 负责最终组装和启动。
---

<div style="height: 1.5rem"></div>

# ModLink Studio 文档总览

这个站点主要服务两类人：

- 写设备 driver 的人
- 在已有流模型上继续做展示、录制或应用组装的人

如果你是来接设备的，推荐按下面这个顺序读：

1. [SDK 开发者指南](/sdk)
2. [Core 模块架构](/core)
3. [API 快速索引](/api)

如果你是来做展示或应用的，推荐按这个顺序读：

1. [Core 模块架构](/core)
2. [UI 模块架构](/ui)
3. [App 组合根](/app)

## 目前这套文档重点回答什么

- 什么时候直接继承 `Driver`
- 什么时候优先用 `LoopDriver`
- `SearchResult`、`StreamDescriptor`、`FrameEnvelope` 各自负责什么
- 插件如何通过 `uv run --with ...` 挂到当前运行环境里
- UI 和 Core 应该依赖哪些稳定约定，而不是依赖设备细节

## 现在最推荐的接入思路

对大多数传感器项目，建议先做这个判断：

- 如果设备是轮询型、串口型、BrainFlow 型，优先考虑 `LoopDriver`
- 如果设备底层是 callback 型 SDK，直接继承 `Driver`

然后再做这四件事：

1. 写 `search()`，返回可展示的 `SearchResult`
2. 写 `descriptors()`，定义这个设备会暴露哪些流
3. 写连接逻辑和采集逻辑
4. 通过 `sig_frame` 发出 `FrameEnvelope`

## 你最常要找的东西

- [SDK 页面](/sdk)：driver 契约、LoopDriver、数据模型
- [Core 页面](/core)：driver portal、engine、stream bus、录制链路
- [UI 页面](/ui)：UI 应该依赖哪些稳定约定
- [App 页面](/app)：插件发现、应用入口、推荐启动方式
- [API 页面](/api)：pdoc 自动文档入口


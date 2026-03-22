---
layout: home

hero:
  name: ModLink Studio
  text: 面向设备接入、多模态采集与展示的文档站
  tagline: 这个文档站记录的是 ModLink Studio 的接入方式、运行时结构，以及围绕这些能力展开的展示与应用组织方式
  actions:
    - theme: brand
      text: 查看 SDK
      link: /sdk
    - theme: alt
      text: 查看 Core
      link: /core

features:
  - icon: 🔌
    title: 设备接入
    details: 这里记录 driver 的基本契约，以及一个设备如何通过 SearchResult、StreamDescriptor 和 FrameEnvelope 接入整套平台。
  - icon: 🧠
    title: 轻量开发
    details: 常见轮询设备可以直接使用 LoopDriver；遇到 callback 型或更特殊的设备时，再回到基础 Driver 即可。
  - icon: 📡
    title: 统一流模型
    details: 设备一旦接入，系统内部主要围绕 stream_id、payload_type、数据 shape 和 descriptor 来协作，而不是继续依赖具体设备协议。
  - icon: 🧩
    title: 分层组织
    details: SDK 负责接入契约，Core 负责运行时与总线，UI 负责展示，App 负责最终组装与启动。
---

<div style="height: 1.5rem"></div>

# ModLink Studio 文档总览

`ModLink Studio` 是一个面向设备接入、多模态采集与展示的项目。

我目前主要把文档写在两个方向上：

- 如何为项目新增一个 driver
- 如何在已有流模型上继续做展示、录制和应用组装

## 阅读顺序：为项目新增一个 driver

如果目标是为项目新增加一个 driver，我会建议按下面这个顺序阅读：

1. [SDK 开发者指南](/sdk)
2. [Core 模块架构](/core)
3. [API 快速索引](/api)
4. [App 组合根](/app)

这条顺序的原因很简单：

- `SDK` 先定义接入契约
- `Core` 再说明这些契约在运行时里如何被调用和消费
- `API` 方便回头查具体类型和方法
- `App` 负责补上插件挂载和最终启动方式

## 这套文档主要覆盖的两个层面

### 1. 如何编写 driver

这里主要记录：

- 什么时候直接继承 `Driver`
- 什么时候优先使用 `LoopDriver`
- `SearchResult`、`StreamDescriptor`、`FrameEnvelope` 分别承担什么职责
- 一个插件怎样通过 `uv run --with ...` 挂到当前运行环境里

### 2. 如何使用这个项目

这里主要记录：

- `Core`、`UI` 和 `App` 各自负责什么
- 上层模块应该依赖哪些稳定约定，而不是依赖设备细节
- 一个已经接入的设备怎样被展示、录制和组装进具体应用

## 常用入口

- [SDK 页面](/sdk)：driver 契约、LoopDriver、共享数据模型
- [Core 页面](/core)：driver portal、engine、stream bus、录制链路
- [UI 页面](/ui)：展示层应该依赖的稳定边界
- [App 页面](/app)：插件发现、应用入口和启动方式
- [API 页面](/api)：pdoc 自动文档入口
